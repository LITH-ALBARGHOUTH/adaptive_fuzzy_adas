"""Scenario library for the time-based ADAS simulation."""

from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

from config import get_default_simulation_config
from utils import (
    EgoVehicleState,
    EnvironmentState,
    FrontVehicleState,
    ScenarioExpectation,
    ScenarioDefinition,
)


def _constant_lane_rate(rate: float):
    return lambda _t: rate


def _sinusoidal_lane_rate(amplitude: float, frequency: float, bias: float = 0.0):
    return lambda t: bias + amplitude * math.sin(frequency * t)


def _windowed_acceleration(default_value: float, windows: Iterable[Tuple[float, float, float]]):
    windows = tuple(windows)

    def profile(t: float, _front_state: FrontVehicleState) -> float:
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


def normal_driving() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="normal_driving",
        description="Balanced cruising with small lateral motion and mild lead-vehicle variation.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.03, speed=22.0),
        front_initial=FrontVehicleState(x_position=45.0, speed=23.0),
        environment_initial=EnvironmentState(road_condition=0.90, slope=0.5, traffic_density=0.30),
        interpretation_hint="This should stay in a comfortable, low-risk operating region.",
        front_acceleration_profile=_windowed_acceleration(0.0, [(8.0, 10.0, -0.8)]),
        environment_profile=_windowed_environment(0.90, 0.5, 0.30, [(12.0, 16.0, {"traffic_density": 0.45})]),
        lane_disturbance_profile=_sinusoidal_lane_rate(0.03, 0.8),
        expectation=ScenarioExpectation(
            description="Low-risk, comfort-oriented cruising with only light braking.",
            max_max_risk=40.0,
            max_peak_brake=0.25,
            min_peak_throttle=0.50,
            max_rms_lane_deviation=0.10,
            min_minimum_distance=35.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def high_speed_short_distance() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="high_speed_short_distance",
        description="High ego speed with a short headway and an abruptly braking lead vehicle.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.00, speed=34.0),
        front_initial=FrontVehicleState(x_position=25.0, speed=28.0),
        environment_initial=EnvironmentState(road_condition=0.82, slope=0.0, traffic_density=0.45),
        interpretation_hint="The controller should rapidly shift into a safety-dominant response.",
        front_acceleration_profile=_windowed_acceleration(0.0, [(4.0, 7.5, -4.0)]),
        environment_profile=_windowed_environment(0.82, 0.0, 0.45, []),
        lane_disturbance_profile=_sinusoidal_lane_rate(0.01, 0.5),
        expectation=ScenarioExpectation(
            description="Safety-dominant braking should emerge while avoiding collision.",
            min_max_risk=65.0,
            min_peak_brake=0.70,
            max_peak_throttle=0.30,
            min_minimum_distance=10.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def large_lane_deviation() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="large_lane_deviation",
        description="The vehicle starts with a strong rightward lane deviation that must be corrected.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=1.05, speed=23.0),
        front_initial=FrontVehicleState(x_position=60.0, speed=22.0),
        environment_initial=EnvironmentState(road_condition=0.93, slope=0.0, traffic_density=0.25),
        interpretation_hint="The lane-stability engine should dominate the first few seconds.",
        front_acceleration_profile=_windowed_acceleration(0.0, []),
        environment_profile=_windowed_environment(0.93, 0.0, 0.25, []),
        lane_disturbance_profile=_constant_lane_rate(0.02),
        expectation=ScenarioExpectation(
            description="Strong lateral correction should dominate without leaving the lane.",
            min_peak_abs_steering=0.70,
            max_rms_lane_deviation=0.30,
            min_minimum_distance=50.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def poor_road_condition() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="poor_road_condition",
        description="Reduced grip and moderate traffic force a more conservative longitudinal response.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.08, speed=25.0),
        front_initial=FrontVehicleState(x_position=38.0, speed=24.0),
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
        expectation=ScenarioExpectation(
            description="Road degradation should raise risk and moderate throttle usage.",
            min_max_risk=50.0,
            max_peak_throttle=0.30,
            min_minimum_distance=30.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def conflicting_tradeoff() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="conflicting_tradeoff",
        description="Medium longitudinal risk, poor lateral state, and a strong comfort preference all compete.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.85, speed=24.0),
        front_initial=FrontVehicleState(x_position=30.0, speed=22.0),
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
        expectation=ScenarioExpectation(
            description="Competing objectives should produce both notable braking and steering activity.",
            min_max_risk=65.0,
            min_peak_brake=0.60,
            min_peak_abs_steering=0.45,
            min_minimum_distance=15.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def boundary_stop_and_go() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="boundary_stop_and_go",
        description="Near-standstill dense traffic with a short gap and stop-and-go lead-vehicle motion.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.00, speed=2.5),
        front_initial=FrontVehicleState(x_position=10.0, speed=2.0),
        environment_initial=EnvironmentState(road_condition=0.45, slope=0.0, traffic_density=0.95),
        interpretation_hint="The controller should stay stable at low speed and avoid a low-speed collision.",
        front_acceleration_profile=_windowed_acceleration(0.0, [(4.0, 6.0, -1.2), (11.0, 14.0, 0.8)]),
        environment_profile=_windowed_environment(0.45, 0.0, 0.95, []),
        lane_disturbance_profile=_constant_lane_rate(0.0),
        expectation=ScenarioExpectation(
            description="The controller should remain stable at low speed and come close to a stop if needed.",
            min_max_risk=50.0,
            max_peak_throttle=0.25,
            max_peak_abs_steering=0.10,
            min_minimum_distance=8.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def boundary_open_road() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="boundary_open_road",
        description="High-speed open-road case with excellent grip and a very large headway.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=-0.04, speed=36.0),
        front_initial=FrontVehicleState(x_position=120.0, speed=35.0),
        environment_initial=EnvironmentState(road_condition=1.00, slope=-0.5, traffic_density=0.05),
        interpretation_hint="The controller should avoid unnecessary braking and remain comfort-oriented.",
        front_acceleration_profile=_windowed_acceleration(0.0, []),
        environment_profile=_windowed_environment(1.00, -0.5, 0.05, []),
        lane_disturbance_profile=_sinusoidal_lane_rate(0.01, 0.5),
        expectation=ScenarioExpectation(
            description="Open-road comfort bias should keep throttle healthy and braking light.",
            max_peak_brake=0.25,
            min_peak_throttle=0.50,
            min_minimum_distance=30.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def uphill_grade_challenge() -> ScenarioDefinition:
    duration = get_default_simulation_config().default_duration_s
    return ScenarioDefinition(
        name="uphill_grade_challenge",
        description="A sustained uphill climb with growing traffic and a slowing lead vehicle.",
        duration_s=duration,
        ego_initial=EgoVehicleState(x_position=0.0, y_position=0.02, speed=21.0),
        front_initial=FrontVehicleState(x_position=48.0, speed=22.0),
        environment_initial=EnvironmentState(road_condition=0.82, slope=1.0, traffic_density=0.35),
        interpretation_hint="This scenario highlights how uphill grade suppresses comfort bias and encourages safer longitudinal control.",
        front_acceleration_profile=_windowed_acceleration(0.0, [(8.0, 12.0, -1.6), (14.0, 17.0, -0.8)]),
        environment_profile=_windowed_environment(
            0.82,
            1.0,
            0.35,
            [
                (4.0, 9.0, {"slope": 4.0, "traffic_density": 0.45}),
                (9.0, 15.0, {"slope": 6.5, "traffic_density": 0.60, "road_condition": 0.74}),
                (15.0, 20.0, {"slope": 3.0, "traffic_density": 0.42}),
            ],
        ),
        lane_disturbance_profile=_sinusoidal_lane_rate(0.012, 0.7),
        expectation=ScenarioExpectation(
            description="The uphill climb should reduce comfort bias and keep throttle moderate while preserving safety.",
            max_peak_throttle=0.35,
            min_peak_brake=0.18,
            min_minimum_distance=40.0,
            expect_collision=False,
            expect_lane_departure=False,
        ),
    )


def get_predefined_scenarios() -> Dict[str, ScenarioDefinition]:
    """Return all required scenarios."""

    scenarios = [
        normal_driving(),
        high_speed_short_distance(),
        large_lane_deviation(),
        poor_road_condition(),
        conflicting_tradeoff(),
        boundary_stop_and_go(),
        boundary_open_road(),
        uphill_grade_challenge(),
    ]
    return {scenario.name: scenario for scenario in scenarios}
