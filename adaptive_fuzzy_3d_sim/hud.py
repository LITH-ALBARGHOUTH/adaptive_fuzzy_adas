from __future__ import annotations

from typing import Callable, Dict

from ursina import Button, Entity, Text, camera, color

from config import DemoConfig


def _make_button(
    text: str,
    position: tuple[float, float],
    callback: Callable[[], None],
    *,
    scale: tuple[float, float] = (0.17, 0.05),
) -> Button:
    button = Button(
        parent=camera.ui,
        text=text,
        scale=scale,
        color=color.rgba(28, 34, 42, 235),
        text_color=color.white,
        highlight_color=color.rgba(66, 103, 138, 255),
        pressed_color=color.rgba(16, 24, 34, 255),
        position=position,
    )
    button.on_click = callback
    return button


def _section_label(text: str, position: tuple[float, float]) -> Text:
    return Text(
        parent=camera.ui,
        text=text,
        origin=(-0.5, 0.0),
        position=position,
        scale=0.86,
        color=color.rgb(132, 190, 238),
    )


class SimulationHUD:

    def __init__(self, config: DemoConfig, callbacks: Dict[str, Callable[[], None]]) -> None:
        self.config = config
        panel_x = -0.55
        panel_y = 0.02

        self.panel = Entity(
            parent=camera.ui,
            model="quad",
            color=color.rgba(18, 22, 28, 210),
            scale=(0.38, 0.90),
            position=(panel_x, panel_y),
        )
        self.title = Text(
            parent=camera.ui,
            text="Hiyerarşik Bulanık 3D ADAS\nDemosu",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.15, 0.43),
            scale=0.66,
            color=color.azure,
        )

        self.controls_label = _section_label("KONTROLLER", (panel_x - 0.15, 0.37))
        self.start_button = _make_button("Başlat", (panel_x - 0.075, 0.33), callbacks["start"], scale=(0.145, 0.048))
        self.pause_button = _make_button("Duraklat", (panel_x + 0.075, 0.33), callbacks["pause"], scale=(0.145, 0.048))
        self.reset_button = _make_button("Sıfırla", (panel_x - 0.075, 0.26), callbacks["reset"], scale=(0.145, 0.048))
        self.quit_button = _make_button("Çıkış", (panel_x + 0.075, 0.26), callbacks["quit"], scale=(0.145, 0.048))
        self.prev_button = _make_button("Önceki", (panel_x - 0.075, 0.19), callbacks["previous_scenario"], scale=(0.145, 0.048))
        self.next_button = _make_button("Sonraki", (panel_x + 0.075, 0.19), callbacks["next_scenario"], scale=(0.145, 0.048))
        self.mode_button = _make_button("Mod", (panel_x - 0.075, 0.12), callbacks["cycle_mode"], scale=(0.145, 0.048))
        self.camera_button = _make_button("Kamera", (panel_x + 0.075, 0.12), callbacks["toggle_camera"], scale=(0.145, 0.048))
        self.debug_button = _make_button("Rehber", (panel_x - 0.075, 0.05), callbacks["toggle_debug"], scale=(0.145, 0.048))
        self.centerline_button = _make_button("Merkez", (panel_x + 0.075, 0.05), callbacks["toggle_centerline"], scale=(0.145, 0.048))

        self.status_group_label = _section_label("OTURUM BİLGİSİ", (panel_x - 0.15, -0.02))

        self.scenario_label = Text(
            parent=camera.ui,
            text="Senaryo: -",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.15, -0.06),
            scale=0.82,
            color=color.white,
        )
        self.mode_label = Text(
            parent=camera.ui,
            text="Mod: Demo",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.15, -0.10),
            scale=0.82,
            color=color.white,
        )
        self.camera_label = Text(
            parent=camera.ui,
            text="Kamera: Takip",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.15, -0.14),
            scale=0.82,
            color=color.light_gray,
        )
        self.state_label = Text(
            parent=camera.ui,
            text="Durum: Hazır",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.15, -0.18),
            scale=0.82,
            color=color.light_gray,
        )

        self.status_banner = Text(
            parent=camera.ui,
            text="GÜVENLİ",
            origin=(0.0, 0.0),
            position=(0.0, 0.45),
            scale=1.8,
            color=color.lime,
            background=True,
        )

        self.warning_text = Text(
            parent=camera.ui,
            text="",
            origin=(0.0, 0.0),
            position=(0.0, 0.39),
            scale=1.0,
            color=color.yellow,
        )

        self.risk_bar_bg = Entity(
            parent=camera.ui,
            model="quad",
            color=color.rgba(60, 60, 60, 220),
            scale=(0.30, 0.028),
            position=(0.38, 0.43),
        )
        self.risk_bar_fill = Entity(
            parent=camera.ui,
            model="quad",
            color=color.lime,
            scale=(0.002, 0.022),
            origin=(-0.5, 0.0),
            position=(0.23, 0.43),
        )
        self.risk_label = Text(
            parent=camera.ui,
            text="Risk",
            origin=(0.0, 0.0),
            position=(0.38, 0.47),
            scale=0.95,
            color=color.white,
        )

        self.rule_panel = Entity(
            parent=camera.ui,
            model="quad",
            color=color.rgba(18, 22, 28, 220),
            scale=(0.31, 0.76),
            position=(0.54, 0.00),
        )
        self.rule_title = Text(
            parent=camera.ui,
            text="Aktif Kurallar",
            origin=(-0.5, 0.0),
            position=(0.425, 0.335),
            scale=0.82,
            color=color.rgb(170, 220, 255),
        )
        self.rule_hint = Text(
            parent=camera.ui,
            text="En baskın neden ve karar özeti yer alır.",
            origin=(-0.5, 0.0),
            position=(0.425, 0.288),
            scale=0.54,
            color=color.rgb(200, 214, 224),
        )
        self.rule_text = Text(
            parent=camera.ui,
            text="Simülasyon başladığında\nen güçlü kurallar burada görünecek.",
            origin=(-0.5, 0.5),
            position=(0.425, 0.215),
            scale=0.58,
            color=color.rgb(230, 236, 243),
            line_height=1.10,
        )

        self.telemetry_label = _section_label("CANLI TELEMETRİ", (panel_x - 0.15, -0.24))
        self.telemetry = Text(
            parent=camera.ui,
            text="Telemetri yükleniyor...",
            origin=(-0.5, 0.5),
            position=(panel_x - 0.145, -0.285),
            scale=0.68,
            color=color.rgb(228, 235, 242),
            line_height=1.18,
        )
        self.help_text = Text(
            parent=camera.ui,
            text="Kısayollar: W/S gaz-fren | A/D direksiyon | Space başlat-duraklat\nR sıfırla | Tab mod | C kamera | N/B senaryo | Esc/Q çıkış",
            origin=(0.0, 0.0),
            position=(0.0, -0.47),
            scale=0.66,
            color=color.rgb(236, 236, 236),
        )

    def update_display(
        self,
        *,
        scenario_name: str,
        mode_name: str,
        camera_mode: str,
        running_state: str,
        telemetry_lines: list[str],
        status_label: str,
        status_color,
        warning_message: str,
        risk_value: float,
        rule_lines: list[str],
    ) -> None:
        """Refresh the dynamic HUD text and risk bar."""

        self.scenario_label.text = f"Senaryo: {scenario_name}"
        self.mode_label.text = f"Mod: {mode_name}"
        self.camera_label.text = f"Kamera: {camera_mode}"
        self.state_label.text = f"Durum: {running_state}"
        self.telemetry.text = "\n".join(telemetry_lines)
        self.status_banner.text = status_label
        self.status_banner.color = status_color
        self.warning_text.text = warning_message
        self.rule_text.text = "\n".join(rule_lines)

        normalized_risk = max(0.0, min(100.0, risk_value)) / 100.0
        self.risk_bar_fill.scale_x = max(0.002, 0.30 * normalized_risk)
        if risk_value >= 75.0:
            self.risk_bar_fill.color = color.red
        elif risk_value >= 45.0:
            self.risk_bar_fill.color = color.yellow
        else:
            self.risk_bar_fill.color = color.lime
