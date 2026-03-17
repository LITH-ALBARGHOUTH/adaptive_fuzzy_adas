"""Comfort-efficiency fuzzy engine."""

from __future__ import annotations

from typing import Dict, List

from fuzzy_systems.common import EngineResult, FuzzyRule, MamdaniEngine


class ComfortEfficiencyEngine(MamdaniEngine):
    """Hierarchical subsystem that estimates comfort-speed retention preference."""

    def __init__(self, config_bundle: Dict[str, Dict]) -> None:
        rules = {"comfort_efficiency": self._build_rules()}
        super().__init__(
            name="comfort_efficiency_engine",
            input_configs=config_bundle["inputs"],
            output_configs=config_bundle["outputs"],
            rules=rules,
            default_outputs={"comfort_efficiency": 50.0},
        )

    @staticmethod
    def _build_rules() -> List[FuzzyRule]:
        return [
            FuzzyRule(
                "r1_light_traffic_baseline",
                (("traffic_density", "light"),),
                ("comfort_efficiency", "high"),
                "Light traffic supports a comfort-oriented pace as a baseline.",
            ),
            FuzzyRule(
                "r2_moderate_traffic_baseline",
                (("traffic_density", "moderate"),),
                ("comfort_efficiency", "medium"),
                "Moderate traffic encourages a balanced comfort-efficiency target.",
            ),
            FuzzyRule(
                "r3_heavy_traffic_baseline",
                (("traffic_density", "heavy"),),
                ("comfort_efficiency", "low"),
                "Dense traffic suppresses the desire to preserve speed.",
            ),
            FuzzyRule(
                "r4_downhill_baseline",
                (("road_slope", "downhill"),),
                ("comfort_efficiency", "high"),
                "Downhill travel naturally favors smooth momentum retention.",
                weight=0.70,
            ),
            FuzzyRule(
                "r5_flat_baseline",
                (("road_slope", "flat"),),
                ("comfort_efficiency", "medium"),
                "Flat roads produce a neutral baseline comfort target.",
                weight=0.70,
            ),
            FuzzyRule(
                "r6_uphill_baseline",
                (("road_slope", "uphill"),),
                ("comfort_efficiency", "low"),
                "Uphill travel reduces comfort-oriented speed retention.",
                weight=0.75,
            ),
            FuzzyRule(
                "r7_flat_light_mediumspeed",
                (("road_slope", "flat"), ("traffic_density", "light"), ("current_speed", "medium")),
                ("comfort_efficiency", "high"),
                "Flat road, light traffic, and cruise speed favor maintaining pace.",
            ),
            FuzzyRule(
                "r8_flat_moderate_mediumspeed",
                (("road_slope", "flat"), ("traffic_density", "moderate"), ("current_speed", "medium")),
                ("comfort_efficiency", "high"),
                "Moderate traffic still supports efficient cruising on flat terrain.",
            ),
            FuzzyRule(
                "r9_uphill_heavy",
                (("road_slope", "uphill"), ("traffic_density", "heavy")),
                ("comfort_efficiency", "low"),
                "Uphill driving in dense traffic discourages aggressive pace keeping.",
            ),
            FuzzyRule(
                "r10_uphill_highspeed",
                (("road_slope", "uphill"), ("current_speed", "high")),
                ("comfort_efficiency", "low"),
                "High-speed uphill travel reduces comfort and efficiency.",
            ),
            FuzzyRule(
                "r11_uphill_light_lowspeed",
                (("road_slope", "uphill"), ("traffic_density", "light"), ("current_speed", "low")),
                ("comfort_efficiency", "medium"),
                "Low speed on an uphill road can remain balanced when traffic is light.",
            ),
            FuzzyRule(
                "r12_downhill_light_mediumspeed",
                (("road_slope", "downhill"), ("traffic_density", "light"), ("current_speed", "medium")),
                ("comfort_efficiency", "high"),
                "A mild downhill with light traffic favors smooth momentum retention.",
            ),
            FuzzyRule(
                "r13_downhill_highspeed",
                (("road_slope", "downhill"), ("current_speed", "high")),
                ("comfort_efficiency", "medium"),
                "Downhill motion at high speed should moderate comfort-driven acceleration.",
            ),
            FuzzyRule(
                "r14_heavy_highspeed",
                (("traffic_density", "heavy"), ("current_speed", "high")),
                ("comfort_efficiency", "low"),
                "Dense traffic at high speed should suppress efficiency bias.",
            ),
            FuzzyRule(
                "r15_heavy_lowspeed",
                (("traffic_density", "heavy"), ("current_speed", "low")),
                ("comfort_efficiency", "medium"),
                "Low speed in heavy traffic supports a balanced, patient style.",
            ),
            FuzzyRule(
                "r16_flat_heavy_lowspeed",
                (("road_slope", "flat"), ("traffic_density", "heavy"), ("current_speed", "low")),
                ("comfort_efficiency", "medium"),
                "Flat roads remove some burden, but traffic still constrains comfort bias.",
            ),
            FuzzyRule(
                "r17_flat_light_highspeed",
                (("road_slope", "flat"), ("traffic_density", "light"), ("current_speed", "high")),
                ("comfort_efficiency", "medium"),
                "Open road invites pace keeping, but very high speed softens the comfort target.",
            ),
            FuzzyRule(
                "r18_downhill_moderate_lowspeed",
                (("road_slope", "downhill"), ("traffic_density", "moderate"), ("current_speed", "low")),
                ("comfort_efficiency", "high"),
                "Gentle downhill motion at low speed and moderate traffic invites smooth acceleration.",
                weight=0.90,
            ),
        ]

    def evaluate(
        self,
        road_slope: float,
        traffic_density: float,
        current_speed: float,
    ) -> EngineResult:
        """Evaluate comfort-efficiency preference."""

        return self.compute(
            {
                "road_slope": road_slope,
                "traffic_density": traffic_density,
                "current_speed": current_speed,
            }
        )
