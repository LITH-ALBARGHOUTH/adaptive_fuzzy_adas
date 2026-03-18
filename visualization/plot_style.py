"""Shared plotting style helpers for readable exported figures."""

from __future__ import annotations

import matplotlib.pyplot as plt

from config import PlotConfig


def apply_plot_style(plot_config: PlotConfig) -> None:
    """Apply a readable global matplotlib style for exported figures."""

    plt.rcParams.update(
        {
            "figure.dpi": plot_config.dpi,
            "savefig.dpi": plot_config.dpi,
            "axes.titlesize": plot_config.title_font_size,
            "axes.labelsize": plot_config.label_font_size,
            "xtick.labelsize": plot_config.tick_font_size,
            "ytick.labelsize": plot_config.tick_font_size,
            "legend.fontsize": plot_config.legend_font_size,
            "figure.titlesize": plot_config.title_font_size + 1,
            "font.size": plot_config.annotation_font_size,
        }
    )


def style_axis(ax, plot_config: PlotConfig) -> None:
    """Apply consistent axis-level formatting."""

    ax.tick_params(axis="both", labelsize=plot_config.tick_font_size)

