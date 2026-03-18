"""Predefined scenarios for the 3D fuzzy driving demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Tuple

from vehicle import EgoVehicleState, EnvironmentState, TrafficVehicleState


@dataclass
class ScenarioDefinition:
    """Complete scenario definition with time-varying profiles."""

    name: str
    description: str
    duration_s: float
    ego_initial: EgoVehicleState
    front_initial: TrafficVehicleState
    environment_initial: EnvironmentState
    interpretation_hint: str
    front_acceleration_profile: Callable[[float, TrafficVehicleState], float]
    environment_profile: Callable[[float], EnvironmentState]
    lane_disturbance_profile: Callable[[float], float]


def _constant_lane_rate(rate: float):
    return lambda _t: rate


def _sinusoidal_lane_rate(amplitude: float, frequency: float, bias: float = 0.0):
    import math

    return lambda t: bias + amplitude * math.sin(frequency * t)


def _windowed_acceleration(default_value: float, windows: Iterable[Tuple[float, float, float]]):
    windows = tuple(windows)

    def profile(t: float, _front_state: TrafficVehicleState) -> float:
        for start, end, value in windows:
            if start <= t <= end:
                return value
        return default_value

    return profile


def _windowed_environment(
    base_condition: float,
    base_slope: float,
    base_traffic: float,
    windows: Iterable[Tuple[float, float, Dict[str, float]]],
):
    windows = tuple(windows)

    def profile(t: float) -> EnvironmentState:
        road_condition = base_condition
        slope = base_slope
        traffic_density = base_traffic

        for start, end, overrides in windows:
            if start <= t <= end:
                road_condition = overrides.get("road_condition", road_condition)
                slope = overrides.get("slope", slope)
                traffic_density = overrides.get("traffic_density", traffic_density)

        return EnvironmentState(
            road_condition=road_condition,
            slope=slope,
            traffic_density=traffic_density,
        )

    return profile


def build_scenarios() -> Dict[str, ScenarioDefinition]:
    """Build the complete predefined scenario set."""

    duration = 20.0
    scenarios = [
        ScenarioDefinition(
            name="normal_driving",
            description="Balanced cruising with small lateral motion and mild lead-vehicle variation.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=0.03, forward_z=0.0, speed_mps=22.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=45.0, speed_mps=23.0),
            environment_initial=EnvironmentState(road_condition=0.90, slope=0.5, traffic_density=0.30),
            interpretation_hint="This should stay in a comfortable, low-risk operating region.",
            front_acceleration_profile=_windowed_acceleration(0.0, [(8.0, 10.0, -0.8)]),
            environment_profile=_windowed_environment(0.90, 0.5, 0.30, [(12.0, 16.0, {"traffic_density": 0.45})]),
            lane_disturbance_profile=_sinusoidal_lane_rate(0.03, 0.8),
        ),
        ScenarioDefinition(
            name="high_speed_short_distance",
            description="High ego speed with a short headway and an abruptly braking lead vehicle.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=0.0, forward_z=0.0, speed_mps=34.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=25.0, speed_mps=28.0),
            environment_initial=EnvironmentState(road_condition=0.82, slope=0.0, traffic_density=0.45),
            interpretation_hint="The controller should rapidly shift into a safety-dominant response.",
            front_acceleration_profile=_windowed_acceleration(0.0, [(4.0, 7.5, -4.0)]),
            environment_profile=_windowed_environment(0.82, 0.0, 0.45, []),
            lane_disturbance_profile=_sinusoidal_lane_rate(0.01, 0.5),
        ),
        ScenarioDefinition(
            name="large_lane_deviation",
            description="The vehicle starts with a strong rightward lane deviation that must be corrected.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=1.05, forward_z=0.0, speed_mps=23.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=60.0, speed_mps=22.0),
            environment_initial=EnvironmentState(road_condition=0.93, slope=0.0, traffic_density=0.25),
            interpretation_hint="The lane-stability engine should dominate the first few seconds.",
            front_acceleration_profile=_windowed_acceleration(0.0, []),
            environment_profile=_windowed_environment(0.93, 0.0, 0.25, []),
            lane_disturbance_profile=_constant_lane_rate(0.02),
        ),
        ScenarioDefinition(
            name="poor_road_condition",
            description="Reduced grip and moderate traffic force a more conservative longitudinal response.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=0.08, forward_z=0.0, speed_mps=25.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=38.0, speed_mps=24.0),
            environment_initial=EnvironmentState(road_condition=0.35, slope=1.5, traffic_density=0.55),
            interpretation_hint="Road-condition degradation should raise the risk estimate even without a critical gap.",
            front_acceleration_profile=_windowed_acceleration(0.0, [(9.0, 12.0, -1.5)]),
            environment_profile=_windowed_environment(
                0.35,
                1.5,
                0.55,
                [(7.0, 14.0, {"road_condition": 0.22, "traffic_density": 0.65})],
            ),
            lane_disturbance_profile=_sinusoidal_lane_rate(0.015, 1.1),
        ),
        ScenarioDefinition(
            name="conflicting_tradeoff",
            description="Medium longitudinal risk, poor lateral state, and a strong comfort preference all compete.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=0.85, forward_z=0.0, speed_mps=24.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=30.0, speed_mps=22.0),
            environment_initial=EnvironmentState(road_condition=0.78, slope=-2.5, traffic_density=0.15),
            interpretation_hint="This exposes how the meta controller resolves competing fuzzy objectives.",
            front_acceleration_profile=_windowed_acceleration(0.0, [(7.0, 10.0, -1.8)]),
            environment_profile=_windowed_environment(
                0.78,
                -2.5,
                0.15,
                [(10.0, 15.0, {"traffic_density": 0.08, "slope": -3.5})],
            ),
            lane_disturbance_profile=_sinusoidal_lane_rate(0.025, 0.6, bias=0.02),
        ),
        ScenarioDefinition(
            name="boundary_stop_and_go",
            description="Near-standstill dense traffic with a short gap and stop-and-go lead-vehicle motion.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=0.0, forward_z=0.0, speed_mps=2.5),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=10.0, speed_mps=2.0),
            environment_initial=EnvironmentState(road_condition=0.45, slope=0.0, traffic_density=0.95),
            interpretation_hint="The controller should stay stable at low speed and avoid a low-speed collision.",
            front_acceleration_profile=_windowed_acceleration(0.0, [(4.0, 6.0, -1.2), (11.0, 14.0, 0.8)]),
            environment_profile=_windowed_environment(0.45, 0.0, 0.95, []),
            lane_disturbance_profile=_constant_lane_rate(0.0),
        ),
        ScenarioDefinition(
            name="boundary_open_road",
            description="High-speed open-road case with excellent grip and a very large headway.",
            duration_s=duration,
            ego_initial=EgoVehicleState(lateral_x=-0.04, forward_z=0.0, speed_mps=36.0),
            front_initial=TrafficVehicleState(lateral_x=0.0, forward_z=120.0, speed_mps=35.0),
            environment_initial=EnvironmentState(road_condition=1.00, slope=-0.5, traffic_density=0.05),
            interpretation_hint="The controller should avoid unnecessary braking and remain comfort-oriented.",
            front_acceleration_profile=_windowed_acceleration(0.0, []),
            environment_profile=_windowed_environment(1.00, -0.5, 0.05, []),
            lane_disturbance_profile=_sinusoidal_lane_rate(0.01, 0.5),
        ),
    ]
    return {scenario.name: scenario for scenario in scenarios}
