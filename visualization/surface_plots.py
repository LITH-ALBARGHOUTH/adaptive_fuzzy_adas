"""Surface and contour plots for fuzzy-engine responses."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from config import PlotConfig
from simulation import HierarchicalFuzzyADASController
from visualization.plot_style import apply_plot_style, style_axis


def plot_collision_risk_surface(
    controller: HierarchicalFuzzyADASController,
    output_dir: Path,
    plot_config: PlotConfig,
    road_condition: float = 0.55,
) -> None:
    """Generate a 3D surface for collision risk over speed and distance."""

    apply_plot_style(plot_config)
    speeds = np.linspace(0.0, 140.0, plot_config.surface_grid_points)
    distances = np.linspace(0.0, 100.0, plot_config.surface_grid_points)
    speed_grid, distance_grid = np.meshgrid(speeds, distances)
    risk_grid = np.zeros_like(speed_grid)

    for i in range(speed_grid.shape[0]):
        for j in range(speed_grid.shape[1]):
            risk_grid[i, j] = controller.risk_engine.evaluate(
                speed=float(speed_grid[i, j]),
                front_distance=float(distance_grid[i, j]),
                road_condition=road_condition,
            ).crisp_outputs["risk_level"]

    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection="3d")
    surface = ax.plot_surface(speed_grid, distance_grid, risk_grid, cmap="viridis", edgecolor="none")
    ax.set_title("Sabit Yol Koşulunda Çarpışma Riski Yüzeyi")
    ax.set_xlabel("hız (km/h)")
    ax.set_ylabel("ön mesafe (m)")
    ax.set_zlabel("risk seviyesi")
    fig.colorbar(surface, shrink=0.7, aspect=12, label="risk seviyesi")
    ax.tick_params(axis="both", labelsize=plot_config.tick_font_size)
    fig.tight_layout(pad=1.2)
    fig.savefig(output_dir / "surface_collision_risk.png", dpi=plot_config.dpi)
    plt.close(fig)


def plot_meta_brake_contour(
    controller: HierarchicalFuzzyADASController,
    output_dir: Path,
    plot_config: PlotConfig,
    comfort_efficiency: float = 65.0,
) -> None:
    """Generate a contour plot for brake command over risk and lane index."""

    apply_plot_style(plot_config)
    risks = np.linspace(0.0, 100.0, plot_config.surface_grid_points)
    lane_indices = np.linspace(0.0, 100.0, plot_config.surface_grid_points)
    risk_grid, lane_grid = np.meshgrid(risks, lane_indices)
    brake_grid = np.zeros_like(risk_grid)

    for i in range(risk_grid.shape[0]):
        for j in range(risk_grid.shape[1]):
            brake_grid[i, j] = controller.meta_engine.evaluate(
                risk_level=float(risk_grid[i, j]),
                lane_stability=float(lane_grid[i, j]),
                comfort_efficiency=comfort_efficiency,
            ).crisp_outputs["brake_command"]

    fig, ax = plt.subplots(figsize=(9, 6))
    contour = ax.contourf(risk_grid, lane_grid, brake_grid, levels=18, cmap="magma")
    ax.set_title("Meta Fren Komutu Kontur Grafiği")
    ax.set_xlabel("risk seviyesi")
    ax.set_ylabel("şerit kararlılığı indeksi")
    fig.colorbar(contour, ax=ax, label="fren komutu")
    style_axis(ax, plot_config)
    fig.tight_layout(pad=1.2)
    fig.savefig(output_dir / "contour_meta_brake.png", dpi=plot_config.dpi)
    plt.close(fig)
