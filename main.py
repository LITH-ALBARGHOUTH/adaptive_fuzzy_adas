"""CLI entry point for the time-based hierarchical fuzzy driving simulation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from config import get_default_plot_config, get_default_simulation_config
from scenarios import get_predefined_scenarios
from simulation import HierarchicalFuzzyADASController, run_simulation
from utils import ensure_directory, print_scenario_report
from visualization.live_simulation import show_live_simulation
from visualization.scenario_plots import plot_scenario_comparison, plot_scenario_timeseries


def build_argument_parser(scenario_names: Sequence[str]) -> argparse.ArgumentParser:
    """Build the command-line interface."""

    parser = argparse.ArgumentParser(
        description="Run the hierarchical fuzzy ADAS time-based simulation."
    )
    parser.add_argument(
        "--scenario",
        default="all",
        choices=["all", *scenario_names],
        help="Run one named scenario or all scenarios.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for one-shot sensor inputs and print throttle, brake, and steering.",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Run scenarios without saving plots.",
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Disable the live simulation window for single-scenario runs.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/generated_figures",
        help="Directory for saved figures.",
    )
    return parser


def run_interactive_mode(controller: HierarchicalFuzzyADASController) -> None:
    """Prompt the user for one-shot inputs and run the fuzzy hierarchy once."""

    simulation_config = get_default_simulation_config()

    speed = float(input("Enter ego speed (m/s): ").strip())
    distance = float(input("Enter front distance (m): ").strip())
    lane_deviation = float(input("Enter lane deviation (m): ").strip())
    road_condition = float(input("Enter road condition (0-1): ").strip())

    sensor_inputs = {
        "speed": speed,
        "distance": distance,
        "lane_deviation": lane_deviation,
        "road_condition": road_condition,
        "slope": simulation_config.interactive_slope,
        "traffic_density": simulation_config.interactive_traffic_density,
        "steering_stability": simulation_config.default_steering_stability,
    }

    evaluation = controller.evaluate(sensor_inputs)
    commands = evaluation["final_commands"]

    print("=" * 88)
    print("Interactive fuzzy evaluation")
    print(
        "Defaults used: "
        f"steering_stability={simulation_config.default_steering_stability:.2f}, "
        f"slope={simulation_config.interactive_slope:.2f}, "
        f"traffic_density={simulation_config.interactive_traffic_density:.2f}"
    )
    print(
        "Subsystem outputs: "
        f"risk={evaluation['subsystem_outputs']['risk']:.2f}, "
        f"lane={evaluation['subsystem_outputs']['lane']:.2f}, "
        f"comfort={evaluation['subsystem_outputs']['comfort']:.2f}"
    )
    print(
        "Meta outputs: "
        f"throttle={commands['throttle']:.3f}, "
        f"brake={commands['brake']:.3f}, "
        f"steering={commands['steering']:.3f}"
    )


def main() -> None:
    """Run the requested simulation mode."""

    scenarios = get_predefined_scenarios()
    parser = build_argument_parser(sorted(scenarios))
    args = parser.parse_args()

    controller = HierarchicalFuzzyADASController()

    if args.interactive:
        run_interactive_mode(controller)
        return

    selected_names = list(scenarios) if args.scenario == "all" else [args.scenario]
    output_dir = ensure_directory(Path(args.output_dir))
    plot_config = get_default_plot_config()
    simulation_config = get_default_simulation_config()
    results = {}

    for scenario_name in selected_names:
        result = run_simulation(
            scenario=scenarios[scenario_name],
            controller=controller,
            simulation_config=simulation_config,
        )
        results[scenario_name] = result
        print_scenario_report(result)

        if not args.skip_plots:
            plot_scenario_timeseries(result, output_dir, plot_config)

    if not args.skip_plots and len(results) > 1:
        plot_scenario_comparison(results, output_dir, plot_config)

    if not args.no_live and len(results) == 1:
        only_result = next(iter(results.values()))
        show_live_simulation(only_result, plot_config)

    if args.skip_plots:
        print("-" * 88)
        print("Simulation finished without plot generation.")
    else:
        print("-" * 88)
        print(f"Saved plots to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
