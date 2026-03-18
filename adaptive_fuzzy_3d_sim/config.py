"""Configuration for the 3D fuzzy driving demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np


@dataclass
class MembershipSpec:
    """Editable membership-function definition."""

    shape: str
    params: Tuple[float, ...]


@dataclass
class VariableConfig:
    """Variable universe and linguistic labels."""

    name: str
    bounds: Tuple[float, float]
    step: float
    labels: Dict[str, MembershipSpec]

    @property
    def universe(self) -> np.ndarray:
        start, stop = self.bounds
        num_points = int(round((stop - start) / self.step)) + 1
        return np.linspace(start, stop, num_points, dtype=float)


@dataclass
class DemoConfig:
    """Tuning values for the lightweight 3D driving demo."""

    target_fps: int = 60
    dt_cap: float = 1.0 / 20.0
    max_speed_mps: float = 40.0
    throttle_gain: float = 3.6
    brake_gain: float = 7.0
    steering_response: float = 4.5
    lateral_gain: float = 0.23
    steering_visual_yaw_deg: float = 12.0
    lane_width_m: float = 3.5
    lane_departure_limit_m: float = 1.75
    road_lane_count: int = 3
    road_length_m: float = 1800.0
    road_width_margin_m: float = 2.0
    steering_history_window: int = 18
    default_steering_stability: float = 0.88
    same_lane_threshold_m: float = 1.8
    collision_distance_m: float = 4.2
    assisted_risk_threshold: float = 65.0
    critical_risk_threshold: float = 80.0
    status_high_risk_threshold: float = 70.0
    status_caution_threshold: float = 40.0
    chase_camera_height: float = 7.0
    chase_camera_distance: float = 18.0
    topdown_camera_height: float = 42.0
    topdown_follow_distance: float = 3.0
    ui_panel_width: float = 0.42
    environment_floor_size: float = 2200.0


def _speed_config(name: str = "speed") -> VariableConfig:
    return VariableConfig(
        name=name,
        bounds=(0.0, 140.0),
        step=1.0,
        labels={
            "low": MembershipSpec("trap", (0.0, 0.0, 25.0, 55.0)),
            "medium": MembershipSpec("tri", (35.0, 70.0, 100.0)),
            "high": MembershipSpec("trap", (85.0, 110.0, 140.0, 140.0)),
        },
    )


def _front_distance_config() -> VariableConfig:
    return VariableConfig(
        name="front_distance",
        bounds=(0.0, 100.0),
        step=1.0,
        labels={
            "close": MembershipSpec("trap", (0.0, 0.0, 12.0, 30.0)),
            "medium": MembershipSpec("tri", (20.0, 50.0, 75.0)),
            "far": MembershipSpec("trap", (60.0, 80.0, 100.0, 100.0)),
        },
    )


def _road_condition_config() -> VariableConfig:
    return VariableConfig(
        name="road_condition",
        bounds=(0.0, 1.0),
        step=0.01,
        labels={
            "poor": MembershipSpec("trap", (0.0, 0.0, 0.20, 0.45)),
            "normal": MembershipSpec("tri", (0.30, 0.55, 0.80)),
            "good": MembershipSpec("trap", (0.65, 0.85, 1.0, 1.0)),
        },
    )


def _risk_level_config() -> VariableConfig:
    return VariableConfig(
        name="risk_level",
        bounds=(0.0, 100.0),
        step=1.0,
        labels={
            "low": MembershipSpec("trap", (0.0, 0.0, 15.0, 35.0)),
            "medium": MembershipSpec("tri", (25.0, 50.0, 70.0)),
            "high": MembershipSpec("tri", (60.0, 78.0, 90.0)),
            "critical": MembershipSpec("trap", (85.0, 93.0, 100.0, 100.0)),
        },
    )


def _lane_deviation_config() -> VariableConfig:
    return VariableConfig(
        name="lane_deviation",
        bounds=(-1.5, 1.5),
        step=0.01,
        labels={
            "far_left": MembershipSpec("trap", (-1.5, -1.5, -1.1, -0.6)),
            "left": MembershipSpec("tri", (-0.9, -0.45, 0.0)),
            "centered": MembershipSpec("tri", (-0.15, 0.0, 0.15)),
            "right": MembershipSpec("tri", (0.0, 0.45, 0.9)),
            "far_right": MembershipSpec("trap", (0.6, 1.1, 1.5, 1.5)),
        },
    )


def _steering_stability_config() -> VariableConfig:
    return VariableConfig(
        name="steering_stability",
        bounds=(0.0, 1.0),
        step=0.01,
        labels={
            "unstable": MembershipSpec("trap", (0.0, 0.0, 0.18, 0.42)),
            "moderate": MembershipSpec("tri", (0.30, 0.55, 0.78)),
            "stable": MembershipSpec("trap", (0.65, 0.85, 1.0, 1.0)),
        },
    )


def _lane_stability_config() -> VariableConfig:
    return VariableConfig(
        name="lane_stability",
        bounds=(0.0, 100.0),
        step=1.0,
        labels={
            "strong_left": MembershipSpec("trap", (0.0, 0.0, 10.0, 25.0)),
            "left": MembershipSpec("tri", (15.0, 30.0, 45.0)),
            "centered": MembershipSpec("tri", (40.0, 50.0, 60.0)),
            "right": MembershipSpec("tri", (55.0, 70.0, 85.0)),
            "strong_right": MembershipSpec("trap", (75.0, 90.0, 100.0, 100.0)),
        },
    )


def _road_slope_config() -> VariableConfig:
    return VariableConfig(
        name="road_slope",
        bounds=(-10.0, 10.0),
        step=0.1,
        labels={
            "downhill": MembershipSpec("trap", (-10.0, -10.0, -6.0, -1.0)),
            "flat": MembershipSpec("tri", (-2.0, 0.0, 2.0)),
            "uphill": MembershipSpec("trap", (1.0, 6.0, 10.0, 10.0)),
        },
    )


def _traffic_density_config() -> VariableConfig:
    return VariableConfig(
        name="traffic_density",
        bounds=(0.0, 1.0),
        step=0.01,
        labels={
            "light": MembershipSpec("trap", (0.0, 0.0, 0.20, 0.40)),
            "moderate": MembershipSpec("tri", (0.30, 0.50, 0.70)),
            "heavy": MembershipSpec("trap", (0.60, 0.80, 1.0, 1.0)),
        },
    )


def _comfort_efficiency_config() -> VariableConfig:
    return VariableConfig(
        name="comfort_efficiency",
        bounds=(0.0, 100.0),
        step=1.0,
        labels={
            "low": MembershipSpec("trap", (0.0, 0.0, 20.0, 40.0)),
            "medium": MembershipSpec("tri", (30.0, 50.0, 70.0)),
            "high": MembershipSpec("trap", (60.0, 80.0, 100.0, 100.0)),
        },
    )


def _throttle_command_config() -> VariableConfig:
    return VariableConfig(
        name="throttle_command",
        bounds=(0.0, 1.0),
        step=0.01,
        labels={
            "zero": MembershipSpec("trap", (0.0, 0.0, 0.04, 0.10)),
            "light": MembershipSpec("tri", (0.05, 0.20, 0.38)),
            "medium": MembershipSpec("tri", (0.30, 0.50, 0.70)),
            "strong": MembershipSpec("trap", (0.62, 0.82, 1.0, 1.0)),
        },
    )


def _brake_command_config() -> VariableConfig:
    return VariableConfig(
        name="brake_command",
        bounds=(0.0, 1.0),
        step=0.01,
        labels={
            "none": MembershipSpec("trap", (0.0, 0.0, 0.03, 0.08)),
            "light": MembershipSpec("tri", (0.05, 0.18, 0.35)),
            "medium": MembershipSpec("tri", (0.28, 0.50, 0.70)),
            "hard": MembershipSpec("trap", (0.62, 0.82, 1.0, 1.0)),
        },
    )


def _steering_correction_config() -> VariableConfig:
    return VariableConfig(
        name="steering_correction",
        bounds=(-1.0, 1.0),
        step=0.01,
        labels={
            "steer_left_hard": MembershipSpec("trap", (-1.0, -1.0, -0.8, -0.45)),
            "steer_left": MembershipSpec("tri", (-0.65, -0.30, 0.0)),
            "keep": MembershipSpec("tri", (-0.08, 0.0, 0.08)),
            "steer_right": MembershipSpec("tri", (0.0, 0.30, 0.65)),
            "steer_right_hard": MembershipSpec("trap", (0.45, 0.80, 1.0, 1.0)),
        },
    )


def get_default_fuzzy_config() -> Dict[str, Dict[str, Dict[str, VariableConfig]]]:
    """Return the existing hierarchical fuzzy configuration."""

    return {
        "collision": {
            "inputs": {
                "speed": _speed_config("speed"),
                "front_distance": _front_distance_config(),
                "road_condition": _road_condition_config(),
            },
            "outputs": {"risk_level": _risk_level_config()},
        },
        "lane": {
            "inputs": {
                "lane_deviation": _lane_deviation_config(),
                "steering_stability": _steering_stability_config(),
                "speed": _speed_config("speed"),
            },
            "outputs": {"lane_stability": _lane_stability_config()},
        },
        "comfort": {
            "inputs": {
                "road_slope": _road_slope_config(),
                "traffic_density": _traffic_density_config(),
                "current_speed": _speed_config("current_speed"),
            },
            "outputs": {"comfort_efficiency": _comfort_efficiency_config()},
        },
        "meta": {
            "inputs": {
                "risk_level": _risk_level_config(),
                "lane_stability": _lane_stability_config(),
                "comfort_efficiency": _comfort_efficiency_config(),
            },
            "outputs": {
                "throttle_command": _throttle_command_config(),
                "brake_command": _brake_command_config(),
                "steering_correction": _steering_correction_config(),
            },
        },
    }
