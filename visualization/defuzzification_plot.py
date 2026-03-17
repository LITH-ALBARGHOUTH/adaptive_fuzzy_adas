"""Defuzzification visualizations for explainable fuzzy outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from config import PlotConfig
from utils import SimulationStepRecord


def _plot_output_defuzzification(explanation, title: str, output_path: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))

    for label, membership in explanation.terms.items():
        ax.plot(
            explanation.universe,
            membership,
            linestyle="--",
            linewidth=1.0,
            alpha=0.35,
            label=f"{label} term",
        )

    for activation in explanation.activations:
        if activation.firing_strength > 0.0:
            ax.fill_between(
                explanation.universe,
                0.0,
                activation.clipped_membership,
                alpha=0.10,
            )

    ax.plot(
        explanation.universe,
        explanation.aggregated_membership,
        color="black",
        linewidth=2.5,
        label="aggregated output",
    )
    ax.axvline(
        explanation.crisp_value,
        color="tab:red",
        linestyle="-",
        linewidth=2.0,
        label=f"centroid = {explanation.crisp_value:.2f}",
    )
    ax.set_title(title)
    ax.set_xlabel(explanation.output_name.replace("_", " "))
    ax.set_ylabel("membership")
    ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)


def plot_example_defuzzifications(
    record: SimulationStepRecord,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Generate defuzzification plots for representative outputs."""

    _plot_output_defuzzification(
        explanation=record.engine_results["risk"].output("risk_level"),
        title="Collision Risk Defuzzification",
        output_path=output_dir / "defuzzification_risk_level.png",
        dpi=plot_config.dpi,
    )
    _plot_output_defuzzification(
        explanation=record.engine_results["meta"].output("brake_command"),
        title="Meta Brake Defuzzification",
        output_path=output_dir / "defuzzification_brake_command.png",
        dpi=plot_config.dpi,
    )
