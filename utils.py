"""Utility models and helper functions for the time-based ADAS simulation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

import numpy as np


@dataclass
class EgoVehicleState:
    """Ego vehicle state in metric simulation units."""

    x_position: float
    y_position: float
    speed: float

    @property
    def x(self) -> float:
        return self.x_position

    @property
    def y(self) -> float:
        return self.y_position

    @property
    def speed_kph(self) -> float:
        return self.speed * 3.6


@dataclass
class FrontVehicleState:
    """Front vehicle state in metric simulation units."""

    x_position: float
    speed: float

    @property
    def x(self) -> float:
        return self.x_position

    @property
    def speed_kph(self) -> float:
        return self.speed * 3.6


@dataclass
class EnvironmentState:
    """Environment state sampled by the controller."""

    road_condition: float
    slope: float
    traffic_density: float

    @property
    def road_slope(self) -> float:
        return self.slope


@dataclass
class ScenarioExpectation:
    """Validation targets used for scenario-level test comparisons."""

    description: str
    min_max_risk: float | None = None
    max_max_risk: float | None = None
    min_peak_brake: float | None = None
    max_peak_brake: float | None = None
    min_peak_throttle: float | None = None
    max_peak_throttle: float | None = None
    min_peak_abs_steering: float | None = None
    max_peak_abs_steering: float | None = None
    max_rms_lane_deviation: float | None = None
    min_minimum_distance: float | None = None
    expect_collision: bool | None = None
    expect_lane_departure: bool | None = None


@dataclass
class ScenarioDefinition:
    """Scenario definition with dynamic callback profiles."""

    name: str
    description: str
    duration_s: float
    ego_initial: EgoVehicleState
    front_initial: FrontVehicleState
    environment_initial: EnvironmentState
    interpretation_hint: str
    front_acceleration_profile: Callable[[float, FrontVehicleState], float]
    environment_profile: Callable[[float], EnvironmentState]
    lane_disturbance_profile: Callable[[float], float]
    expectation: ScenarioExpectation | None = None


@dataclass
class SimulationStepRecord:
    """Single logged time step."""

    time_s: float
    sensor_inputs: Dict[str, float]
    subsystem_outputs: Dict[str, float]
    raw_command_outputs: Dict[str, float]
    final_command_outputs: Dict[str, float]
    ego_state: EgoVehicleState
    front_state: FrontVehicleState
    ego_state_next: EgoVehicleState
    front_state_next: FrontVehicleState
    environment_state: EnvironmentState
    engine_results: Dict[str, Any]
    collision: bool
    lane_departure: bool


@dataclass
class SimulationResult:
    """Complete scenario result."""

    scenario: ScenarioDefinition
    records: List[SimulationStepRecord]
    summary: Dict[str, Any]


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if it does not exist."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a floating-point value."""

    return float(max(lower, min(value, upper)))


def clone_state(state: Any) -> Any:
    """Deep-copy a state object."""

    return copy.deepcopy(state)


def mps_to_kph(speed_mps: float) -> float:
    """Convert meters per second to kilometers per hour."""

    return speed_mps * 3.6


def compute_steering_stability(steering_history: Sequence[float], fallback: float = 0.85) -> float:
    """Estimate a normalized steering-stability score from recent commands."""

    if len(steering_history) < 3:
        return fallback

    variability = float(np.std(np.asarray(steering_history, dtype=float)))
    stability = 1.0 - min(variability / 0.55, 1.0)
    return clamp(stability, 0.0, 1.0)


def rms(values: Sequence[float]) -> float:
    """Root-mean-square helper."""

    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(array**2)))


def select_representative_record(results: Dict[str, SimulationResult]) -> SimulationStepRecord:
    """Pick an informative record for optional explainability plots."""

    best_record: SimulationStepRecord | None = None
    best_score = -1.0

    for result in results.values():
        for record in result.records:
            score = (
                record.subsystem_outputs["risk"]
                + 70.0 * record.final_command_outputs["brake"]
                + 50.0 * abs(record.final_command_outputs["steering"])
                + 20.0 * abs(record.sensor_inputs["lane_deviation"])
            )
            if score > best_score:
                best_score = score
                best_record = record

    if best_record is None:
        raise ValueError("No simulation records are available.")

    return best_record


def build_interpretation(result: SimulationResult) -> str:
    """Generate a short interpretation of a scenario result."""

    if not result.records:
        return "The scenario produced no simulation records."

    first = result.records[0]
    final = result.records[-1]
    summary = result.summary

    if summary["collision"]:
        return "The controller could not prevent a collision in this scenario."
    if summary["lane_departure"]:
        return "The controller lost lane containment before the scenario finished."
    if summary["max_risk"] >= 70.0 or final.final_command_outputs["brake"] >= 0.5:
        return "Safety dominated the response, with braking prioritized over speed keeping."
    if abs(final.final_command_outputs["steering"]) >= 0.4 or summary["rms_lane_deviation"] >= 0.35:
        return "The controller focused on lateral recovery while keeping longitudinal commands moderate."
    if first.subsystem_outputs["comfort"] >= 65.0 and summary["max_risk"] < 60.0:
        return "The controller remained in a comfort-oriented regime and preserved speed smoothly."
    return "The controller balanced safety, lane stability, and comfort without hitting a hard limit."


def compute_result_metrics(result: SimulationResult) -> Dict[str, float | bool]:
    """Compute derived metrics used for validation and reporting."""

    peak_brake = max((record.final_command_outputs["brake"] for record in result.records), default=0.0)
    peak_throttle = max((record.final_command_outputs["throttle"] for record in result.records), default=0.0)
    peak_abs_steering = max(
        (abs(record.final_command_outputs["steering"]) for record in result.records),
        default=0.0,
    )

    return {
        "final_speed": float(result.summary["final_speed"]),
        "minimum_distance": float(result.summary["minimum_distance"]),
        "max_risk": float(result.summary["max_risk"]),
        "rms_lane_deviation": float(result.summary["rms_lane_deviation"]),
        "collision": bool(result.summary["collision"]),
        "lane_departure": bool(result.summary["lane_departure"]),
        "peak_brake": float(peak_brake),
        "peak_throttle": float(peak_throttle),
        "peak_abs_steering": float(peak_abs_steering),
    }


def print_scenario_report(result: SimulationResult) -> None:
    """Print the required scenario report."""

    if not result.records:
        print("=" * 88)
        print(f"Scenario: {result.scenario.name}")
        print("No simulation records were generated.")
        return

    first = result.records[0]
    final = result.records[-1]
    summary = result.summary

    print("=" * 88)
    print(f"Scenario: {result.scenario.name}")
    print(f"Description: {result.scenario.description}")
    print("Initial inputs:")
    print(
        "  "
        f"speed={first.sensor_inputs['speed']:.2f} m/s, "
        f"distance={first.sensor_inputs['distance']:.2f} m, "
        f"lane_deviation={first.sensor_inputs['lane_deviation']:.2f} m, "
        f"road_condition={first.sensor_inputs['road_condition']:.2f}, "
        f"slope={first.sensor_inputs['slope']:.2f}, "
        f"traffic_density={first.sensor_inputs['traffic_density']:.2f}"
    )
    print("Subsystem outputs (first step):")
    print(
        "  "
        f"risk={first.subsystem_outputs['risk']:.2f}, "
        f"lane={first.subsystem_outputs['lane']:.2f}, "
        f"comfort={first.subsystem_outputs['comfort']:.2f}"
    )
    print("Final outputs:")
    print(
        "  "
        f"throttle={final.final_command_outputs['throttle']:.3f}, "
        f"brake={final.final_command_outputs['brake']:.3f}, "
        f"steering={final.final_command_outputs['steering']:.3f}"
    )
    print(f"Interpretation: {build_interpretation(result)}")
    print("Summary:")
    print(
        "  "
        f"final_speed={summary['final_speed']:.2f} m/s, "
        f"minimum_distance={summary['minimum_distance']:.2f} m, "
        f"maximum_risk={summary['max_risk']:.2f}, "
        f"rms_lane_deviation={summary['rms_lane_deviation']:.3f} m"
    )
    print(
        "  "
        f"collision={summary['collision']}, "
        f"lane_departure={summary['lane_departure']}, "
        f"steps={summary['steps']}"
    )
    print(f"Scenario note: {result.scenario.interpretation_hint}")
