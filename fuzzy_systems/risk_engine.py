"""Collision-risk fuzzy engine."""

from __future__ import annotations

from typing import Dict, List

from fuzzy_systems.common import EngineResult, FuzzyRule, MamdaniEngine


class CollisionRiskEngine(MamdaniEngine):
    """Hierarchical subsystem that estimates collision risk."""

    def __init__(self, config_bundle: Dict[str, Dict]) -> None:
        rules = {"risk_level": self._build_rules()}
        super().__init__(
            name="collision_risk_engine",
            input_configs=config_bundle["inputs"],
            output_configs=config_bundle["outputs"],
            rules=rules,
            default_outputs={"risk_level": 50.0},
        )

    @staticmethod
    def _build_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "r1_close_baseline",
                (("front_distance", "close"),),
                ("risk_level", "high"),
                "Short spacing should already be considered high risk before other factors are added.",
            ),
            FuzzyRule(
                "r2_medium_gap_baseline",
                (("front_distance", "medium"),),
                ("risk_level", "medium"),
                "A medium following gap is a moderate baseline condition.",
            ),
            FuzzyRule(
                "r3_far_gap_baseline",
                (("front_distance", "far"),),
                ("risk_level", "low"),
                "A large following gap starts from a low-risk baseline.",
            ),
            FuzzyRule(
                "r4_high_speed_baseline",
                (("speed", "high"),),
                ("risk_level", "medium"),
                "Very high speed should raise risk even before spacing is considered.",
                weight=0.55,
            ),
            FuzzyRule(
                "r5_poor_road_baseline",
                (("road_condition", "poor"),),
                ("risk_level", "medium"),
                "Poor grip raises risk independent of spacing.",
                weight=0.65,
            ),
            FuzzyRule(
                "r6_close_highspeed",
                (("front_distance", "close"), ("speed", "high")),
                ("risk_level", "critical"),
                "Close spacing at high speed is immediately critical.",
            ),
            FuzzyRule(
                "r7_close_medspeed",
                (("front_distance", "close"), ("speed", "medium")),
                ("risk_level", "high"),
                "Close spacing at medium speed remains strongly hazardous.",
            ),
            FuzzyRule(
                "r8_close_lowspeed",
                (("front_distance", "close"), ("speed", "low")),
                ("risk_level", "medium"),
                "Short spacing at low speed is still non-negligible.",
                weight=0.85,
            ),
            FuzzyRule(
                "r9_close_poorroad",
                (("front_distance", "close"), ("road_condition", "poor")),
                ("risk_level", "critical"),
                "Poor grip turns short spacing into a critical condition.",
            ),
            FuzzyRule(
                "r10_close_normalroad",
                (("front_distance", "close"), ("road_condition", "normal")),
                ("risk_level", "high"),
                "Normal grip does not make a short headway safe.",
            ),
            FuzzyRule(
                "r11_medium_highspeed",
                (("front_distance", "medium"), ("speed", "high")),
                ("risk_level", "high"),
                "A medium gap can become risky when speed is high.",
            ),
            FuzzyRule(
                "r12_medium_medspeed_goodroad",
                (("front_distance", "medium"), ("speed", "medium"), ("road_condition", "good")),
                ("risk_level", "low"),
                "A healthy road surface makes medium spacing at cruise speed relatively safe.",
            ),
            FuzzyRule(
                "r13_medium_medspeed_poorroad",
                (("front_distance", "medium"), ("speed", "medium"), ("road_condition", "poor")),
                ("risk_level", "high"),
                "Moderate speed with degraded grip elevates a medium gap to high risk.",
            ),
            FuzzyRule(
                "r14_medium_lowspeed_goodroad",
                (("front_distance", "medium"), ("speed", "low"), ("road_condition", "good")),
                ("risk_level", "low"),
                "Low speed and good grip make a medium gap comfortable.",
            ),
            FuzzyRule(
                "r15_far_highspeed_goodroad",
                (("front_distance", "far"), ("speed", "high"), ("road_condition", "good")),
                ("risk_level", "low"),
                "A very large gap and good grip offset much of the high-speed risk.",
                weight=0.85,
            ),
            FuzzyRule(
                "r16_far_highspeed_poorroad",
                (("front_distance", "far"), ("speed", "high"), ("road_condition", "poor")),
                ("risk_level", "medium"),
                "Poor grip keeps some residual risk even when spacing is large.",
            ),
            FuzzyRule(
                "r17_far_medspeed",
                (("front_distance", "far"), ("speed", "medium")),
                ("risk_level", "low"),
                "Long spacing at moderate speed should remain low risk.",
            ),
            FuzzyRule(
                "r18_far_lowspeed",
                (("front_distance", "far"), ("speed", "low")),
                ("risk_level", "low"),
                "Long spacing at low speed is safely low risk.",
            ),
        ]

    def evaluate(self, speed: float, front_distance: float, road_condition: float) -> EngineResult:
        """Evaluate collision risk."""

        return self.compute(
            {
                "speed": speed,
                "front_distance": front_distance,
                "road_condition": road_condition,
            }
        )
