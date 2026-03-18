"""Rule activation visualization for explainable fuzzy inference."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np

from config import PlotConfig
from utils import SimulationStepRecord
from visualization.plot_style import apply_plot_style, style_axis


def _pretty_rule_label(rule_name: str, width: int = 20) -> str:
    """Convert long internal rule ids into wrapped plot labels."""

    label = rule_name.replace("_", " ")
    return textwrap.fill(label, width=width)


def _plot_activation_bars(ax, title, activations, plot_config: PlotConfig) -> None:
    ranked = sorted(activations, key=lambda item: item.firing_strength, reverse=True)[:8]
    names = [_pretty_rule_label(activation.rule_name) for activation in ranked]
    values = [activation.firing_strength for activation in ranked]
    y_pos = np.arange(len(ranked))

    ax.barh(y_pos, values, color="tab:blue", alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.0)
    ax.set_title(title)
    ax.set_xlabel("firing strength")
    ax.grid(axis="x", alpha=0.25)
    style_axis(ax, plot_config)


def plot_rule_activation_overview(
    record: SimulationStepRecord,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Plot rule firing strengths for a representative simulation step."""

    apply_plot_style(plot_config)
    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    axes = axes.flatten()

    _plot_activation_bars(
        axes[0],
        "Collision Risk Rules",
        record.engine_results["risk"].output("risk_level").activations,
        plot_config,
    )
    _plot_activation_bars(
        axes[1],
        "Lane Stability Rules",
        record.engine_results["lane"].output("lane_stability").activations,
        plot_config,
    )
    _plot_activation_bars(
        axes[2],
        "Comfort Efficiency Rules",
        record.engine_results["comfort"].output("comfort_efficiency").activations,
        plot_config,
    )
    _plot_activation_bars(
        axes[3],
        "Meta Brake Rules",
        record.engine_results["meta"].output("brake_command").activations,
        plot_config,
    )

    fig.suptitle(
        "Rule Activation Overview for One Controller Evaluation",
        fontsize=plot_config.title_font_size,
    )
    fig.subplots_adjust(left=0.25, right=0.98, top=0.90, bottom=0.08, wspace=0.55, hspace=0.35)
    fig.savefig(output_dir / "rule_activation_overview.png", dpi=plot_config.dpi)
    plt.close(fig)
