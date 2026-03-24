"""Scenario plotting utilities for the time-based simulation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt

from config import PlotConfig
from utils import SimulationResult
from visualization.plot_style import apply_plot_style, style_axis


def _scenario_label(name: str) -> str:
    """Shorten scenario names for crowded legends."""

    labels = {
        "normal_driving": "normal sürüş",
        "high_speed_short_distance": "yüksek hız kısa mesafe",
        "large_lane_deviation": "büyük şerit sapması",
        "poor_road_condition": "kötü yol",
        "conflicting_tradeoff": "çatışmalı karar",
        "boundary_stop_and_go": "dur kalk",
        "boundary_open_road": "açık yol",
        "uphill_grade_challenge": "yokuş tırmanışı",
    }
    return labels.get(name, name.replace("_", " "))


def plot_scenario_timeseries(
    result: SimulationResult,
    output_dir: Path,
    plot_config: PlotConfig,
) -> Path:
    """Generate the required per-scenario time-series plots."""

    apply_plot_style(plot_config)
    time = [record.time_s for record in result.records]
    speed = [record.sensor_inputs["speed"] for record in result.records]
    distance = [record.sensor_inputs["distance"] for record in result.records]
    risk = [record.subsystem_outputs["risk"] for record in result.records]
    lane_deviation = [record.sensor_inputs["lane_deviation"] for record in result.records]
    throttle = [record.final_command_outputs["throttle"] for record in result.records]
    brake = [record.final_command_outputs["brake"] for record in result.records]
    steering = [record.final_command_outputs["steering"] for record in result.records]

    figure, axes = plt.subplots(5, 1, figsize=plot_config.figure_size, sharex=True)

    axes[0].plot(time, speed, color="tab:blue", label="ego hızı")
    axes[0].set_title(f"{_scenario_label(result.scenario.name).title()}: Hıza Göre Zaman")
    axes[0].set_ylabel("hız (m/s)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    style_axis(axes[0], plot_config)

    axes[1].plot(time, distance, color="tab:orange", label="on mesafe")
    axes[1].set_title("Mesafeye Göre Zaman")
    axes[1].set_ylabel("mesafe (m)")
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    style_axis(axes[1], plot_config)

    axes[2].plot(time, risk, color="tab:red", label="risk")
    axes[2].set_title("Riske Göre Zaman")
    axes[2].set_ylabel("risk")
    axes[2].legend()
    axes[2].grid(alpha=0.25)
    style_axis(axes[2], plot_config)

    axes[3].plot(time, lane_deviation, color="tab:green", label="şerit sapması")
    axes[3].set_title("Şerit Sapmasına Göre Zaman")
    axes[3].set_ylabel("şerit sapması (m)")
    axes[3].legend()
    axes[3].grid(alpha=0.25)
    style_axis(axes[3], plot_config)

    axes[4].plot(time, throttle, label="gaz", color="tab:purple")
    axes[4].plot(time, brake, label="fren", color="tab:brown")
    axes[4].plot(time, steering, label="direksiyon", color="tab:gray")
    axes[4].set_title("Kontrol Sinyallerine Göre Zaman")
    axes[4].set_xlabel("zaman (s)")
    axes[4].set_ylabel("komut")
    axes[4].legend()
    axes[4].grid(alpha=0.25)
    style_axis(axes[4], plot_config)

    figure.tight_layout(pad=1.4)
    output_path = output_dir / f"{result.scenario.name}_timeseries.png"
    figure.savefig(output_path, dpi=plot_config.dpi)
    plt.close(figure)
    return output_path


def plot_scenario_comparison(
    results: Dict[str, SimulationResult],
    output_dir: Path,
    plot_config: PlotConfig,
) -> Path:
    """Generate an optional comparison plot across multiple scenarios."""

    apply_plot_style(plot_config)
    figure, axes = plt.subplots(2, 2, figsize=(16, 11), sharex=False)
    axes = axes.flatten()

    for scenario_name, result in results.items():
        time = [record.time_s for record in result.records]
        speed = [record.sensor_inputs["speed"] for record in result.records]
        distance = [record.sensor_inputs["distance"] for record in result.records]
        risk = [record.subsystem_outputs["risk"] for record in result.records]
        lane = [record.sensor_inputs["lane_deviation"] for record in result.records]

        label = _scenario_label(scenario_name)
        axes[0].plot(time, speed, label=label)
        axes[1].plot(time, distance, label=label)
        axes[2].plot(time, risk, label=label)
        axes[3].plot(time, lane, label=label)

    axes[0].set_title("Hız Karşılaştırması")
    axes[0].set_ylabel("hız (m/s)")
    axes[1].set_title("Mesafe Karşılaştırması")
    axes[1].set_ylabel("mesafe (m)")
    axes[2].set_title("Risk Karşılaştırması")
    axes[2].set_ylabel("risk")
    axes[3].set_title("Şerit Sapması Karşılaştırması")
    axes[3].set_ylabel("şerit sapması (m)")

    for axis in axes:
        axis.set_xlabel("zaman (s)")
        axis.legend(fontsize=plot_config.legend_font_size, loc="best", framealpha=0.92)
        axis.grid(alpha=0.25)
        style_axis(axis, plot_config)

    figure.tight_layout(pad=1.8, w_pad=1.8, h_pad=1.8)
    output_path = output_dir / "scenario_comparison.png"
    figure.savefig(output_path, dpi=plot_config.dpi)
    plt.close(figure)
    return output_path
