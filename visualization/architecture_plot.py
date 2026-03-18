"""Architecture diagram plotting for the hierarchical fuzzy ADAS project."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from config import PlotConfig
from visualization.plot_style import apply_plot_style


def _box(ax, xy, width, height, label, facecolor):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.6,
        edgecolor="#243447",
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2.0,
        xy[1] + height / 2.0,
        label,
        ha="center",
        va="center",
        fontsize=11,
        weight="bold",
    )


def _arrow(ax, start, end):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=1.8,
            color="#243447",
        )
    )


def plot_system_architecture_diagram(output_dir: Path, plot_config: PlotConfig) -> None:
    """Generate a block diagram for the hierarchical fuzzy controller."""

    apply_plot_style(plot_config)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    _box(ax, (0.05, 0.40), 0.20, 0.18, "Sensor Inputs\nspeed, distance,\nlane, road, slope,\ntraffic, stability", "#d7ebff")
    _box(ax, (0.34, 0.70), 0.22, 0.14, "Collision Risk\nEngine", "#ffe1d6")
    _box(ax, (0.34, 0.43), 0.22, 0.14, "Lane Stability\nEngine", "#e5f7da")
    _box(ax, (0.34, 0.16), 0.22, 0.14, "Comfort / Efficiency\nEngine", "#fff0c9")
    _box(ax, (0.66, 0.42), 0.20, 0.18, "Meta Decision\nEngine", "#eadcff")
    _box(ax, (0.88, 0.42), 0.10, 0.18, "Vehicle\nDynamics", "#dce8f0")

    ax.text(0.60, 0.63, "risk level", fontsize=10, ha="center")
    ax.text(0.60, 0.50, "lane stability", fontsize=10, ha="center")
    ax.text(0.60, 0.37, "comfort-efficiency", fontsize=10, ha="center")
    ax.text(0.77, 0.64, "throttle", fontsize=10, ha="center")
    ax.text(0.77, 0.52, "brake", fontsize=10, ha="center")
    ax.text(0.77, 0.40, "steering", fontsize=10, ha="center")

    _arrow(ax, (0.25, 0.49), (0.34, 0.77))
    _arrow(ax, (0.25, 0.49), (0.34, 0.50))
    _arrow(ax, (0.25, 0.49), (0.34, 0.23))
    _arrow(ax, (0.56, 0.77), (0.66, 0.57))
    _arrow(ax, (0.56, 0.50), (0.66, 0.51))
    _arrow(ax, (0.56, 0.23), (0.66, 0.45))
    _arrow(ax, (0.86, 0.51), (0.88, 0.51))
    _arrow(ax, (0.93, 0.42), (0.15, 0.40))

    ax.text(
        0.52,
        0.93,
        "Hierarchical Fuzzy ADAS Architecture",
        ha="center",
        fontsize=plot_config.title_font_size,
        weight="bold",
    )
    ax.text(
        0.53,
        0.07,
        "Closed-loop flow: sensor inputs -> subsystem fuzzification/inference -> meta arbitration -> vehicle response -> new inputs",
        ha="center",
        fontsize=plot_config.annotation_font_size,
    )

    fig.tight_layout(pad=1.2)
    fig.savefig(output_dir / "system_architecture_diagram.png", dpi=plot_config.dpi)
    plt.close(fig)
