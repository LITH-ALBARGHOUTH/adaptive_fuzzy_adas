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
            "engine_results": {
                "risk": risk_result,
                "lane": lane_result,
                "comfort": comfort_result,
                "meta": meta_result,
            },
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

    MODES = ["OTONOM", "MANUEL", "DESTEKLİ"]
    SCENARIO_LABELS = {
        "normal_driving": "Normal Sürüş",
        "high_speed_short_distance": "Yüksek Hız Kısa Mesafe",
        "large_lane_deviation": "Büyük Şerit Sapması",
        "poor_road_condition": "Kötü Yol Koşulu",
        "conflicting_tradeoff": "Çatışmalı Karar Durumu",
        "boundary_stop_and_go": "Sınır Durumu Dur-Kalk",
        "boundary_open_road": "Sınır Durumu Açık Yol",
        "uphill_grade_challenge": "Yokuş Tırmanışı",
    }
    CAMERA_LABELS = {
        "CHASE": "Takip",
        "TOP-DOWN": "Üstten",
    }
    RULE_TOKEN_LABELS = {
        "close": "yakın",
        "medium": "orta",
        "low": "düşük",
        "high": "yüksek",
        "far": "uzak",
        "highspeed": "yüksek hız",
        "medspeed": "orta hız",
        "lowspeed": "düşük hız",
        "highrisk": "yüksek risk",
        "mediumrisk": "orta risk",
        "lowrisk": "düşük risk",
        "critical": "kritik",
        "poorroad": "kötü yol",
        "normalroad": "normal yol",
        "goodroad": "iyi yol",
        "farleft": "çok sola kayma",
        "farright": "çok sağa kayma",
        "left": "sol",
        "right": "sağ",
        "centered": "merkez",
        "unstable": "dengesiz direksiyon",
        "stable": "kararlı direksiyon",
        "light": "hafif",
        "moderate": "orta",
        "heavy": "yoğun",
        "downhill": "iniş",
        "uphill": "çıkış",
        "flat": "düz yol",
        "highcomfort": "yüksek konfor",
        "mediumcomfort": "orta konfor",
        "lowcomfort": "düşük konfor",
        "strongleft": "sert sol düzeltme",
        "strongright": "sert sağ düzeltme",
        "baseline": "temel",
    }
    ANTECEDENT_VAR_LABELS = {
        "front_distance": "ön mesafe",
        "speed": "hız",
        "road_condition": "yol",
        "lane_deviation": "şerit ofseti",
        "steering_stability": "direksiyon",
        "road_slope": "eğim",
        "traffic_density": "trafik",
        "current_speed": "hız",
        "risk_level": "risk",
        "lane_stability": "şerit",
        "comfort_efficiency": "konfor",
    }
    CONSEQUENT_LABELS = {
        "low": "düşük",
        "medium": "orta",
        "high": "yüksek",
        "critical": "kritik",
        "strong_left": "sert sol",
        "left": "sol",
        "centered": "merkez",
        "right": "sağ",
        "strong_right": "sert sağ",
        "zero": "sıfır",
        "light": "hafif",
        "none": "yok",
        "hard": "sert",
        "keep": "koru",
        "steer_left": "sola kır",
        "steer_left_hard": "sert sola kır",
        "steer_right": "sağa kır",
        "steer_right_hard": "sert sağa kır",
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
        self.dangerous_overtake = False
        self.overtake_state_label = "Yok"
        self.overtake_phase = "idle"

        self.ego_visual = VehicleVisual(color.azure, with_brake_lights=True)
        self.front_visual = VehicleVisual(color.orange, with_brake_lights=True, scale_factor=0.96)
        self.oncoming_visual = VehicleVisual(color.red, with_brake_lights=True, scale_factor=0.92)

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
        self.oncoming_state = TrafficVehicleState(lateral_x=0.0, forward_z=160.0, speed_mps=24.0)
        self.steering_history: deque[float] = deque(
            [self.ego_state.steering_state],
            maxlen=self.config.steering_history_window,
        )
        self.last_manual_command = ControlCommand(0.0, 0.0, 0.0)
        self.last_fuzzy_subsystems = {"risk": 0.0, "lane": 50.0, "comfort": 50.0}
        self.last_fuzzy_controls = {"throttle": 0.0, "brake": 0.0, "steering": 0.0}
        self.last_engine_results = {}
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
        self.dangerous_overtake = False
        self.overtake_state_label = "Yok"
        self.overtake_phase = "idle"
        self.input_controller.reset()

        self.ego_state = EgoVehicleState(**asdict(scenario.ego_initial))
        self.front_state = TrafficVehicleState(**asdict(scenario.front_initial))
        self.oncoming_state = TrafficVehicleState(
            lateral_x=0.0,
            forward_z=self.ego_state.forward_z + self.config.oncoming_spawn_distance_m,
            speed_mps=20.0 + (scenario.environment_initial.traffic_density * 12.0),
        )
        self.environment_state = EnvironmentState(**asdict(scenario.environment_initial))
        self.steering_history = deque(
            [self.ego_state.steering_state],
            maxlen=self.config.steering_history_window,
        )
        self.last_manual_command = ControlCommand(0.0, 0.0, 0.0)
        self.last_fuzzy_subsystems = {"risk": 0.0, "lane": 50.0, "comfort": 50.0}
        self.last_fuzzy_controls = {"throttle": 0.0, "brake": 0.0, "steering": 0.0}
        self.last_engine_results = {}
        self.last_applied_command = ControlCommand(0.0, 0.0, 0.0)
        self.world.configure_for_scenario(self.current_scenario.name)

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
            self.last_engine_results = fuzzy_result["engine_results"]
            self._update_overtake_analysis()
            self._update_overtake_phase()

            fuzzy_command = ControlCommand(**self.last_fuzzy_controls)
            applied_command = self._resolve_command(
                manual_command=self.last_manual_command,
                fuzzy_command=fuzzy_command,
                sensor_inputs=sensor_inputs,
            )
            applied_command = self._apply_overtake_behavior(applied_command)
            self.last_applied_command = applied_command

            self._update_ego_vehicle(applied_command, dt)
            self._update_front_vehicle(dt)
            self._update_oncoming_vehicle(dt)
            self._update_flags(sensor_inputs["front_distance_m"])

            if self.current_time >= self.current_scenario.duration_s or self.collision or self.lane_departure:
                self.finished = True
                self.running = False

        self._sync_visuals()
        ego_render_x = self.world.lane_visual_x(
            self.ego_state.lateral_x,
            self.config.ego_lane_visual_offset_m,
        )
        ego_height, _ = self.world.road_height_and_pitch(self.ego_state.forward_z)
        self.camera_controller.update(self.ego_state, dt, ego_render_x, ego_height)
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
        ego_lane = self._ego_lane_id()
        front_lane = self._front_lane_id()
        forward_gap = self.front_state.forward_z - self.ego_state.forward_z
        if forward_gap <= 0.0:
            return 120.0
        if ego_lane != front_lane:
            return 120.0
        return min(forward_gap, 120.0)

    def _steering_stability(self) -> float:
        if len(self.steering_history) < 3:
            return self.config.default_steering_stability

        variability = float(np.std(np.asarray(self.steering_history, dtype=float)))
        stability = 1.0 - min(variability / 0.55, 1.0)
        return _clamp(stability, 0.0, 1.0)

    def _oncoming_distance(self) -> float:
        """Distance to the nearest oncoming vehicle in the opposite lane."""

        return self.oncoming_state.forward_z - self.ego_state.forward_z

    def _ego_visual_x(self) -> float:
        """Rendered x position of the ego vehicle."""

        return self.world.lane_visual_x(
            self.ego_state.lateral_x,
            self.config.ego_lane_visual_offset_m,
        )

    def _front_visual_x(self) -> float:
        """Rendered x position of the front vehicle."""

        return self.world.lane_visual_x(
            self.front_state.lateral_x,
            self.config.ego_lane_visual_offset_m,
        )

    def _oncoming_visual_x(self) -> float:
        """Rendered x position of the oncoming vehicle."""

        return self.world.lane_visual_x(
            self.oncoming_state.lateral_x,
            -self.config.ego_lane_visual_offset_m,
        )

    def _ego_lane_id(self) -> int:
        """Lane identity of the ego car in rendered space."""

        return self.world.lane_id_from_visual_x(self._ego_visual_x())

    def _front_lane_id(self) -> int:
        """Lane identity of the front car in rendered space."""

        return self.world.lane_id_from_visual_x(self._front_visual_x())

    def _oncoming_lane_id(self) -> int:
        """Lane identity of the oncoming car in rendered space."""

        return self.world.lane_id_from_visual_x(self._oncoming_visual_x())

    def _is_attempting_overtake(self) -> bool:
        """Return True when the ego vehicle has crossed into the opposite lane."""

        ego_visual_x = self.world.lane_visual_x(
            self.ego_state.lateral_x,
            self.config.ego_lane_visual_offset_m,
        )
        return ego_visual_x <= 0.2

    def _should_start_overtake(self) -> bool:
        """Return True when conditions are favorable for a pass."""

        if self._ego_lane_id() != 1 or self._front_lane_id() != 1:
            return False
        if self._front_distance() > self.config.overtake_trigger_distance_m:
            return False
        if (self.ego_state.speed_mps - self.front_state.speed_mps) < self.config.overtake_min_speed_advantage_mps:
            return False
        if self._oncoming_distance() < self.config.overtake_safe_oncoming_distance_m:
            return False
        return self.last_fuzzy_subsystems["risk"] < self.config.status_high_risk_threshold

    def _update_overtake_phase(self) -> None:
        """Advance the pass-and-return state machine."""

        if self.mode_name == "MANUEL":
            if self._is_attempting_overtake():
                self.overtake_phase = "manual"
                self.overtake_state_label = "Manuel Sollama"
            elif self.overtake_phase == "manual":
                self.overtake_phase = "idle"
                self.overtake_state_label = "Yok"
            return

        if self.dangerous_overtake and self.overtake_phase in {"merge_left", "pass_left"}:
            self.overtake_phase = "return_right"
            return

        if self.overtake_phase == "idle":
            if self.mode_name == "OTONOM" and self._should_start_overtake():
                self.overtake_phase = "merge_left"
            return

        if self.overtake_phase == "merge_left":
            if self.ego_state.lateral_x <= self.config.overtake_left_lane_target_m + 0.10:
                self.overtake_phase = "pass_left"
            return

        if self.overtake_phase == "pass_left":
            if (self.ego_state.forward_z - self.front_state.forward_z) >= self.config.overtake_return_gap_m:
                self.overtake_phase = "return_right"
            return

        if self.overtake_phase == "return_right":
            if self.ego_state.lateral_x >= -0.10:
                self.overtake_phase = "idle"
                self.overtake_state_label = "Tamamlandı"
            return

    def _apply_overtake_behavior(self, command: ControlCommand) -> ControlCommand:
        """Blend overtaking steering targets with the current command."""

        if self.mode_name == "MANUEL":
            return command

        if self.overtake_phase == "merge_left":
            target_offset = self.config.overtake_left_lane_target_m
            steering = _clamp((target_offset - self.ego_state.lateral_x) * 0.95, -0.95, 0.55)
            self.overtake_state_label = "Sollama Başlıyor"
            return ControlCommand(
                throttle=max(command.throttle, 0.45),
                brake=min(command.brake, 0.10),
                steering=steering,
            )

        if self.overtake_phase == "pass_left":
            steering = _clamp((self.config.overtake_left_lane_target_m - self.ego_state.lateral_x) * 0.70, -0.55, 0.35)
            self.overtake_state_label = "Sol Şeritte Geçiş"
            return ControlCommand(
                throttle=max(command.throttle, 0.40),
                brake=min(command.brake, 0.12),
                steering=steering,
            )

        if self.overtake_phase == "return_right":
            steering = _clamp((0.0 - self.ego_state.lateral_x) * 0.95, -0.60, 0.95)
            self.overtake_state_label = "Sağ Şeride Dönüş"
            return ControlCommand(
                throttle=max(command.throttle, 0.28),
                brake=min(command.brake, 0.18),
                steering=steering,
            )

        if self.overtake_phase == "idle" and self.overtake_state_label != "Tamamlandı":
            self.overtake_state_label = "Yok"
        return command

    def _update_overtake_analysis(self) -> None:
        """Analyze whether the current overtaking maneuver is dangerous."""

        if not self._is_attempting_overtake():
            self.dangerous_overtake = False
            self.overtake_state_label = "Yok"
            return

        oncoming_distance = self._oncoming_distance()
        if oncoming_distance <= 0.0:
            self.dangerous_overtake = False
            self.overtake_state_label = "Temiz"
            return
        if oncoming_distance <= self.config.oncoming_critical_distance_m:
            self.dangerous_overtake = True
            self.overtake_state_label = "Kritik"
            return
        if oncoming_distance <= self.config.oncoming_clearance_distance_m:
            self.dangerous_overtake = True
            self.overtake_state_label = "Riskli"
            return

        self.dangerous_overtake = False
        self.overtake_state_label = "Kontrollü"

    def _resolve_command(
        self,
        *,
        manual_command: ControlCommand,
        fuzzy_command: ControlCommand,
        sensor_inputs: Dict[str, float],
    ) -> ControlCommand:
        if self.mode_name == "OTONOM":
            self.last_warning_message = "Otonom bulanık kontrol aktif."
            if self.dangerous_overtake:
                self.last_warning_message = "Tehlikeli sollama: karşı şeritte araç var."
            elif self.overtake_phase in {"merge_left", "pass_left", "return_right"}:
                self.last_warning_message = f"Otonom manevra: {self.overtake_state_label}."
            return fuzzy_command

        if self.mode_name == "MANUEL":
            if self.dangerous_overtake:
                self.last_warning_message = "Tehlikeli sollama: karşıdan araç yaklaşıyor."
            elif self.last_fuzzy_subsystems["risk"] >= self.config.status_high_risk_threshold:
                self.last_warning_message = "Uyarı: sürüş sırasında yüksek risk algılandı."
            elif abs(sensor_inputs["lane_deviation_m"]) > 1.0:
                self.last_warning_message = "Uyarı: şerit sapması artıyor."
            else:
                self.last_warning_message = "Manuel sürüş. Bulanık çıktılar karşılaştırma için gösteriliyor."
            return manual_command

        risk = self.last_fuzzy_subsystems["risk"]
        if self.dangerous_overtake:
            self.last_warning_message = "Destek devrede: tehlikeli sollama kesiliyor."
            return ControlCommand(
                throttle=min(manual_command.throttle, 0.12),
                brake=max(manual_command.brake, max(0.45, fuzzy_command.brake)),
                steering=max(manual_command.steering, fuzzy_command.steering),
            )

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

    def _update_oncoming_vehicle(self, dt: float) -> None:
        """Move the opposite-lane vehicle toward the ego car and recycle it."""

        traffic_bias = self.environment_state.traffic_density
        target_speed = 18.0 + (traffic_bias * 16.0)
        self.oncoming_state.speed_mps += (target_speed - self.oncoming_state.speed_mps) * min(1.0, dt * 1.5)
        self.oncoming_state.forward_z -= self.oncoming_state.speed_mps * dt
        self.oncoming_state.braking = False

        if self.oncoming_state.forward_z < self.ego_state.forward_z - 45.0:
            self.oncoming_state.forward_z = self.ego_state.forward_z + self.config.oncoming_spawn_distance_m + (
                traffic_bias * 35.0
            )
            self.oncoming_state.speed_mps = target_speed

    def _update_flags(self, sensed_distance: float) -> None:
        actual_distance = self.front_state.forward_z - self.ego_state.forward_z
        ego_lane = self._ego_lane_id()
        front_lane = self._front_lane_id()
        self.collision = (
            ego_lane == front_lane
            and actual_distance >= 0.0
            and actual_distance <= self.config.collision_distance_m
        )

        oncoming_distance = self._oncoming_distance()
        oncoming_collision = (
            ego_lane == self._oncoming_lane_id()
            and oncoming_distance >= 0.0
            and oncoming_distance <= self.config.collision_distance_m
        )
        self.collision = self.collision or oncoming_collision

        self.lane_departure = abs(self._ego_visual_x()) >= self.world.offroad_limit_x()
        self._update_overtake_analysis()

    def _sync_visuals(self) -> None:
        lane_visual_offset = self.config.ego_lane_visual_offset_m
        lane_visual_scale = self.config.lane_visual_scale
        ego_height, ego_pitch = self.world.road_height_and_pitch(self.ego_state.forward_z)
        front_height, front_pitch = self.world.road_height_and_pitch(self.front_state.forward_z)
        oncoming_height, oncoming_pitch = self.world.road_height_and_pitch(self.oncoming_state.forward_z)
        self.ego_visual.sync_ego(
            self.ego_state,
            self.config.steering_visual_yaw_deg,
            lane_visual_offset,
            lane_visual_scale,
            ego_height,
            ego_pitch,
        )
        self.front_visual.sync_traffic(
            self.front_state,
            lane_visual_offset,
            lane_visual_scale,
            front_height,
            front_pitch,
        )
        self.oncoming_visual.sync_traffic(
            self.oncoming_state,
            -lane_visual_offset,
            lane_visual_scale,
            oncoming_height,
            oncoming_pitch,
            180.0,
        )
        self.ego_visual.set_brake_lights(self.last_applied_command.brake > 0.2)
        self.world.update_debug_visuals(
            self.ego_state,
            self.front_state,
            self._front_distance(),
            self.debug_enabled,
            lane_visual_offset,
        )
        self.world.set_lane_center_visible(self.centerline_visible)

    def _status_style(self) -> tuple[str, object]:
        if self.collision:
            return "ÇARPIŞMA", color.red
        if self.dangerous_overtake:
            return "TEHLİKELİ SOLLAMA", color.orange
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
            f"Hız {self.ego_state.speed_mps:4.1f} m/s | Ön {self._front_distance():4.1f} m",
            f"Ofset {self.ego_state.lateral_x:4.2f} m | Risk {self.last_fuzzy_subsystems['risk']:5.1f}",
            f"Şerit {self.last_fuzzy_subsystems['lane']:5.1f} | Konfor {self.last_fuzzy_subsystems['comfort']:5.1f}",
            f"Gaz {self.last_applied_command.throttle:4.2f} | Fren {self.last_applied_command.brake:4.2f} | Dir {self.last_applied_command.steering:4.2f}",
            f"Karşı {self._oncoming_distance():4.1f} m | Sollama {self.overtake_state_label}",
            f"Yol {self.environment_state.road_condition:4.2f} | Eğim {self.environment_state.slope:4.1f} | Trafik {self.environment_state.traffic_density:4.2f}",
        ]

    def _pretty_antecedent(self, antecedent_key: str) -> str:
        """Convert one antecedent key into a readable Turkish phrase."""

        variable_name, label_name = antecedent_key.split(".", 1)
        variable_label = self.ANTECEDENT_VAR_LABELS.get(variable_name, variable_name.replace("_", " "))
        state_label = self.RULE_TOKEN_LABELS.get(label_name, label_name.replace("_", " "))
        return f"{variable_label} {state_label}"

    def _summarize_activation_reason(self, activation) -> str:
        """Build a compact reason sentence from rule antecedents."""

        reasons = [
            self._pretty_antecedent(key)
            for key in activation.antecedent_memberships.keys()
        ]
        if not reasons:
            return "genel durum"

        text = ", ".join(reasons[:2])
        if len(reasons) > 2:
            text = f"{text}, ..."
        if len(text) > 32:
            return f"{text[:29]}..."
        return text

    def _pretty_consequent(self, label: str) -> str:
        """Return a user-facing Turkish consequent label."""

        return self.CONSEQUENT_LABELS.get(label, label.replace("_", " "))

    def _rule_lines(self) -> list[str]:
        """Return readable live rule summaries for the HUD."""

        if not self.last_engine_results:
            return [
                "Simülasyon başlayınca burada",
                "baskın neden ve kararlar",
                "özet olarak görünecek.",
            ]

        engine_outputs = [
            ("RİSK", self.last_engine_results["risk"].output("risk_level").activations, False),
            ("ŞERİT", self.last_engine_results["lane"].output("lane_stability").activations, False),
            ("KONFOR", self.last_engine_results["comfort"].output("comfort_efficiency").activations, True),
            ("FREN", self.last_engine_results["meta"].output("brake_command").activations, False),
        ]

        lines = []
        for title, activations, prefer_slope_rule in engine_outputs:
            ranked = [
                activation
                for activation in sorted(activations, key=lambda item: item.firing_strength, reverse=True)
                if activation.firing_strength > 0.0
            ]
            lines.append(f"{title}:")
            if not ranked:
                lines.append("  aktif kural yok")
                continue
            display_activations = [ranked[0]]
            if prefer_slope_rule:
                slope_activation = next(
                    (
                        activation
                        for activation in ranked[1:]
                        if any(key.startswith("road_slope.") for key in activation.antecedent_memberships)
                    ),
                    None,
                )
                if slope_activation is not None:
                    display_activations.append(slope_activation)

            for activation in display_activations[:2]:
                lines.append(
                    f"  Neden: {self._summarize_activation_reason(activation)}"
                )
                lines.append(
                    f"  Karar: {self._pretty_consequent(activation.consequent_label)} "
                    f"({activation.firing_strength:.2f})"
                )
        return lines

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
            rule_lines=self._rule_lines(),
        )
