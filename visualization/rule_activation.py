"""Rule activation visualization for explainable fuzzy inference."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from config import PlotConfig
from utils import SimulationStepRecord


def _plot_activation_bars(ax, title, activations) -> None:
    ranked = sorted(activations, key=lambda item: item.firing_strength, reverse=True)[:8]
    names = [activation.rule_name for activation in ranked]
    values = [activation.firing_strength for activation in ranked]
    y_pos = np.arange(len(ranked))

    ax.barh(y_pos, values, color="tab:blue", alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.0)
    ax.set_title(title)
    ax.set_xlabel("firing strength")
    ax.grid(axis="x", alpha=0.25)


def plot_rule_activation_overview(
    record: SimulationStepRecord,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Plot rule firing strengths for a representative simulation step."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()

    _plot_activation_bars(
        axes[0],
        "Collision Risk Rules",
        record.engine_results["risk"].output("risk_level").activations,
    )
    _plot_activation_bars(
        axes[1],
        "Lane Stability Rules",
        record.engine_results["lane"].output("lane_stability").activations,
    )
    _plot_activation_bars(
        axes[2],
        "Comfort Efficiency Rules",
        record.engine_results["comfort"].output("comfort_efficiency").activations,
    )
    _plot_activation_bars(
        axes[3],
        "Meta Brake Rules",
        record.engine_results["meta"].output("brake_command").activations,
    )

    fig.suptitle("Rule Activation Overview for One Controller Evaluation", fontsize=14)
    fig.tight_layout()
    fig.savefig(output_dir / "rule_activation_overview.png", dpi=plot_config.dpi)
    plt.close(fig)
