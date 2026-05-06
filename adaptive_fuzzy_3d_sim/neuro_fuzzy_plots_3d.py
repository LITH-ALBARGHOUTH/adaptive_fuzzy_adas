"""Plot helpers for 3D neuro-fuzzy startup adaptation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_neuro_fuzzy_adaptation_3d(report, output_dir: Path) -> Path:
    """Save the 3D startup adaptation summary figure."""

    output_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        1,
        2,
        figsize=(14.0, 6.0),
        gridspec_kw={"width_ratios": [1.0, 1.8]},
    )

    axes[0].bar(
        ["Başlangıç", "Uyarlanmış"],
        [report.baseline_loss, report.adapted_loss],
        color=["#9aa5b1", "#2b6cb0"],
        width=0.55,
    )
    axes[0].set_title("3D Nöro-Fuzzy Kayıp")
    axes[0].set_ylabel("Ortalama Kayıp")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].text(
        0.5,
        max(report.baseline_loss, report.adapted_loss) * 0.95 if max(report.baseline_loss, report.adapted_loss) > 0 else 0.05,
        f"Örnek: {report.sample_count}\nEpoch: {report.epochs}",
        ha="center",
        va="top",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#eef4fb", "edgecolor": "#c9d7ea"},
    )

    labels = [change[0].split(".")[-1] for change in report.top_rule_changes]
    deltas = [change[3] - change[2] for change in report.top_rule_changes]
    y_positions = np.arange(len(labels))
    colors = ["#2f855a" if delta >= 0.0 else "#c53030" for delta in deltas]

    axes[1].barh(y_positions, deltas, color=colors, alpha=0.88)
    axes[1].set_yticks(y_positions)
    axes[1].set_yticklabels(labels, fontsize=10)
    axes[1].invert_yaxis()
    axes[1].axvline(0.0, color="#4a5568", linewidth=1.0)
    axes[1].set_title("En Büyük Kural Ağırlığı Değişimleri")
    axes[1].set_xlabel("Yeni - Eski Ağırlık")
    axes[1].grid(axis="x", alpha=0.25)

    for index, delta in enumerate(deltas):
        axes[1].text(
            delta + (0.01 if delta >= 0 else -0.01),
            index,
            f"{delta:+.3f}",
            va="center",
            ha="left" if delta >= 0 else "right",
            fontsize=10,
        )

    figure.suptitle("3D Mamdani-Uyumlu Nöro-Fuzzy Uyarlama Özeti", fontsize=15)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))

    output_path = output_dir / "neuro_fuzzy_adaptation_summary_3d.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path
