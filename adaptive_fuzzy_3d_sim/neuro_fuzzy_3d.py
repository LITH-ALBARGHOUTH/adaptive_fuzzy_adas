"""Mamdani-compatible neuro-fuzzy adaptation for the 3D driving demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np


@dataclass
class NeuroFuzzyConfig3D:
    """Training settings for the 3D Mamdani-compatible adaptation pass."""

    epochs: int = 4
    learning_rate: float = 0.05
    sample_dt: float = 0.25
    min_rule_weight: float = 0.05
    max_rule_weight: float = 1.00


@dataclass
class NeuroFuzzyTrainingReport3D:
    """Small summary returned after 3D pre-adaptation."""

    sample_count: int
    epochs: int
    baseline_loss: float
    adapted_loss: float
    top_rule_changes: List[Tuple[str, str, float, float]]


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(value, upper)))


def _membership_center(universe: np.ndarray, membership: np.ndarray) -> float:
    denominator = float(np.trapezoid(membership, universe))
    if denominator <= 1e-9:
        return float(np.mean([universe[0], universe[-1]]))
    numerator = float(np.trapezoid(universe * membership, universe))
    return numerator / denominator


def _risk_target(sample: Dict[str, float]) -> float:
    speed_kph = sample["speed_mps"] * 3.6
    closeness = 1.0 - _clamp(sample["front_distance_m"] / 85.0, 0.0, 1.0)
    speed_factor = _clamp(speed_kph / 130.0, 0.0, 1.0)
    poor_road = 1.0 - _clamp(sample["road_condition"], 0.0, 1.0)

    score = (0.56 * closeness) + (0.28 * speed_factor) + (0.16 * poor_road)
    if sample["front_distance_m"] < 20.0 and speed_kph > 85.0:
        score += 0.16
    if sample["road_condition"] < 0.35:
        score += 0.08
    return _clamp(score * 100.0, 0.0, 100.0)


def _lane_target(sample: Dict[str, float]) -> float:
    speed_kph = sample["speed_mps"] * 3.6
    deviation = _clamp(sample["lane_deviation_m"] / 1.20, -1.0, 1.0)
    speed_factor = 0.60 + (0.40 * _clamp(speed_kph / 120.0, 0.0, 1.0))
    instability = 1.0 - _clamp(sample["steering_stability"], 0.0, 1.0)
    urgency = 42.0 * speed_factor * (0.70 + (0.30 * instability))
    return _clamp(50.0 - (deviation * urgency), 0.0, 100.0)


def _comfort_target(sample: Dict[str, float]) -> float:
    speed_kph = sample["speed_mps"] * 3.6
    slope = sample["slope"]
    traffic = _clamp(sample["traffic_density"], 0.0, 1.0)

    base = 64.0
    downhill_bonus = 12.0 * _clamp(-slope / 6.0, 0.0, 1.0)
    uphill_penalty = 20.0 * _clamp(slope / 8.0, 0.0, 1.0)
    traffic_penalty = 28.0 * traffic
    overspeed_penalty = 10.0 * _clamp((speed_kph - 95.0) / 35.0, 0.0, 1.0)
    return _clamp(base + downhill_bonus - uphill_penalty - traffic_penalty - overspeed_penalty, 0.0, 100.0)


def _meta_targets(sample: Dict[str, float], risk: float, lane: float, comfort: float) -> Dict[str, float]:
    risk_ratio = risk / 100.0
    lane_urgency = abs(lane - 50.0) / 50.0
    comfort_ratio = comfort / 100.0

    throttle = _clamp(
        (0.68 * comfort_ratio) + (0.16 * (1.0 - risk_ratio)) - (0.60 * risk_ratio) - (0.28 * lane_urgency),
        0.0,
        1.0,
    )
    brake = _clamp(
        (0.78 * risk_ratio) + (0.32 * lane_urgency) - (0.18 * comfort_ratio),
        0.0,
        1.0,
    )
    steering = _clamp((lane - 50.0) / 45.0, -1.0, 1.0)
    return {
        "throttle_command": throttle,
        "brake_command": brake,
        "steering_correction": steering,
    }


def _output_targets(sample: Dict[str, float]) -> Dict[str, float]:
    risk = _risk_target(sample)
    lane = _lane_target(sample)
    comfort = _comfort_target(sample)
    meta = _meta_targets(sample, risk, lane, comfort)
    return {
        "risk_level": risk,
        "lane_stability": lane,
        "comfort_efficiency": comfort,
        **meta,
    }


def _build_training_samples(scenarios: Iterable, sample_dt: float) -> List[Dict[str, float]]:
    samples: List[Dict[str, float]] = []
    for scenario in scenarios:
        ego_speed = scenario.ego_initial.speed_mps
        lane_deviation = scenario.ego_initial.lateral_x
        steering_stability = 0.88
        front_speed = scenario.front_initial.speed_mps
        front_distance = max(8.0, scenario.front_initial.forward_z - scenario.ego_initial.forward_z)

        t = 0.0
        while t < scenario.duration_s:
            env = scenario.environment_profile(t)
            samples.append(
                {
                    "speed_mps": ego_speed,
                    "front_distance_m": front_distance,
                    "lane_deviation_m": lane_deviation,
                    "steering_stability": steering_stability,
                    "road_condition": env.road_condition,
                    "slope": env.slope,
                    "traffic_density": env.traffic_density,
                }
            )

            lane_deviation = (lane_deviation * 0.94) + (scenario.lane_disturbance_profile(t) * sample_dt)
            front_acc = scenario.front_acceleration_profile(t, scenario.front_initial)
            front_speed = _clamp(front_speed + (front_acc * sample_dt), 0.0, 40.0)
            ego_speed = _clamp(
                ego_speed + ((0.20 * (front_speed - ego_speed)) - (0.07 * max(env.slope, 0.0))) * sample_dt,
                0.0,
                40.0,
            )
            front_distance = _clamp(front_distance + ((front_speed - ego_speed) * sample_dt), 6.0, 120.0)
            steering_stability = _clamp(0.92 - min(abs(lane_deviation) * 0.20, 0.35), 0.45, 0.95)
            t += sample_dt

    return samples


def _snapshot_rule_weights(controller) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for engine_name, engine in (
        ("risk", controller.risk_engine),
        ("lane", controller.lane_engine),
        ("comfort", controller.comfort_engine),
        ("meta", controller.meta_engine),
    ):
        for output_name, rules in engine.rules.items():
            for rule in rules:
                weights[f"{engine_name}.{output_name}.{rule.name}"] = rule.weight
    return weights


def _adapt_engine_output(engine, output_name: str, result, target: float, config: NeuroFuzzyConfig3D) -> None:
    explanation = result.output(output_name)
    actual = explanation.crisp_value
    output_variable = engine.output_variables[output_name]
    output_min = float(output_variable.universe[0])
    output_max = float(output_variable.universe[-1])
    value_range = max(output_max - output_min, 1e-6)
    normalized_error = abs(target - actual) / value_range

    for rule, activation in zip(engine.rules[output_name], explanation.activations):
        if activation.firing_strength <= 1e-9:
            continue

        label_center = _membership_center(
            output_variable.universe,
            output_variable.terms[rule.consequent[1]],
        )
        alignment = np.sign((label_center - actual) * (target - actual))
        if alignment == 0.0:
            continue

        delta = (
            config.learning_rate
            * activation.firing_strength
            * normalized_error
            * float(alignment)
        )
        rule.weight = _clamp(
            rule.weight + delta,
            config.min_rule_weight,
            config.max_rule_weight,
        )


def _evaluate_loss(controller, samples: Iterable[Dict[str, float]]) -> float:
    total = 0.0
    count = 0
    for sample in samples:
        targets = _output_targets(sample)
        speed_kph = sample["speed_mps"] * 3.6
        risk_result = controller.risk_engine.evaluate(
            speed=speed_kph,
            front_distance=sample["front_distance_m"],
            road_condition=sample["road_condition"],
        )
        lane_result = controller.lane_engine.evaluate(
            lane_deviation=sample["lane_deviation_m"],
            steering_stability=sample["steering_stability"],
            speed=speed_kph,
        )
        comfort_result = controller.comfort_engine.evaluate(
            road_slope=sample["slope"],
            traffic_density=sample["traffic_density"],
            current_speed=speed_kph,
        )
        meta_result = controller.meta_engine.evaluate(
            risk_level=risk_result.crisp_outputs["risk_level"],
            lane_stability=lane_result.crisp_outputs["lane_stability"],
            comfort_efficiency=comfort_result.crisp_outputs["comfort_efficiency"],
        )

        total += abs(risk_result.crisp_outputs["risk_level"] - targets["risk_level"]) / 100.0
        total += abs(lane_result.crisp_outputs["lane_stability"] - targets["lane_stability"]) / 100.0
        total += abs(comfort_result.crisp_outputs["comfort_efficiency"] - targets["comfort_efficiency"]) / 100.0
        total += abs(meta_result.crisp_outputs["throttle_command"] - targets["throttle_command"])
        total += abs(meta_result.crisp_outputs["brake_command"] - targets["brake_command"])
        total += abs(meta_result.crisp_outputs["steering_correction"] - targets["steering_correction"]) / 2.0
        count += 6

    if count == 0:
        return 0.0
    return total / count


def _largest_weight_changes(controller, baseline_weights: Dict[str, float], limit: int = 6) -> List[Tuple[str, str, float, float]]:
    changes: List[Tuple[str, str, float, float]] = []
    for engine_name, engine in (
        ("risk", controller.risk_engine),
        ("lane", controller.lane_engine),
        ("comfort", controller.comfort_engine),
        ("meta", controller.meta_engine),
    ):
        for output_name, rules in engine.rules.items():
            for rule in rules:
                key = f"{engine_name}.{output_name}.{rule.name}"
                before = baseline_weights[key]
                after = rule.weight
                changes.append((key, rule.description, before, after))
    changes.sort(key=lambda item: abs(item[3] - item[2]), reverse=True)
    return changes[:limit]


def train_neuro_fuzzy_adapter_3d(controller, scenarios: Iterable, config: NeuroFuzzyConfig3D | None = None) -> NeuroFuzzyTrainingReport3D:
    """Adapt the 3D demo Mamdani rule weights from scenario-derived samples."""

    config = config or NeuroFuzzyConfig3D()
    baseline_weights = _snapshot_rule_weights(controller)
    samples = _build_training_samples(scenarios, config.sample_dt)
    baseline_loss = _evaluate_loss(controller, samples)

    for _epoch in range(config.epochs):
        for sample in samples:
            targets = _output_targets(sample)
            speed_kph = sample["speed_mps"] * 3.6

            risk_result = controller.risk_engine.evaluate(
                speed=speed_kph,
                front_distance=sample["front_distance_m"],
                road_condition=sample["road_condition"],
            )
            _adapt_engine_output(controller.risk_engine, "risk_level", risk_result, targets["risk_level"], config)

            lane_result = controller.lane_engine.evaluate(
                lane_deviation=sample["lane_deviation_m"],
                steering_stability=sample["steering_stability"],
                speed=speed_kph,
            )
            _adapt_engine_output(controller.lane_engine, "lane_stability", lane_result, targets["lane_stability"], config)

            comfort_result = controller.comfort_engine.evaluate(
                road_slope=sample["slope"],
                traffic_density=sample["traffic_density"],
                current_speed=speed_kph,
            )
            _adapt_engine_output(
                controller.comfort_engine,
                "comfort_efficiency",
                comfort_result,
                targets["comfort_efficiency"],
                config,
            )

            risk_level = controller.risk_engine.evaluate(
                speed=speed_kph,
                front_distance=sample["front_distance_m"],
                road_condition=sample["road_condition"],
            ).crisp_outputs["risk_level"]
            lane_level = controller.lane_engine.evaluate(
                lane_deviation=sample["lane_deviation_m"],
                steering_stability=sample["steering_stability"],
                speed=speed_kph,
            ).crisp_outputs["lane_stability"]
            comfort_level = controller.comfort_engine.evaluate(
                road_slope=sample["slope"],
                traffic_density=sample["traffic_density"],
                current_speed=speed_kph,
            ).crisp_outputs["comfort_efficiency"]
            meta_result = controller.meta_engine.evaluate(
                risk_level=risk_level,
                lane_stability=lane_level,
                comfort_efficiency=comfort_level,
            )
            _adapt_engine_output(controller.meta_engine, "throttle_command", meta_result, targets["throttle_command"], config)
            _adapt_engine_output(controller.meta_engine, "brake_command", meta_result, targets["brake_command"], config)
            _adapt_engine_output(
                controller.meta_engine,
                "steering_correction",
                meta_result,
                targets["steering_correction"],
                config,
            )

    adapted_loss = _evaluate_loss(controller, samples)
    return NeuroFuzzyTrainingReport3D(
        sample_count=len(samples),
        epochs=config.epochs,
        baseline_loss=baseline_loss,
        adapted_loss=adapted_loss,
        top_rule_changes=_largest_weight_changes(controller, baseline_weights),
    )


def format_training_report_3d(report: NeuroFuzzyTrainingReport3D) -> str:
    """Build a concise terminal summary for the 3D startup pass."""

    lines = [
        "=" * 88,
        "3D neuro-fuzzy uyarlama özeti",
        (
            f"örnek={report.sample_count}, epoch={report.epochs}, "
            f"başlangıç_kayıp={report.baseline_loss:.4f}, uyarlanmış_kayıp={report.adapted_loss:.4f}"
        ),
        "En büyük kural ağırlığı değişimleri:",
    ]
    for key, description, before, after in report.top_rule_changes:
        lines.append(f"  {key}: {before:.3f} -> {after:.3f} | {description}")
    return "\n".join(lines)
