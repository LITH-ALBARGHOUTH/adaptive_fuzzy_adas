"""Scenario plotting utilities for the time-based simulation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt

from config import PlotConfig
from utils import SimulationResult


def plot_scenario_timeseries(
    result: SimulationResult,
    output_dir: Path,
    plot_config: PlotConfig,
) -> Path:
    """Generate the required per-scenario time-series plots."""

    time = [record.time_s for record in result.records]
    speed = [record.sensor_inputs["speed"] for record in result.records]
    distance = [record.sensor_inputs["distance"] for record in result.records]
    risk = [record.subsystem_outputs["risk"] for record in result.records]
    lane_deviation = [record.sensor_inputs["lane_deviation"] for record in result.records]
    throttle = [record.final_command_outputs["throttle"] for record in result.records]
    brake = [record.final_command_outputs["brake"] for record in result.records]
    steering = [record.final_command_outputs["steering"] for record in result.records]

    figure, axes = plt.subplots(5, 1, figsize=plot_config.figure_size, sharex=True)

    axes[0].plot(time, speed, color="tab:blue", label="ego speed")
    axes[0].set_title(f"{result.scenario.name}: Speed vs Time")
    axes[0].set_ylabel("speed (m/s)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].plot(time, distance, color="tab:orange", label="front distance")
    axes[1].set_title("Distance vs Time")
    axes[1].set_ylabel("distance (m)")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    axes[2].plot(time, risk, color="tab:red", label="risk")
    axes[2].set_title("Risk vs Time")
    axes[2].set_ylabel("risk")
    axes[2].legend()
    axes[2].grid(alpha=0.25)

    axes[3].plot(time, lane_deviation, color="tab:green", label="lane deviation")
    axes[3].set_title("Lane Deviation vs Time")
    axes[3].set_ylabel("lane deviation (m)")
    axes[3].legend()
    axes[3].grid(alpha=0.25)

    axes[4].plot(time, throttle, label="throttle", color="tab:purple")
    axes[4].plot(time, brake, label="brake", color="tab:brown")
    axes[4].plot(time, steering, label="steering", color="tab:gray")
    axes[4].set_title("Control Signals vs Time")
    axes[4].set_xlabel("time (s)")
    axes[4].set_ylabel("command")
    axes[4].legend()
    axes[4].grid(alpha=0.25)

    figure.tight_layout()
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

    figure, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=False)
    axes = axes.flatten()

    for scenario_name, result in results.items():
        time = [record.time_s for record in result.records]
        speed = [record.sensor_inputs["speed"] for record in result.records]
        distance = [record.sensor_inputs["distance"] for record in result.records]
        risk = [record.subsystem_outputs["risk"] for record in result.records]
        lane = [record.sensor_inputs["lane_deviation"] for record in result.records]

        axes[0].plot(time, speed, label=scenario_name)
        axes[1].plot(time, distance, label=scenario_name)
        axes[2].plot(time, risk, label=scenario_name)
        axes[3].plot(time, lane, label=scenario_name)

    axes[0].set_title("Speed Comparison")
    axes[0].set_ylabel("speed (m/s)")
    axes[1].set_title("Distance Comparison")
    axes[1].set_ylabel("distance (m)")
    axes[2].set_title("Risk Comparison")
    axes[2].set_ylabel("risk")
    axes[3].set_title("Lane Deviation Comparison")
    axes[3].set_ylabel("lane deviation (m)")

    for axis in axes:
        axis.set_xlabel("time (s)")
        axis.legend(fontsize=8)
        axis.grid(alpha=0.25)

    figure.tight_layout()
    output_path = output_dir / "scenario_comparison.png"
    figure.savefig(output_path, dpi=plot_config.dpi)
    plt.close(figure)
    return output_path
