"""Membership and sensitivity plots."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from config import MembershipSpec, PlotConfig
from fuzzy_systems.risk_engine import CollisionRiskEngine
from simulation import HierarchicalFuzzyADASController


def plot_all_memberships(
    controller: HierarchicalFuzzyADASController,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Generate membership figures for every engine."""

    engine_map = {
        "collision": controller.risk_engine,
        "lane": controller.lane_engine,
        "comfort": controller.comfort_engine,
        "meta": controller.meta_engine,
    }

    for engine_name, engine in engine_map.items():
        variables = list(engine.input_variables.values()) + list(engine.output_variables.values())
        cols = 2
        rows = math.ceil(len(variables) / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(14, 4.2 * rows))
        axes_array = np.atleast_1d(axes).reshape(rows, cols)

        for ax, variable in zip(axes_array.flat, variables):
            for label, membership in variable.terms.items():
                ax.plot(variable.universe, membership, linewidth=2, label=label.replace("_", " "))
            ax.set_title(variable.name.replace("_", " ").title())
            ax.set_xlabel(variable.name.replace("_", " "))
            ax.set_ylabel("membership")
            ax.set_ylim(-0.02, 1.05)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8, loc="upper right")

        for ax in axes_array.flat[len(variables) :]:
            ax.axis("off")

        fig.suptitle(f"{engine_name.title()} Engine Membership Functions", fontsize=14)
        fig.tight_layout()
        fig.savefig(output_dir / f"membership_{engine_name}.png", dpi=plot_config.dpi)
        plt.close(fig)


def plot_membership_sensitivity(
    fuzzy_config,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Vary one membership parameter and plot the effect on collision risk."""

    reference_input = {"speed": 90.0, "front_distance": 26.0, "road_condition": 0.50}
    shoulder_values = np.linspace(24.0, 40.0, 20)
    risk_values = []

    for shoulder in shoulder_values:
        config_variant = copy.deepcopy(fuzzy_config)
        close_spec = config_variant["collision"]["inputs"]["front_distance"].labels["close"]
        params = list(close_spec.params)
        params[3] = float(shoulder)
        config_variant["collision"]["inputs"]["front_distance"].labels["close"] = MembershipSpec(
            shape=close_spec.shape,
            params=tuple(params),
        )
        risk_engine = CollisionRiskEngine(config_variant["collision"])
        risk_value = risk_engine.evaluate(**reference_input).crisp_outputs["risk_level"]
        risk_values.append(risk_value)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(shoulder_values, risk_values, color="tab:red", marker="o", linewidth=2)
    ax.set_title("Sensitivity of Collision Risk to Close-Distance Membership Shoulder")
    ax.set_xlabel("close-distance trapezoid upper shoulder (m)")
    ax.set_ylabel("risk_level output")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "sensitivity_collision_distance.png", dpi=plot_config.dpi)
    plt.close(fig)
