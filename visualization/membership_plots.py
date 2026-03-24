"""Membership and sensitivity plots."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from config import MembershipSpec, PlotConfig
from fuzzy_systems.risk_engine import CollisionRiskEngine
from simulation import HierarchicalFuzzyADASController
from visualization.plot_style import apply_plot_style, style_axis


def _label_tr(text: str) -> str:
    mapping = {
        "collision": "çarpışma",
        "lane": "şerit",
        "comfort": "konfor",
        "meta": "meta",
        "speed": "hız",
        "front_distance": "ön_mesafe",
        "road_condition": "yol_koşulu",
        "risk_level": "risk_seviyesi",
        "lane_deviation": "şerit_sapması",
        "steering_stability": "direksiyon_kararlılığı",
        "lane_stability": "şerit_kararlılığı",
        "road_slope": "yol_eğimi",
        "traffic_density": "trafik_yoğunluğu",
        "comfort_efficiency": "konfor_verimlilik",
        "current_speed": "anlık_hız",
        "throttle_command": "gaz_komutu",
        "brake_command": "fren_komutu",
        "steering_correction": "direksiyon_düzeltmesi",
        "membership": "üyelik",
        "low": "düşük",
        "medium": "orta",
        "high": "yüksek",
        "critical": "kritik",
        "close": "yakın",
        "far": "uzak",
        "poor": "kötü",
        "normal": "normal",
        "good": "iyi",
        "far_left": "çok_sol",
        "left": "sol",
        "centered": "merkez",
        "right": "sağ",
        "far_right": "çok_sağ",
        "unstable": "dengesiz",
        "stable": "kararlı",
        "strong_left": "sert_sol",
        "strong_right": "sert_sağ",
        "downhill": "iniş",
        "flat": "düz",
        "uphill": "yokuş",
        "light": "hafif",
        "moderate": "orta",
        "heavy": "yoğun",
        "zero": "sıfır",
        "none": "yok",
        "hard": "sert",
        "keep": "koru",
        "steer_left": "sola_kır",
        "steer_left_hard": "sert_sola_kır",
        "steer_right": "sağa_kır",
        "steer_right_hard": "sert_sağa_kır",
        "strong": "güçlü",
    }
    return mapping.get(text, text)


def plot_all_memberships(
    controller: HierarchicalFuzzyADASController,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Generate membership figures for every engine."""

    apply_plot_style(plot_config)
    engine_map = {
        "collision": controller.risk_engine,
        "lane": controller.lane_engine,
        "comfort": controller.comfort_engine,
        "meta": controller.meta_engine,
    }

    for engine_name, engine in engine_map.items():
        variables = list(engine.input_variables.values()) + list(engine.output_variables.values())
        cols = 2
        rows = math.ceil(len(variables) / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(14, 4.2 * rows))
        axes_array = np.atleast_1d(axes).reshape(rows, cols)

        for ax, variable in zip(axes_array.flat, variables):
            for label, membership in variable.terms.items():
                ax.plot(variable.universe, membership, linewidth=2, label=_label_tr(label).replace("_", " "))
            ax.set_title(_label_tr(variable.name).replace("_", " ").title())
            ax.set_xlabel(_label_tr(variable.name).replace("_", " "))
            ax.set_ylabel("üyelik")
            ax.set_ylim(-0.02, 1.05)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=plot_config.legend_font_size, loc="upper right")
            style_axis(ax, plot_config)

        for ax in axes_array.flat[len(variables) :]:
            ax.axis("off")

        fig.suptitle(
            f"{_label_tr(engine_name).title()} Motoru Üyelik Fonksiyonları",
            fontsize=plot_config.title_font_size,
        )
        fig.tight_layout(pad=1.4)
        fig.savefig(output_dir / f"membership_{engine_name}.png", dpi=plot_config.dpi)
        plt.close(fig)


def plot_membership_sensitivity(
    fuzzy_config,
    output_dir: Path,
    plot_config: PlotConfig,
) -> None:
    """Vary one membership parameter and plot the effect on collision risk."""

    apply_plot_style(plot_config)
    reference_input = {"speed": 90.0, "front_distance": 26.0, "road_condition": 0.50}
    shoulder_values = np.linspace(24.0, 40.0, 20)
    risk_values = []

    for shoulder in shoulder_values:
        config_variant = copy.deepcopy(fuzzy_config)
        close_spec = config_variant["collision"]["inputs"]["front_distance"].labels["close"]
        params = list(close_spec.params)
        params[3] = float(shoulder)
        config_variant["collision"]["inputs"]["front_distance"].labels["close"] = MembershipSpec(
            shape=close_spec.shape,
            params=tuple(params),
        )
        risk_engine = CollisionRiskEngine(config_variant["collision"])
        risk_value = risk_engine.evaluate(**reference_input).crisp_outputs["risk_level"]
        risk_values.append(risk_value)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(shoulder_values, risk_values, color="tab:red", marker="o", linewidth=2)
    ax.set_title("Çarpışma Riskinin Yakın Mesafe Üyelik Omzuna Duyarlılığı")
    ax.set_xlabel("yakın mesafe yamuk üst omzu (m)")
    ax.set_ylabel("risk seviyesi çıkışı")
    ax.grid(alpha=0.3)
    style_axis(ax, plot_config)
    fig.tight_layout(pad=1.2)
    fig.savefig(output_dir / "sensitivity_collision_distance.png", dpi=plot_config.dpi)
    plt.close(fig)
