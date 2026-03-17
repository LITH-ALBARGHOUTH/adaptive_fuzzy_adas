"""Lane-stability fuzzy engine."""

from __future__ import annotations

from typing import Dict, List

from fuzzy_systems.common import EngineResult, FuzzyRule, MamdaniEngine


class LaneStabilityEngine(MamdaniEngine):
    """Hierarchical subsystem that encodes steering urgency on a 0-100 scale."""

    def __init__(self, config_bundle: Dict[str, Dict]) -> None:
        rules = {"lane_stability": self._build_rules()}
        super().__init__(
            name="lane_stability_engine",
            input_configs=config_bundle["inputs"],
            output_configs=config_bundle["outputs"],
            rules=rules,
            default_outputs={"lane_stability": 50.0},
        )

    @staticmethod
    def _build_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "r1_farleft_baseline",
                (("lane_deviation", "far_left"),),
                ("lane_stability", "strong_right"),
                "A large left offset requires a strong right correction as a baseline.",
            ),
            FuzzyRule(
                "r2_left_baseline",
                (("lane_deviation", "left"),),
                ("lane_stability", "right"),
                "A left offset should request a right correction.",
            ),
            FuzzyRule(
                "r3_centered_baseline",
                (("lane_deviation", "centered"),),
                ("lane_stability", "centered"),
                "A centered vehicle should default to lane keeping.",
            ),
            FuzzyRule(
                "r4_right_baseline",
                (("lane_deviation", "right"),),
                ("lane_stability", "left"),
                "A right offset should request a left correction.",
            ),
            FuzzyRule(
                "r5_farright_baseline",
                (("lane_deviation", "far_right"),),
                ("lane_stability", "strong_left"),
                "A large right offset requires a strong left correction as a baseline.",
            ),
            FuzzyRule(
                "r6_left_highspeed",
                (("lane_deviation", "left"), ("speed", "high")),
                ("lane_stability", "strong_right"),
                "At high speed, moderate left drift requires stronger correction.",
            ),
            FuzzyRule(
                "r7_right_highspeed",
                (("lane_deviation", "right"), ("speed", "high")),
                ("lane_stability", "strong_left"),
                "At high speed, moderate right drift requires stronger correction.",
            ),
            FuzzyRule(
                "r8_left_unstable",
                (("lane_deviation", "left"), ("steering_stability", "unstable")),
                ("lane_stability", "strong_right"),
                "Unstable steering amplifies left-drift urgency.",
            ),
            FuzzyRule(
                "r9_right_unstable",
                (("lane_deviation", "right"), ("steering_stability", "unstable")),
                ("lane_stability", "strong_left"),
                "Unstable steering amplifies right-drift urgency.",
            ),
            FuzzyRule(
                "r10_farleft_stable",
                (("lane_deviation", "far_left"), ("steering_stability", "stable")),
                ("lane_stability", "right"),
                "Stable steering allows a slightly softer recovery from far-left deviation.",
                weight=0.80,
            ),
            FuzzyRule(
                "r11_farright_stable",
                (("lane_deviation", "far_right"), ("steering_stability", "stable")),
                ("lane_stability", "left"),
                "Stable steering allows a slightly softer recovery from far-right deviation.",
                weight=0.80,
            ),
            FuzzyRule(
                "r12_farleft_highspeed",
                (("lane_deviation", "far_left"), ("speed", "high")),
                ("lane_stability", "strong_right"),
                "A large left offset at high speed remains a severe event.",
            ),
            FuzzyRule(
                "r13_farright_highspeed",
                (("lane_deviation", "far_right"), ("speed", "high")),
                ("lane_stability", "strong_left"),
                "A large right offset at high speed remains a severe event.",
            ),
            FuzzyRule(
                "r14_centered_unstable",
                (("lane_deviation", "centered"), ("steering_stability", "unstable")),
                ("lane_stability", "centered"),
                "Steering noise without lane error should not introduce a directional steering bias.",
            ),
            FuzzyRule(
                "r15_left_lowspeed_stable",
                (("lane_deviation", "left"), ("speed", "low"), ("steering_stability", "stable")),
                ("lane_stability", "right"),
                "At low speed a moderate right correction is enough for left drift.",
            ),
            FuzzyRule(
                "r16_right_lowspeed_stable",
                (("lane_deviation", "right"), ("speed", "low"), ("steering_stability", "stable")),
                ("lane_stability", "left"),
                "At low speed a moderate left correction is enough for right drift.",
            ),
        ]

    def evaluate(
        self,
        lane_deviation: float,
        steering_stability: float,
        speed: float,
    ) -> EngineResult:
        """Evaluate lane-stability index."""

        return self.compute(
            {
                "lane_deviation": lane_deviation,
                "steering_stability": steering_stability,
                "speed": speed,
            }
        )
