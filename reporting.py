"""Automated exports that align the project with fuzzy-logic report requirements."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable

from config import PlotConfig
from simulation import HierarchicalFuzzyADASController
from utils import (
    SimulationResult,
    compute_result_metrics,
    ensure_directory,
    select_representative_record,
)
from visualization.architecture_plot import plot_system_architecture_diagram
from visualization.defuzzification_plot import plot_example_defuzzifications
from visualization.membership_plots import plot_all_memberships, plot_membership_sensitivity
from visualization.rule_activation import plot_rule_activation_overview
from visualization.surface_plots import plot_collision_risk_surface, plot_meta_brake_contour


def _format_antecedents(antecedents: Iterable[tuple[str, str]]) -> str:
    return " AND ".join(f"{variable} IS {label}" for variable, label in antecedents)


def _rule_to_statement(rule) -> str:
    antecedent_text = _format_antecedents(rule.antecedents)
    output_name, output_label = rule.consequent
    return f"IF {antecedent_text} THEN {output_name} IS {output_label}"


def export_rule_base_tables(controller: HierarchicalFuzzyADASController, export_dir: Path) -> list[Path]:
    """Export numbered rule tables in markdown and CSV formats."""

    ensure_directory(export_dir)
    markdown_path = export_dir / "rule_base_tables.md"
    csv_path = export_dir / "rule_base_tables.csv"

    engine_map = {
        "collision": controller.risk_engine,
        "lane": controller.lane_engine,
        "comfort": controller.comfort_engine,
        "meta": controller.meta_engine,
    }

    markdown_lines = [
        "# Rule Base Tables",
        "",
        "This file exports the implemented fuzzy rule base in numbered IF-THEN form.",
        "",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "engine",
                "output_name",
                "rule_index",
                "rule_name",
                "if_then_statement",
                "weight",
                "description",
            ],
        )
        writer.writeheader()

        for engine_name, engine in engine_map.items():
            markdown_lines.append(f"## {engine_name.title()} Engine")
            markdown_lines.append("")

            for output_name, rules in engine.rules.items():
                markdown_lines.append(f"### Output: `{output_name}`")
                markdown_lines.append("")
                markdown_lines.append("| # | Rule Name | IF-THEN Statement | Weight | Description |")
                markdown_lines.append("|---|---|---|---:|---|")

                for rule_index, rule in enumerate(rules, start=1):
                    statement = _rule_to_statement(rule)
                    markdown_lines.append(
                        f"| {rule_index} | `{rule.name}` | `{statement}` | {rule.weight:.2f} | {rule.description} |"
                    )
                    writer.writerow(
                        {
                            "engine": engine_name,
                            "output_name": output_name,
                            "rule_index": rule_index,
                            "rule_name": rule.name,
                            "if_then_statement": statement,
                            "weight": f"{rule.weight:.2f}",
                            "description": rule.description,
                        }
                    )

                markdown_lines.append("")

    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")
    return [markdown_path, csv_path]


def export_conflict_notes(controller: HierarchicalFuzzyADASController, export_dir: Path) -> Path:
    """Export representative conflicting-rule examples for the report."""

    ensure_directory(export_dir)
    path = export_dir / "rule_conflict_examples.md"

    pairs = [
        (
            "Collision risk depends on interacting inputs, not a single monotonic trend.",
            [
                controller.risk_engine.rules["risk_level"][5],   # r6_close_highspeed
                controller.risk_engine.rules["risk_level"][7],   # r8_close_lowspeed
                controller.risk_engine.rules["risk_level"][11],  # r12_medium_medspeed_goodroad
                controller.risk_engine.rules["risk_level"][12],  # r13_medium_medspeed_poorroad
            ],
        ),
        (
            "Lane correction strength changes with speed and steering stability even for similar offsets.",
            [
                controller.lane_engine.rules["lane_stability"][5],   # r6_left_highspeed
                controller.lane_engine.rules["lane_stability"][14],  # r15_left_lowspeed_stable
                controller.lane_engine.rules["lane_stability"][7],   # r8_left_unstable
            ],
        ),
        (
            "Meta decisions explicitly balance comfort against safety and lateral urgency.",
            [
                controller.meta_engine.rules["throttle_command"][8],   # t9_lowrisk_centered_highcomfort
                controller.meta_engine.rules["throttle_command"][10],  # t11_lowrisk_centered_lowcomfort
                controller.meta_engine.rules["brake_command"][13],     # b14_mediumrisk_centered_highcomfort
                controller.meta_engine.rules["brake_command"][10],     # b11_highrisk_strongleft
            ],
        ),
    ]

    lines = [
        "# Conflict-Oriented Rule Notes",
        "",
        "These examples highlight how the rule base handles interacting and competing conditions.",
        "",
    ]

    for section_title, rules in pairs:
        lines.append(f"## {section_title}")
        lines.append("")
        for rule in rules:
            lines.append(f"- `{rule.name}`: `{_rule_to_statement(rule)}`")
            lines.append(f"  Description: {rule.description} (weight={rule.weight:.2f})")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _append_threshold_check(checks, label: str, actual, target, comparator: str) -> None:
    if comparator == ">=":
        passed = actual >= target
    elif comparator == "<=":
        passed = actual <= target
    elif comparator == "==":
        passed = actual == target
    else:
        raise ValueError(f"Unsupported comparator '{comparator}'.")

    checks.append(
        {
            "check": label,
            "actual": actual,
            "target": target,
            "comparator": comparator,
            "passed": passed,
        }
    )


def evaluate_expectations(result: SimulationResult) -> tuple[dict, list[dict], bool]:
    """Evaluate one scenario against its declared validation targets."""

    metrics = compute_result_metrics(result)
    expectation = result.scenario.expectation
    if expectation is None:
        return metrics, [], True

    checks: list[dict] = []
    threshold_specs = [
        ("max_risk", expectation.min_max_risk, ">=", "max risk should be high enough"),
        ("max_risk", expectation.max_max_risk, "<=", "max risk should stay below target"),
        ("peak_brake", expectation.min_peak_brake, ">=", "peak brake should reach target"),
        ("peak_brake", expectation.max_peak_brake, "<=", "peak brake should stay below target"),
        ("peak_throttle", expectation.min_peak_throttle, ">=", "peak throttle should reach target"),
        ("peak_throttle", expectation.max_peak_throttle, "<=", "peak throttle should stay below target"),
        (
            "peak_abs_steering",
            expectation.min_peak_abs_steering,
            ">=",
            "peak steering magnitude should reach target",
        ),
        (
            "peak_abs_steering",
            expectation.max_peak_abs_steering,
            "<=",
            "peak steering magnitude should stay below target",
        ),
        (
            "rms_lane_deviation",
            expectation.max_rms_lane_deviation,
            "<=",
            "RMS lane deviation should stay below target",
        ),
        (
            "minimum_distance",
            expectation.min_minimum_distance,
            ">=",
            "minimum distance should stay above target",
        ),
    ]

    for metric_name, target_value, comparator, label in threshold_specs:
        if target_value is not None:
            _append_threshold_check(
                checks,
                label,
                round(float(metrics[metric_name]), 4),
                round(float(target_value), 4),
                comparator,
            )

    if expectation.expect_collision is not None:
        _append_threshold_check(
            checks,
            "collision expectation",
            bool(metrics["collision"]),
            bool(expectation.expect_collision),
            "==",
        )
    if expectation.expect_lane_departure is not None:
        _append_threshold_check(
            checks,
            "lane departure expectation",
            bool(metrics["lane_departure"]),
            bool(expectation.expect_lane_departure),
            "==",
        )

    overall = all(check["passed"] for check in checks)
    return metrics, checks, overall


def export_scenario_validation(results: Dict[str, SimulationResult], export_dir: Path) -> list[Path]:
    """Export expected-versus-actual scenario validation tables."""

    ensure_directory(export_dir)
    summary_csv = export_dir / "scenario_validation_summary.csv"
    checks_csv = export_dir / "scenario_validation_checks.csv"
    summary_md = export_dir / "scenario_validation_summary.md"
    summary_json = export_dir / "scenario_validation_summary.json"

    summary_rows = []
    check_rows = []

    for scenario_name, result in results.items():
        metrics, checks, overall = evaluate_expectations(result)
        expectation = result.scenario.expectation
        summary_rows.append(
            {
                "scenario": scenario_name,
                "expected_behavior": expectation.description if expectation else "",
                "final_speed": round(float(metrics["final_speed"]), 4),
                "minimum_distance": round(float(metrics["minimum_distance"]), 4),
                "max_risk": round(float(metrics["max_risk"]), 4),
                "rms_lane_deviation": round(float(metrics["rms_lane_deviation"]), 4),
                "peak_brake": round(float(metrics["peak_brake"]), 4),
                "peak_throttle": round(float(metrics["peak_throttle"]), 4),
                "peak_abs_steering": round(float(metrics["peak_abs_steering"]), 4),
                "collision": bool(metrics["collision"]),
                "lane_departure": bool(metrics["lane_departure"]),
                "overall_pass": overall,
            }
        )

        for check in checks:
            check_rows.append(
                {
                    "scenario": scenario_name,
                    "check": check["check"],
                    "actual": check["actual"],
                    "comparator": check["comparator"],
                    "target": check["target"],
                    "passed": check["passed"],
                }
            )

    if not summary_rows:
        empty_text = "# Scenario Validation Summary\n\nNo scenario results were available.\n"
        summary_csv.write_text("", encoding="utf-8")
        checks_csv.write_text("", encoding="utf-8")
        summary_md.write_text(empty_text, encoding="utf-8")
        summary_json.write_text("[]", encoding="utf-8")
        return [summary_csv, checks_csv, summary_md, summary_json]

    with summary_csv.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    check_fieldnames = ["scenario", "check", "actual", "comparator", "target", "passed"]
    with checks_csv.open("w", newline="", encoding="utf-8") as checks_file:
        writer = csv.DictWriter(checks_file, fieldnames=check_fieldnames)
        writer.writeheader()
        writer.writerows(check_rows)

    lines = [
        "# Scenario Validation Summary",
        "",
        "This file compares expected scenario behavior against the measured simulation outputs.",
        "",
        "| Scenario | Expected Behavior | Max Risk | Peak Brake | Peak Abs Steering | Min Distance | RMS Lane | Collision | Lane Departure | Overall |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['scenario']} | {row['expected_behavior']} | {row['max_risk']:.2f} | "
            f"{row['peak_brake']:.2f} | {row['peak_abs_steering']:.2f} | {row['minimum_distance']:.2f} | "
            f"{row['rms_lane_deviation']:.3f} | {row['collision']} | {row['lane_departure']} | {row['overall_pass']} |"
        )

    lines.append("")
    for row in summary_rows:
        scenario_checks = [check for check in check_rows if check["scenario"] == row["scenario"]]
        lines.append(f"## {row['scenario']}")
        lines.append("")
        lines.append("| Check | Actual | Comparator | Target | Passed |")
        lines.append("|---|---:|---|---:|---|")
        for check in scenario_checks:
            lines.append(
                f"| {check['check']} | {check['actual']} | {check['comparator']} | {check['target']} | {check['passed']} |"
            )
        lines.append("")

    summary_md.write_text("\n".join(lines), encoding="utf-8")
    summary_json.write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")

    return [summary_csv, checks_csv, summary_md, summary_json]


def write_report_manifest(output_dir: Path, export_dir: Path) -> Path:
    """Write a compact index of generated report-oriented artifacts."""

    figure_names = sorted(path.name for path in output_dir.glob("*.png"))
    export_names = sorted(path.name for path in export_dir.iterdir() if path.is_file())
    manifest_path = export_dir / "report_manifest.md"

    lines = [
        "# Report Artifact Manifest",
        "",
        "Generated figures:",
        "",
    ]
    lines.extend(f"- {name}" for name in figure_names)
    lines.extend(["", "Generated tables and exports:", ""])
    lines.extend(f"- {name}" for name in export_names)
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path


def generate_report_bundle(
    controller: HierarchicalFuzzyADASController,
    fuzzy_config,
    results: Dict[str, SimulationResult],
    output_dir: Path,
    plot_config: PlotConfig,
) -> Dict[str, list[Path]]:
    """Generate the full bundle of figures and tables useful for the course report."""

    export_dir = ensure_directory(output_dir / "report_exports")
    representative_record = select_representative_record(results)

    plot_system_architecture_diagram(output_dir, plot_config)
    plot_all_memberships(controller, output_dir, plot_config)
    plot_rule_activation_overview(representative_record, output_dir, plot_config)
    plot_example_defuzzifications(representative_record, output_dir, plot_config)
    plot_collision_risk_surface(controller, output_dir, plot_config)
    plot_meta_brake_contour(controller, output_dir, plot_config)
    plot_membership_sensitivity(fuzzy_config, output_dir, plot_config)

    exported_paths = []
    exported_paths.extend(export_rule_base_tables(controller, export_dir))
    exported_paths.append(export_conflict_notes(controller, export_dir))
    exported_paths.extend(export_scenario_validation(results, export_dir))
    exported_paths.append(write_report_manifest(output_dir, export_dir))

    figure_paths = sorted(output_dir.glob("*.png"))
    return {
        "figures": list(figure_paths),
        "exports": exported_paths,
    }
