"""Time-based driving simulation wrapped around the hierarchical fuzzy controller."""

from __future__ import annotations

from collections import deque
from typing import Dict, List

from config import SimulationConfig, get_default_fuzzy_config, get_default_simulation_config
from fuzzy_systems import (
    CollisionRiskEngine,
    ComfortEfficiencyEngine,
    LaneStabilityEngine,
    MetaDecisionEngine,
)
from utils import (
    EgoVehicleState,
    EnvironmentState,
    FrontVehicleState,
    ScenarioDefinition,
    SimulationResult,
    SimulationStepRecord,
    clamp,
    clone_state,
    compute_steering_stability,
    mps_to_kph,
    rms,
)


class HierarchicalFuzzyADASController:
    """Thin integration wrapper around the existing fuzzy engines."""

    def __init__(self, fuzzy_config: Dict[str, Dict] | None = None) -> None:
        config_bundle = fuzzy_config or get_default_fuzzy_config()
        self.risk_engine = CollisionRiskEngine(config_bundle["collision"])
        self.lane_engine = LaneStabilityEngine(config_bundle["lane"])
        self.comfort_engine = ComfortEfficiencyEngine(config_bundle["comfort"])
        self.meta_engine = MetaDecisionEngine(config_bundle["meta"])

    def evaluate(self, sensor_inputs: Dict[str, float]) -> Dict[str, object]:
        """Evaluate the hierarchical fuzzy stack for the current time step."""

        speed_kph = mps_to_kph(sensor_inputs["speed"])

        risk_result = self.risk_engine.evaluate(
            speed=speed_kph,
            front_distance=sensor_inputs["distance"],
            road_condition=sensor_inputs["road_condition"],
        )
        lane_result = self.lane_engine.evaluate(
            lane_deviation=sensor_inputs["lane_deviation"],
            steering_stability=sensor_inputs["steering_stability"],
            speed=speed_kph,
        )
        comfort_result = self.comfort_engine.evaluate(
            road_slope=sensor_inputs["slope"],
            traffic_density=sensor_inputs["traffic_density"],
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

        raw_commands = {
            "throttle": meta_result.crisp_outputs["throttle_command"],
            "brake": meta_result.crisp_outputs["brake_command"],
            "steering": meta_result.crisp_outputs["steering_correction"],
        }
        final_commands = self._arbitrate_commands(raw_commands)

        return {
            "subsystem_outputs": subsystem_outputs,
            "raw_commands": raw_commands,
            "final_commands": final_commands,
            "engine_results": {
                "risk": risk_result,
                "lane": lane_result,
                "comfort": comfort_result,
                "meta": meta_result,
            },
        }

    @staticmethod
    def _arbitrate_commands(raw_commands: Dict[str, float]) -> Dict[str, float]:
        """Reduce unrealistic simultaneous throttle and brake authority."""

        throttle = clamp(raw_commands["throttle"], 0.0, 1.0)
        brake = clamp(raw_commands["brake"], 0.0, 1.0)
        steering = clamp(raw_commands["steering"], -1.0, 1.0)

        if brake >= 0.60:
            throttle = 0.0
        elif brake >= 0.35:
            throttle = min(throttle, 0.12)
        elif brake >= 0.15:
            throttle = min(throttle, 0.25)

        return {"throttle": throttle, "brake": brake, "steering": steering}


def compute_inputs(
    ego_state: EgoVehicleState,
    front_state: FrontVehicleState,
    environment_state: EnvironmentState,
    steering_history: deque[float],
    simulation_config: SimulationConfig,
) -> Dict[str, float]:
    """Compute the sensor inputs used by the fuzzy hierarchy."""

    distance = front_state.x_position - ego_state.x_position
    steering_stability = compute_steering_stability(
        list(steering_history),
        fallback=simulation_config.default_steering_stability,
    )

    return {
        "speed": clamp(ego_state.speed, 0.0, simulation_config.max_speed_mps),
        "distance": distance,
        "lane_deviation": ego_state.y_position,
        "road_condition": clamp(environment_state.road_condition, 0.0, 1.0),
        "slope": environment_state.slope,
        "traffic_density": clamp(environment_state.traffic_density, 0.0, 1.0),
        "steering_stability": steering_stability,
    }


def update_vehicle(
    ego_state: EgoVehicleState,
    throttle: float,
    brake: float,
    steering: float,
    dt: float,
    throttle_gain: float,
    brake_gain: float,
    max_speed_mps: float,
    lane_disturbance_rate: float = 0.0,
) -> EgoVehicleState:
    """Update the ego vehicle using the required simple time-domain model."""

    acceleration = (throttle_gain * throttle) - (brake_gain * brake)
    speed = max(0.0, min(max_speed_mps, ego_state.speed + acceleration * dt))
    x_position = ego_state.x_position + speed * dt
    y_position = ego_state.y_position + (steering + lane_disturbance_rate) * dt

    return EgoVehicleState(x_position=x_position, y_position=y_position, speed=speed)


def update_front_vehicle(
    front_state: FrontVehicleState,
    front_acceleration: float,
    dt: float,
    max_speed_mps: float,
) -> FrontVehicleState:
    """Update the front-vehicle state."""

    speed = max(0.0, min(max_speed_mps, front_state.speed + front_acceleration * dt))
    x_position = front_state.x_position + speed * dt
    return FrontVehicleState(x_position=x_position, speed=speed)


def _build_summary(records: List[SimulationStepRecord]) -> Dict[str, object]:
    if not records:
        return {
            "steps": 0,
            "final_speed": 0.0,
            "minimum_distance": 0.0,
            "max_risk": 0.0,
            "rms_lane_deviation": 0.0,
            "collision": False,
            "lane_departure": False,
        }

    minimum_distance = min(
        min(
            record.sensor_inputs["distance"],
            record.front_state_next.x_position - record.ego_state_next.x_position,
        )
        for record in records
    )

    return {
        "steps": len(records),
        "final_speed": records[-1].ego_state_next.speed,
        "minimum_distance": minimum_distance,
        "max_risk": max(record.subsystem_outputs["risk"] for record in records),
        "rms_lane_deviation": rms([record.ego_state.y_position for record in records]),
        "collision": any(record.collision for record in records),
        "lane_departure": any(record.lane_departure for record in records),
    }


def run_simulation(
    scenario: ScenarioDefinition,
    controller: HierarchicalFuzzyADASController | None = None,
    simulation_config: SimulationConfig | None = None,
) -> SimulationResult:
    """Run a complete time-based scenario simulation."""

    controller = controller or HierarchicalFuzzyADASController()
    simulation_config = simulation_config or get_default_simulation_config()

    ego_state = clone_state(scenario.ego_initial)
    front_state = clone_state(scenario.front_initial)
    steering_history: deque[float] = deque(
        [0.0],
        maxlen=simulation_config.steering_history_window,
    )
    records: List[SimulationStepRecord] = []

    step_count = int(round(scenario.duration_s / simulation_config.dt))

    for step_index in range(step_count):
        time_s = step_index * simulation_config.dt
        environment_state = scenario.environment_profile(time_s)

        ego_before = clone_state(ego_state)
        front_before = clone_state(front_state)
        sensor_inputs = compute_inputs(
            ego_state=ego_before,
            front_state=front_before,
            environment_state=environment_state,
            steering_history=steering_history,
            simulation_config=simulation_config,
        )

        evaluation = controller.evaluate(sensor_inputs)
        commands = evaluation["final_commands"]

        ego_state = update_vehicle(
            ego_state=ego_before,
            throttle=commands["throttle"],
            brake=commands["brake"],
            steering=commands["steering"],
            dt=simulation_config.dt,
            throttle_gain=simulation_config.throttle_gain,
            brake_gain=simulation_config.brake_gain,
            max_speed_mps=simulation_config.max_speed_mps,
            lane_disturbance_rate=scenario.lane_disturbance_profile(time_s),
        )
        front_state = update_front_vehicle(
            front_state=front_before,
            front_acceleration=scenario.front_acceleration_profile(time_s, front_before),
            dt=simulation_config.dt,
            max_speed_mps=simulation_config.max_speed_mps,
        )

        steering_history.append(commands["steering"])

        distance_after = front_state.x_position - ego_state.x_position
        collision = distance_after <= simulation_config.collision_distance_m
        lane_departure = abs(ego_state.y_position) >= simulation_config.lane_departure_limit_m

        records.append(
            SimulationStepRecord(
                time_s=time_s,
                sensor_inputs=sensor_inputs,
                subsystem_outputs=evaluation["subsystem_outputs"],
                raw_command_outputs=evaluation["raw_commands"],
                final_command_outputs=commands,
                ego_state=ego_before,
                front_state=front_before,
                ego_state_next=clone_state(ego_state),
                front_state_next=clone_state(front_state),
                environment_state=clone_state(environment_state),
                engine_results=evaluation["engine_results"],
                collision=collision,
                lane_departure=lane_departure,
            )
        )

        if collision or lane_departure:
            break

    return SimulationResult(
        scenario=scenario,
        records=records,
        summary=_build_summary(records),
    )
