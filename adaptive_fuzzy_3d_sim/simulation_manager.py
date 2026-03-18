"""3D bulanık sürüş demosunun simülasyon orkestrasyonu."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict
from typing import Dict

import numpy as np
from ursina import application, color

from camera_controller import CameraController
from config import DemoConfig, get_default_fuzzy_config
from fuzzy_systems import (
    CollisionRiskEngine,
    ComfortEfficiencyEngine,
    LaneStabilityEngine,
    MetaDecisionEngine,
)
from hud import SimulationHUD
from input_controller import InputController
from scenario_manager import ScenarioManager
from vehicle import ControlCommand, EgoVehicleState, EnvironmentState, TrafficVehicleState, VehicleVisual
from world import DrivingWorld


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(value, upper)))


class FuzzyControllerBridge:
    """Adapter that keeps the existing hierarchical fuzzy system intact."""

    def __init__(self) -> None:
        config_bundle = get_default_fuzzy_config()
        self.risk_engine = CollisionRiskEngine(config_bundle["collision"])
        self.lane_engine = LaneStabilityEngine(config_bundle["lane"])
        self.comfort_engine = ComfortEfficiencyEngine(config_bundle["comfort"])
        self.meta_engine = MetaDecisionEngine(config_bundle["meta"])

    def evaluate(
        self,
        *,
        speed_mps: float,
        front_distance_m: float,
        lane_deviation_m: float,
        steering_stability: float,
        road_condition: float,
        slope: float,
        traffic_density: float,
    ) -> Dict[str, Dict[str, float]]:
        """Run the hierarchical fuzzy system and return subsystem/control outputs."""

        speed_kph = speed_mps * 3.6

        risk_result = self.risk_engine.evaluate(
            speed=speed_kph,
            front_distance=front_distance_m,
            road_condition=road_condition,
        )
        lane_result = self.lane_engine.evaluate(
            lane_deviation=lane_deviation_m,
            steering_stability=steering_stability,
            speed=speed_kph,
        )
        comfort_result = self.comfort_engine.evaluate(
            road_slope=slope,
            traffic_density=traffic_density,
            current_speed=speed_kph,
        )

        subsystem_outputs = {
            "risk": risk_result.crisp_outputs["risk_level"],
            "lane": lane_result.crisp_outputs["lane_stability"],
            "comfort": comfort_result.crisp_outputs["comfort_efficiency"],
        }

        meta_result = self.meta_engine.evaluate(
            risk_level=subsystem_outputs["risk"],
            lane_stability=subsystem_outputs["lane"],
            comfort_efficiency=subsystem_outputs["comfort"],
        )

        raw_controls = ControlCommand(
            throttle=meta_result.crisp_outputs["throttle_command"],
            brake=meta_result.crisp_outputs["brake_command"],
            steering=meta_result.crisp_outputs["steering_correction"],
        )
        final_controls = self._arbitrate(raw_controls)

        return {
            "subsystems": subsystem_outputs,
            "raw_controls": asdict(raw_controls),
            "controls": asdict(final_controls),
        }

    @staticmethod
    def _arbitrate(command: ControlCommand) -> ControlCommand:
        """Prevent unrealistic simultaneous throttle and brake authority."""

        throttle = _clamp(command.throttle, 0.0, 1.0)
        brake = _clamp(command.brake, 0.0, 1.0)
        steering = _clamp(command.steering, -1.0, 1.0)

        if brake >= 0.60:
            throttle = 0.0
        elif brake >= 0.35:
            throttle = min(throttle, 0.15)
        elif brake >= 0.15:
            throttle = min(throttle, 0.28)

        return ControlCommand(throttle=throttle, brake=brake, steering=steering)


class SimulationManager:
    """Canlı 3D simülasyonu, arayüzü ve bulanık entegrasyonu yönetir."""

    MODES = ["DEMO", "MANUEL", "DESTEKLİ"]
    SCENARIO_LABELS = {
        "normal_driving": "Normal Sürüş",
        "high_speed_short_distance": "Yüksek Hız Kısa Mesafe",
        "large_lane_deviation": "Büyük Şerit Sapması",
        "poor_road_condition": "Kötü Yol Koşulu",
        "conflicting_tradeoff": "Çatışmalı Karar Durumu",
        "boundary_stop_and_go": "Sınır Durumu Dur-Kalk",
        "boundary_open_road": "Sınır Durumu Açık Yol",
    }
    CAMERA_LABELS = {
        "CHASE": "Takip",
        "TOP-DOWN": "Üstten",
    }

    def __init__(self, config: DemoConfig | None = None) -> None:
        self.config = config or DemoConfig()
        self.controller = FuzzyControllerBridge()
        self.scenario_manager = ScenarioManager()
        self.input_controller = InputController()
        self.world = DrivingWorld(self.config)
        self.camera_controller = CameraController(self.config)
        self.mode_index = 0
        self.debug_enabled = True
        self.centerline_visible = True
        self.running = False
        self.paused = False
        self.finished = False
        self.current_time = 0.0
        self.collision = False
        self.lane_departure = False
        self.last_warning_message = ""

        self.ego_visual = VehicleVisual(color.azure, with_brake_lights=True)
        self.front_visual = VehicleVisual(color.orange, with_brake_lights=True, scale_factor=0.96)

        self.hud = SimulationHUD(
            self.config,
            callbacks={
                "start": self.start,
                "pause": self.toggle_pause,
                "reset": self.reset_current_scenario,
                "next_scenario": self.next_scenario,
                "previous_scenario": self.previous_scenario,
                "cycle_mode": self.cycle_mode,
                "toggle_camera": self.toggle_camera,
                "toggle_debug": self.toggle_debug,
                "toggle_centerline": self.toggle_centerline,
                "quit": self.quit_simulation,
            },
        )

        self.current_scenario = self.scenario_manager.current()
        self.environment_state = self.current_scenario.environment_initial
        self.ego_state = self.current_scenario.ego_initial
        self.front_state = self.current_scenario.front_initial
        self.steering_history: deque[float] = deque(
            [self.ego_state.steering_state],
            maxlen=self.config.steering_history_window,
        )
        self.last_manual_command = ControlCommand(0.0, 0.0, 0.0)
        self.last_fuzzy_subsystems = {"risk": 0.0, "lane": 50.0, "comfort": 50.0}
        self.last_fuzzy_controls = {"throttle": 0.0, "brake": 0.0, "steering": 0.0}
        self.last_applied_command = ControlCommand(0.0, 0.0, 0.0)
        self.reset_current_scenario()

    @property
    def mode_name(self) -> str:
        """Current driving mode."""

        return self.MODES[self.mode_index]

    def start(self) -> None:
        """Start or resume the simulation."""

        if self.finished:
            self.reset_current_scenario()
        self.running = True
        self.paused = False

    def toggle_pause(self) -> None:
        """Pause or resume the live simulation."""

        if not self.running:
            self.start()
            return
        self.paused = not self.paused

    def cycle_mode(self) -> None:
        """Cycle through demo, manual, and assisted modes."""

        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.input_controller.reset()

    def toggle_camera(self) -> None:
        """Toggle camera mode."""

        self.camera_controller.toggle_mode()

    def toggle_debug(self) -> None:
        """Toggle sensor and guide overlays."""

        self.debug_enabled = not self.debug_enabled

    def toggle_centerline(self) -> None:
        """Toggle the lane-center reference line."""

        self.centerline_visible = not self.centerline_visible
        self.world.set_lane_center_visible(self.centerline_visible)

    def quit_simulation(self) -> None:
        """Oyunu güvenli şekilde kapat."""

        application.quit()

    def next_scenario(self) -> None:
        """Select and load the next scenario."""

        self.current_scenario = self.scenario_manager.next()
        self.reset_current_scenario()

    def previous_scenario(self) -> None:
        """Select and load the previous scenario."""

        self.current_scenario = self.scenario_manager.previous()
        self.reset_current_scenario()

    def reset_current_scenario(self) -> None:
        """Reset the scene to the selected scenario's initial state."""

        scenario = self.scenario_manager.current()
        self.current_scenario = scenario
        self.current_time = 0.0
        self.running = False
        self.paused = False
        self.finished = False
        self.collision = False
        self.lane_departure = False
        self.last_warning_message = ""
        self.input_controller.reset()

        self.ego_state = EgoVehicleState(**asdict(scenario.ego_initial))
        self.front_state = TrafficVehicleState(**asdict(scenario.front_initial))
        self.environment_state = EnvironmentState(**asdict(scenario.environment_initial))
        self.steering_history = deque(
            [self.ego_state.steering_state],
            maxlen=self.config.steering_history_window,
        )
        self.last_manual_command = ControlCommand(0.0, 0.0, 0.0)
        self.last_fuzzy_subsystems = {"risk": 0.0, "lane": 50.0, "comfort": 50.0}
        self.last_fuzzy_controls = {"throttle": 0.0, "brake": 0.0, "steering": 0.0}
        self.last_applied_command = ControlCommand(0.0, 0.0, 0.0)

        self._sync_visuals()
        self._refresh_hud()

    def handle_input(self, key: str) -> None:
        """Keyboard shortcuts for the demo."""

        if key == "space":
            self.toggle_pause()
        elif key == "r":
            self.reset_current_scenario()
        elif key == "tab":
            self.cycle_mode()
        elif key == "c":
            self.toggle_camera()
        elif key == "f1":
            self.toggle_debug()
        elif key == "l":
            self.toggle_centerline()
        elif key == "n":
            self.next_scenario()
        elif key == "b":
            self.previous_scenario()
        elif key in {"escape", "q"}:
            self.quit_simulation()

    def update(self, dt: float) -> None:
        """Advance the live simulation by one frame."""

        dt = min(dt, self.config.dt_cap)
        self.last_manual_command = self.input_controller.sample(dt)

        if self.running and not self.paused and not self.finished:
            self.current_time += dt
            self.environment_state = self.current_scenario.environment_profile(self.current_time)

            sensor_inputs = self._build_sensor_inputs()
            fuzzy_result = self.controller.evaluate(**sensor_inputs)
            self.last_fuzzy_subsystems = fuzzy_result["subsystems"]
            self.last_fuzzy_controls = fuzzy_result["controls"]

            fuzzy_command = ControlCommand(**self.last_fuzzy_controls)
            applied_command = self._resolve_command(
                manual_command=self.last_manual_command,
                fuzzy_command=fuzzy_command,
                sensor_inputs=sensor_inputs,
            )
            self.last_applied_command = applied_command

            self._update_ego_vehicle(applied_command, dt)
            self._update_front_vehicle(dt)
            self._update_flags(sensor_inputs["front_distance_m"])

            if self.current_time >= self.current_scenario.duration_s or self.collision or self.lane_departure:
                self.finished = True
                self.running = False

        self._sync_visuals()
        self.camera_controller.update(self.ego_state, dt)
        self._refresh_hud()

    def _build_sensor_inputs(self) -> Dict[str, float]:
        front_distance = self._front_distance()
        lane_deviation = self.ego_state.lateral_x
        steering_stability = self._steering_stability()
        return {
            "speed_mps": self.ego_state.speed_mps,
            "front_distance_m": front_distance,
            "lane_deviation_m": lane_deviation,
            "steering_stability": steering_stability,
            "road_condition": self.environment_state.road_condition,
            "slope": self.environment_state.slope,
            "traffic_density": self.environment_state.traffic_density,
        }

    def _front_distance(self) -> float:
        lateral_gap = abs(self.front_state.lateral_x - self.ego_state.lateral_x)
        forward_gap = self.front_state.forward_z - self.ego_state.forward_z
        if forward_gap <= 0.0:
            return 120.0
        if lateral_gap > self.config.same_lane_threshold_m:
            return 120.0
        return min(forward_gap, 120.0)

    def _steering_stability(self) -> float:
        if len(self.steering_history) < 3:
            return self.config.default_steering_stability

        variability = float(np.std(np.asarray(self.steering_history, dtype=float)))
        stability = 1.0 - min(variability / 0.55, 1.0)
        return _clamp(stability, 0.0, 1.0)

    def _resolve_command(
        self,
        *,
        manual_command: ControlCommand,
        fuzzy_command: ControlCommand,
        sensor_inputs: Dict[str, float],
    ) -> ControlCommand:
        if self.mode_name == "DEMO":
            self.last_warning_message = "Otonom bulanık kontrol aktif."
            return fuzzy_command

        if self.mode_name == "MANUEL":
            if self.last_fuzzy_subsystems["risk"] >= self.config.status_high_risk_threshold:
                self.last_warning_message = "Uyarı: sürüş sırasında yüksek risk algılandı."
            elif abs(sensor_inputs["lane_deviation_m"]) > 1.0:
                self.last_warning_message = "Uyarı: şerit sapması artıyor."
            else:
                self.last_warning_message = "Manuel sürüş. Bulanık çıktılar karşılaştırma için gösteriliyor."
            return manual_command

        risk = self.last_fuzzy_subsystems["risk"]
        if risk >= self.config.critical_risk_threshold:
            self.last_warning_message = "Destek devraldı: kritik risk."
            return ControlCommand(
                throttle=min(manual_command.throttle, fuzzy_command.throttle),
                brake=max(manual_command.brake, fuzzy_command.brake),
                steering=fuzzy_command.steering,
            )

        if risk >= self.config.assisted_risk_threshold or abs(sensor_inputs["lane_deviation_m"]) > 0.95:
            self.last_warning_message = "Destek devrede: düzeltici müdahale uygulanıyor."
            return ControlCommand(
                throttle=min(manual_command.throttle, max(0.10, fuzzy_command.throttle)),
                brake=max(manual_command.brake, fuzzy_command.brake * 0.85),
                steering=_clamp((manual_command.steering * 0.45) + (fuzzy_command.steering * 0.55), -1.0, 1.0),
            )

        self.last_warning_message = "Destekli mod: sürücü kontrolde, bulanık sistem izliyor."
        return manual_command

    def _update_ego_vehicle(self, command: ControlCommand, dt: float) -> None:
        acceleration = (
            self.config.throttle_gain * command.throttle
            - self.config.brake_gain * command.brake
        )
        self.ego_state.speed_mps = _clamp(
            self.ego_state.speed_mps + acceleration * dt,
            0.0,
            self.config.max_speed_mps,
        )
        self.ego_state.steering_state += (
            (command.steering - self.ego_state.steering_state)
            * self.config.steering_response
            * dt
        )
        self.ego_state.steering_state = _clamp(self.ego_state.steering_state, -1.0, 1.0)
        lane_drift = self.current_scenario.lane_disturbance_profile(self.current_time)
        self.ego_state.lateral_x += (
            self.ego_state.steering_state
            * self.ego_state.speed_mps
            * self.config.lateral_gain
            * dt
        ) + (lane_drift * dt)
        self.ego_state.forward_z += self.ego_state.speed_mps * dt
        self.ego_state.heading_deg = self.ego_state.steering_state * self.config.steering_visual_yaw_deg
        self.steering_history.append(self.ego_state.steering_state)

    def _update_front_vehicle(self, dt: float) -> None:
        acceleration = self.current_scenario.front_acceleration_profile(self.current_time, self.front_state)
        self.front_state.speed_mps = _clamp(
            self.front_state.speed_mps + acceleration * dt,
            0.0,
            self.config.max_speed_mps,
        )
        self.front_state.forward_z += self.front_state.speed_mps * dt
        self.front_state.braking = acceleration < -0.35

    def _update_flags(self, sensed_distance: float) -> None:
        actual_distance = self.front_state.forward_z - self.ego_state.forward_z
        lateral_gap = abs(self.front_state.lateral_x - self.ego_state.lateral_x)
        self.collision = actual_distance <= self.config.collision_distance_m and lateral_gap <= self.config.same_lane_threshold_m
        self.lane_departure = abs(self.ego_state.lateral_x) >= self.config.lane_departure_limit_m

    def _sync_visuals(self) -> None:
        self.ego_visual.sync_ego(self.ego_state, self.config.steering_visual_yaw_deg)
        self.front_visual.sync_traffic(self.front_state)
        self.ego_visual.set_brake_lights(self.last_applied_command.brake > 0.2)
        self.world.update_debug_visuals(
            self.ego_state,
            self.front_state,
            self._front_distance(),
            self.debug_enabled,
        )
        self.world.set_lane_center_visible(self.centerline_visible)

    def _status_style(self) -> tuple[str, object]:
        if self.collision:
            return "ÇARPIŞMA", color.red
        if self.lane_departure:
            return "ŞERİT İHLALİ", color.orange
        if self.last_fuzzy_subsystems["risk"] >= self.config.status_high_risk_threshold:
            return "YÜKSEK RİSK", color.red
        if self.last_fuzzy_subsystems["risk"] >= self.config.status_caution_threshold:
            return "DİKKAT", color.yellow
        return "GÜVENLİ", color.lime

    def _running_state_label(self) -> str:
        if self.finished:
            return "BİTTİ"
        if self.running and not self.paused:
            return "ÇALIŞIYOR"
        if self.paused:
            return "DURAKLATILDI"
        return "HAZIR"

    def _telemetry_lines(self) -> list[str]:
        return [
            f"Hız: {self.ego_state.speed_mps:5.2f} m/s ({self.ego_state.speed_mps * 3.6:5.1f} km/sa)",
            f"Ön Mesafe: {self._front_distance():5.2f} m",
            f"Şerit Ofseti: {self.ego_state.lateral_x:5.2f} m",
            f"Yol Koşulu: {self.environment_state.road_condition:4.2f}",
            f"Eğim: {self.environment_state.slope:5.2f}",
            f"Trafik Yoğunluğu: {self.environment_state.traffic_density:4.2f}",
            f"Risk Seviyesi: {self.last_fuzzy_subsystems['risk']:5.2f}",
            f"Şerit Kararlılığı: {self.last_fuzzy_subsystems['lane']:5.2f}",
            f"Konfor/Verim: {self.last_fuzzy_subsystems['comfort']:5.2f}",
            f"Gaz: {self.last_applied_command.throttle:4.2f}",
            f"Fren: {self.last_applied_command.brake:4.2f}",
            f"Direksiyon: {self.last_applied_command.steering:5.2f}",
        ]

    def _scenario_display_name(self) -> str:
        """Arayüz için Türkçe senaryo etiketi dön."""

        return self.SCENARIO_LABELS.get(self.current_scenario.name, self.current_scenario.name)

    def _camera_display_name(self) -> str:
        """Arayüz için Türkçe kamera etiketi dön."""

        return self.CAMERA_LABELS.get(self.camera_controller.mode_name, self.camera_controller.mode_name)

    def _refresh_hud(self) -> None:
        status_label, status_color = self._status_style()
        self.hud.update_display(
            scenario_name=self._scenario_display_name(),
            mode_name=self.mode_name,
            camera_mode=self._camera_display_name(),
            running_state=self._running_state_label(),
            telemetry_lines=self._telemetry_lines(),
            status_label=status_label,
            status_color=status_color,
            warning_message=self.last_warning_message or self.current_scenario.interpretation_hint,
            risk_value=self.last_fuzzy_subsystems["risk"],
        )
