"""Live replay window for a simulated driving scenario."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle

from config import PlotConfig
from utils import SimulationResult
from visualization.plot_style import apply_plot_style, style_axis


def show_live_simulation(
    result: SimulationResult,
    plot_config: PlotConfig,
    output_path: Path | None = None,
) -> None:
    """Show a simple animated replay of one scenario.

    The replay is intentionally lightweight: it visualizes the ego vehicle,
    front vehicle, lane boundaries, and the evolving control/risk traces.
    """

    if not result.records:
        return

    apply_plot_style(plot_config)
    times = [record.time_s for record in result.records]
    speeds = [record.ego_state_next.speed for record in result.records]
    distances = [record.front_state_next.x_position - record.ego_state_next.x_position for record in result.records]
    risks = [record.subsystem_outputs["risk"] for record in result.records]
    lane_deviations = [record.ego_state_next.y_position for record in result.records]
    throttles = [record.final_command_outputs["throttle"] for record in result.records]
    brakes = [record.final_command_outputs["brake"] for record in result.records]
    steerings = [record.final_command_outputs["steering"] for record in result.records]

    figure = plt.figure(figsize=(14, 9), constrained_layout=True)
    grid = figure.add_gridspec(3, 2, width_ratios=[1.3, 1.0], hspace=0.35, wspace=0.25)
    ax_scene = figure.add_subplot(grid[:, 0])
    ax_speed = figure.add_subplot(grid[0, 1])
    ax_risk = figure.add_subplot(grid[1, 1])
    ax_controls = figure.add_subplot(grid[2, 1])

    lane_half_width = 1.75
    scene_x_min = -10.0
    scene_x_max = 80.0
    vehicle_length = 4.2
    vehicle_width = 1.8

    ax_scene.set_title(f"Live Simulation: {result.scenario.name}")
    ax_scene.set_xlim(scene_x_min, scene_x_max)
    ax_scene.set_ylim(-3.0, 3.0)
    ax_scene.set_xlabel("relative longitudinal position (m)")
    ax_scene.set_ylabel("lateral position (m)")
    ax_scene.grid(alpha=0.2)
    style_axis(ax_scene, plot_config)

    ax_scene.axhline(0.0, color="gray", linestyle="--", linewidth=1.2, alpha=0.8)
    ax_scene.axhline(lane_half_width, color="black", linewidth=1.5)
    ax_scene.axhline(-lane_half_width, color="black", linewidth=1.5)

    ego_patch = Rectangle(
        (-vehicle_length / 2.0, -vehicle_width / 2.0),
        vehicle_length,
        vehicle_width,
        color="tab:blue",
        alpha=0.85,
        label="ego vehicle",
    )
    front_patch = Rectangle(
        (10.0 - vehicle_length / 2.0, -vehicle_width / 2.0),
        vehicle_length,
        vehicle_width,
        color="tab:orange",
        alpha=0.85,
        label="front vehicle",
    )
    ax_scene.add_patch(ego_patch)
    ax_scene.add_patch(front_patch)
    ax_scene.legend(loc="upper right")

    info_text = ax_scene.text(
        0.02,
        0.98,
        "",
        transform=ax_scene.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    rule_text = ax_scene.text(
        0.98,
        0.98,
        "",
        transform=ax_scene.transAxes,
        va="top",
        ha="right",
        fontsize=plot_config.legend_font_size,
        bbox={"boxstyle": "round", "facecolor": "#f8fbff", "alpha": 0.92},
    )

    speed_line, = ax_speed.plot([], [], color="tab:blue", linewidth=2, label="ego speed")
    distance_line, = ax_speed.plot([], [], color="tab:orange", linewidth=2, label="distance")
    ax_speed.set_title("Speed and Distance")
    ax_speed.set_xlim(times[0], times[-1] if len(times) > 1 else times[0] + 1.0)
    speed_upper = max(max(speeds, default=0.0), max(distances, default=0.0), 1.0) * 1.1
    ax_speed.set_ylim(0.0, speed_upper)
    ax_speed.set_xlabel("time (s)")
    ax_speed.set_ylabel("value")
    ax_speed.grid(alpha=0.25)
    ax_speed.legend(loc="upper right")
    style_axis(ax_speed, plot_config)

    risk_line, = ax_risk.plot([], [], color="tab:red", linewidth=2, label="risk")
    lane_line, = ax_risk.plot([], [], color="tab:green", linewidth=2, label="lane deviation")
    ax_risk.set_title("Risk and Lane Deviation")
    ax_risk.set_xlim(times[0], times[-1] if len(times) > 1 else times[0] + 1.0)
    risk_upper = max(max(risks, default=0.0), 100.0)
    lane_upper = max(abs(min(lane_deviations, default=0.0)), abs(max(lane_deviations, default=0.0)), 2.0)
    ax_risk.set_ylim(min(-2.5, -lane_upper * 1.1), max(risk_upper * 1.05, lane_upper * 1.1))
    ax_risk.set_xlabel("time (s)")
    ax_risk.set_ylabel("value")
    ax_risk.grid(alpha=0.25)
    ax_risk.legend(loc="upper right")
    style_axis(ax_risk, plot_config)

    throttle_line, = ax_controls.plot([], [], color="tab:purple", linewidth=2, label="throttle")
    brake_line, = ax_controls.plot([], [], color="tab:brown", linewidth=2, label="brake")
    steering_line, = ax_controls.plot([], [], color="tab:gray", linewidth=2, label="steering")
    ax_controls.set_title("Control Signals")
    ax_controls.set_xlim(times[0], times[-1] if len(times) > 1 else times[0] + 1.0)
    ax_controls.set_ylim(-1.1, 1.1)
    ax_controls.set_xlabel("time (s)")
    ax_controls.set_ylabel("command")
    ax_controls.grid(alpha=0.25)
    ax_controls.legend(loc="upper right")
    style_axis(ax_controls, plot_config)

    def _format_top_rules(frame_record) -> str:
        engine_map = [
            ("Risk", frame_record.engine_results["risk"].output("risk_level").activations),
            ("Lane", frame_record.engine_results["lane"].output("lane_stability").activations),
            ("Comfort", frame_record.engine_results["comfort"].output("comfort_efficiency").activations),
            ("Brake", frame_record.engine_results["meta"].output("brake_command").activations),
        ]
        lines = ["Top Rule Activations"]
        for label, activations in engine_map:
            ranked = [item for item in sorted(activations, key=lambda item: item.firing_strength, reverse=True) if item.firing_strength > 0.0][:2]
            lines.append(f"{label}:")
            if not ranked:
                lines.append("  - no active rule")
                continue
            for activation in ranked:
                lines.append(
                    f"  - {activation.rule_name} -> {activation.consequent_label} ({activation.firing_strength:.2f})"
                )
        return "\n".join(lines)

    def _update(frame_index: int):
        record = result.records[frame_index]
        ego = record.ego_state_next
        front = record.front_state_next

        front_relative_x = front.x_position - ego.x_position
        clipped_front_x = min(max(front_relative_x, scene_x_min + 2.0), scene_x_max - 2.0)

        ego_patch.set_xy((-vehicle_length / 2.0, ego.y_position - vehicle_width / 2.0))
        front_patch.set_xy((clipped_front_x - vehicle_length / 2.0, -vehicle_width / 2.0))

        history_slice = slice(0, frame_index + 1)
        speed_line.set_data(times[history_slice], speeds[history_slice])
        distance_line.set_data(times[history_slice], distances[history_slice])
        risk_line.set_data(times[history_slice], risks[history_slice])
        lane_line.set_data(times[history_slice], lane_deviations[history_slice])
        throttle_line.set_data(times[history_slice], throttles[history_slice])
        brake_line.set_data(times[history_slice], brakes[history_slice])
        steering_line.set_data(times[history_slice], steerings[history_slice])

        info_text.set_text(
            "\n".join(
                [
                    f"t = {record.time_s:.1f} s",
                    f"speed = {ego.speed:.2f} m/s",
                    f"distance = {front_relative_x:.2f} m",
                    f"risk = {record.subsystem_outputs['risk']:.2f}",
                    f"lane y = {ego.y_position:.2f} m",
                    f"throttle = {record.final_command_outputs['throttle']:.2f}",
                    f"brake = {record.final_command_outputs['brake']:.2f}",
                    f"steering = {record.final_command_outputs['steering']:.2f}",
                ]
            )
        )
        rule_text.set_text(_format_top_rules(record))

        return (
            ego_patch,
            front_patch,
            speed_line,
            distance_line,
            risk_line,
            lane_line,
            throttle_line,
            brake_line,
            steering_line,
            info_text,
            rule_text,
        )

    interval_ms = max(25, int(result.records[1].time_s * 400.0)) if len(result.records) > 1 else 120
    backend_name = plt.get_backend().lower()
    interactive_backend = "agg" not in backend_name

    if interactive_backend:
        animation = FuncAnimation(
            figure,
            _update,
            frames=len(result.records),
            interval=interval_ms,
            blit=False,
            repeat=False,
        )
        figure._live_animation = animation  # type: ignore[attr-defined]
        if output_path is not None:
            figure.savefig(output_path, dpi=plot_config.dpi)
        plt.show()
        return

    _update(0)
    if output_path is not None:
        figure.savefig(output_path, dpi=plot_config.dpi)
    plt.close(figure)
