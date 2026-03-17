"""Meta decision fuzzy engine for throttle, brake, and steering outputs."""

from __future__ import annotations

from typing import Dict, List

from fuzzy_systems.common import EngineResult, FuzzyRule, MamdaniEngine


class MetaDecisionEngine(MamdaniEngine):
    """Hierarchical top-level engine that resolves subsystem outputs."""

    def __init__(self, config_bundle: Dict[str, Dict]) -> None:
        rules = {
            "throttle_command": self._build_throttle_rules(),
            "brake_command": self._build_brake_rules(),
            "steering_correction": self._build_steering_rules(),
        }
        super().__init__(
            name="meta_decision_engine",
            input_configs=config_bundle["inputs"],
            output_configs=config_bundle["outputs"],
            rules=rules,
            default_outputs={
                "throttle_command": 0.15,
                "brake_command": 0.0,
                "steering_correction": 0.0,
            },
        )

    @staticmethod
    def _build_throttle_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "t1_critical_risk",
                (("risk_level", "critical"),),
                ("throttle_command", "zero"),
                "Critical risk removes throttle authority.",
            ),
            FuzzyRule(
                "t2_high_risk",
                (("risk_level", "high"),),
                ("throttle_command", "zero"),
                "High risk strongly suppresses throttle.",
            ),
            FuzzyRule(
                "t3_medium_risk_baseline",
                (("risk_level", "medium"),),
                ("throttle_command", "light"),
                "Medium risk should keep throttle conservative by default.",
            ),
            FuzzyRule(
                "t4_low_risk_baseline",
                (("risk_level", "low"),),
                ("throttle_command", "medium"),
                "Low risk allows moderate throttle as a baseline.",
            ),
            FuzzyRule(
                "t5_strong_left_lateral",
                (("lane_stability", "strong_left"),),
                ("throttle_command", "zero"),
                "Strong left steering demand should suppress throttle to help stabilization.",
                weight=0.85,
            ),
            FuzzyRule(
                "t6_strong_right_lateral",
                (("lane_stability", "strong_right"),),
                ("throttle_command", "zero"),
                "Strong right steering demand should suppress throttle to help stabilization.",
                weight=0.85,
            ),
            FuzzyRule(
                "t7_left_lateral",
                (("lane_stability", "left"),),
                ("throttle_command", "light"),
                "Moderate left steering demand should soften throttle.",
            ),
            FuzzyRule(
                "t8_right_lateral",
                (("lane_stability", "right"),),
                ("throttle_command", "light"),
                "Moderate right steering demand should soften throttle.",
            ),
            FuzzyRule(
                "t9_lowrisk_centered_highcomfort",
                (("risk_level", "low"), ("lane_stability", "centered"), ("comfort_efficiency", "high")),
                ("throttle_command", "strong"),
                "Low risk, centered lane, and high comfort preference invite stronger throttle.",
            ),
            FuzzyRule(
                "t10_lowrisk_centered_mediumcomfort",
                (("risk_level", "low"), ("lane_stability", "centered"), ("comfort_efficiency", "medium")),
                ("throttle_command", "medium"),
                "Low risk with balanced comfort supports moderate throttle.",
            ),
            FuzzyRule(
                "t11_lowrisk_centered_lowcomfort",
                (("risk_level", "low"), ("lane_stability", "centered"), ("comfort_efficiency", "low")),
                ("throttle_command", "light"),
                "Low comfort preference restrains throttle even when risk is low.",
            ),
            FuzzyRule(
                "t12_mediumrisk_centered_highcomfort",
                (("risk_level", "medium"), ("lane_stability", "centered"), ("comfort_efficiency", "high")),
                ("throttle_command", "medium"),
                "When only moderately risky and laterally stable, comfort can keep some throttle.",
                weight=0.85,
            ),
            FuzzyRule(
                "t13_mediumrisk_centered_mediumcomfort",
                (("risk_level", "medium"), ("lane_stability", "centered"), ("comfort_efficiency", "medium")),
                ("throttle_command", "light"),
                "Balanced medium-risk conditions justify only light throttle.",
            ),
            FuzzyRule(
                "t14_highrisk_centered_highcomfort",
                (("risk_level", "high"), ("comfort_efficiency", "high"), ("lane_stability", "centered")),
                ("throttle_command", "light"),
                "A residual comfort preference may keep only a trace of throttle when risk is high.",
                weight=0.35,
            ),
        ]

    @staticmethod
    def _build_brake_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "b1_critical_risk",
                (("risk_level", "critical"),),
                ("brake_command", "hard"),
                "Critical risk demands hard braking.",
            ),
            FuzzyRule(
                "b2_high_risk",
                (("risk_level", "high"),),
                ("brake_command", "hard"),
                "High risk requires decisive braking.",
            ),
            FuzzyRule(
                "b3_medium_risk_baseline",
                (("risk_level", "medium"),),
                ("brake_command", "light"),
                "Medium risk should produce at least light braking by default.",
            ),
            FuzzyRule(
                "b4_low_risk_baseline",
                (("risk_level", "low"),),
                ("brake_command", "none"),
                "Low risk alone does not require braking.",
            ),
            FuzzyRule(
                "b5_strong_left_lateral",
                (("lane_stability", "strong_left"),),
                ("brake_command", "medium"),
                "Severe left steering demand benefits from stabilizing braking.",
                weight=0.75,
            ),
            FuzzyRule(
                "b6_strong_right_lateral",
                (("lane_stability", "strong_right"),),
                ("brake_command", "medium"),
                "Severe right steering demand benefits from stabilizing braking.",
                weight=0.75,
            ),
            FuzzyRule(
                "b7_left_lateral",
                (("lane_stability", "left"),),
                ("brake_command", "light"),
                "Moderate left steering demand can justify light braking.",
                weight=0.65,
            ),
            FuzzyRule(
                "b8_right_lateral",
                (("lane_stability", "right"),),
                ("brake_command", "light"),
                "Moderate right steering demand can justify light braking.",
                weight=0.65,
            ),
            FuzzyRule(
                "b9_mediumrisk_strongleft",
                (("risk_level", "medium"), ("lane_stability", "strong_left")),
                ("brake_command", "medium"),
                "Medium risk with large left correction demand calls for stabilizing braking.",
            ),
            FuzzyRule(
                "b10_mediumrisk_strongright",
                (("risk_level", "medium"), ("lane_stability", "strong_right")),
                ("brake_command", "medium"),
                "Medium risk with large right correction demand calls for stabilizing braking.",
            ),
            FuzzyRule(
                "b11_highrisk_strongleft",
                (("risk_level", "high"), ("lane_stability", "strong_left")),
                ("brake_command", "hard"),
                "High risk and severe left lateral demand justify hard braking.",
            ),
            FuzzyRule(
                "b12_highrisk_strongright",
                (("risk_level", "high"), ("lane_stability", "strong_right")),
                ("brake_command", "hard"),
                "High risk and severe right lateral demand justify hard braking.",
            ),
            FuzzyRule(
                "b13_lowrisk_centered_highcomfort",
                (("risk_level", "low"), ("lane_stability", "centered"), ("comfort_efficiency", "high")),
                ("brake_command", "none"),
                "Low-risk comfortable cruising should avoid unnecessary braking.",
            ),
            FuzzyRule(
                "b14_mediumrisk_centered_highcomfort",
                (("risk_level", "medium"), ("comfort_efficiency", "high"), ("lane_stability", "centered")),
                ("brake_command", "none"),
                "Comfort introduces a competing no-brake tendency in medium risk.",
                weight=0.45,
            ),
            FuzzyRule(
                "b15_highrisk_centered_highcomfort",
                (("risk_level", "high"), ("comfort_efficiency", "high"), ("lane_stability", "centered")),
                ("brake_command", "medium"),
                "High comfort adds a softer competing brake tendency against stronger safety rules.",
                weight=0.50,
            ),
        ]

    @staticmethod
    def _build_steering_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "s1_strongleft",
                (("lane_stability", "strong_left"),),
                ("steering_correction", "steer_left_hard"),
                "A strong-left lane index maps to a hard left steering request.",
            ),
            FuzzyRule(
                "s2_left",
                (("lane_stability", "left"),),
                ("steering_correction", "steer_left"),
                "Left correction demand maps to left steering.",
            ),
            FuzzyRule(
                "s3_centered",
                (("lane_stability", "centered"),),
                ("steering_correction", "keep"),
                "Centered lane state keeps the wheel near neutral.",
            ),
            FuzzyRule(
                "s4_right",
                (("lane_stability", "right"),),
                ("steering_correction", "steer_right"),
                "Right correction demand maps to right steering.",
            ),
            FuzzyRule(
                "s5_strongright",
                (("lane_stability", "strong_right"),),
                ("steering_correction", "steer_right_hard"),
                "A strong-right lane index maps to a hard right steering request.",
            ),
            FuzzyRule(
                "s6_highrisk_strongleft",
                (("risk_level", "high"), ("lane_stability", "strong_left")),
                ("steering_correction", "steer_left"),
                "High risk tempers a hard left correction into a slightly softer maneuver.",
                weight=0.80,
            ),
            FuzzyRule(
                "s7_highrisk_strongright",
                (("risk_level", "high"), ("lane_stability", "strong_right")),
                ("steering_correction", "steer_right"),
                "High risk tempers a hard right correction into a slightly softer maneuver.",
                weight=0.80,
            ),
            FuzzyRule(
                "s8_critical_strongleft",
                (("risk_level", "critical"), ("lane_stability", "strong_left")),
                ("steering_correction", "steer_left"),
                "Critical risk discourages very abrupt steering while braking heavily.",
                weight=0.90,
            ),
            FuzzyRule(
                "s9_critical_strongright",
                (("risk_level", "critical"), ("lane_stability", "strong_right")),
                ("steering_correction", "steer_right"),
                "Critical risk discourages very abrupt steering while braking heavily.",
                weight=0.90,
            ),
            FuzzyRule(
                "s10_centered_highcomfort",
                (("lane_stability", "centered"), ("comfort_efficiency", "high")),
                ("steering_correction", "keep"),
                "High comfort preference reinforces smooth lane keeping.",
            ),
        ]

    def evaluate(
        self,
        risk_level: float,
        lane_stability: float,
        comfort_efficiency: float,
    ) -> EngineResult:
        """Evaluate meta commands."""

        return self.compute(
            {
                "risk_level": risk_level,
                "lane_stability": lane_stability,
                "comfort_efficiency": comfort_efficiency,
            }
        )
