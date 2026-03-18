"""3D demo için oyun içi HUD ve kontrol paneli."""

from __future__ import annotations

from typing import Callable, Dict

from ursina import Button, Entity, Text, camera, color

from config import DemoConfig


def _make_button(text: str, position: tuple[float, float], callback: Callable[[], None]) -> Button:
    button = Button(
        parent=camera.ui,
        text=text,
        scale=(0.15, 0.042),
        color=color.rgba(35, 35, 45, 220),
        text_color=color.white,
        highlight_color=color.rgba(70, 100, 140, 255),
        pressed_color=color.rgba(20, 30, 50, 255),
        position=position,
    )
    button.on_click = callback
    return button


class SimulationHUD:
    """Sınıf gösterimleri için sade ve anlaşılır bir arayüz."""

    def __init__(self, config: DemoConfig, callbacks: Dict[str, Callable[[], None]]) -> None:
        self.config = config
        panel_x = -0.62
        panel_y = 0.06

        self.panel = Entity(
            parent=camera.ui,
            model="quad",
            color=color.rgba(18, 22, 28, 210),
            scale=(self.config.ui_panel_width, 0.86),
            position=(panel_x, panel_y),
        )
        self.title = Text(
            parent=camera.ui,
            text="Hiyerarşik Bulanık 3D ADAS Demosu",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.18, 0.45),
            scale=1.05,
            color=color.azure,
        )

        self.start_button = _make_button("Başlat", (panel_x - 0.12, 0.37), callbacks["start"])
        self.pause_button = _make_button("Duraklat", (panel_x + 0.04, 0.37), callbacks["pause"])
        self.reset_button = _make_button("Sıfırla", (panel_x + 0.20, 0.37), callbacks["reset"])

        self.prev_button = _make_button("Önceki", (panel_x - 0.12, 0.30), callbacks["previous_scenario"])
        self.next_button = _make_button("Sonraki", (panel_x + 0.20, 0.30), callbacks["next_scenario"])
        self.mode_button = _make_button("Mod", (panel_x + 0.04, 0.30), callbacks["cycle_mode"])

        self.camera_button = _make_button("Kamera", (panel_x - 0.12, 0.23), callbacks["toggle_camera"])
        self.debug_button = _make_button("Rehber", (panel_x + 0.04, 0.23), callbacks["toggle_debug"])
        self.centerline_button = _make_button("Merkez", (panel_x + 0.20, 0.23), callbacks["toggle_centerline"])
        self.quit_button = _make_button("Çıkış", (panel_x + 0.20, 0.16), callbacks["quit"])

        self.scenario_label = Text(
            parent=camera.ui,
            text="Senaryo: -",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.18, 0.15),
            scale=0.92,
            color=color.white,
        )
        self.mode_label = Text(
            parent=camera.ui,
            text="Mod: Demo",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.18, 0.10),
            scale=0.92,
            color=color.white,
        )
        self.camera_label = Text(
            parent=camera.ui,
            text="Kamera: Takip",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.18, 0.05),
            scale=0.92,
            color=color.light_gray,
        )
        self.state_label = Text(
            parent=camera.ui,
            text="Durum: Hazır",
            origin=(-0.5, 0.0),
            position=(panel_x - 0.18, 0.00),
            scale=0.92,
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

        self.telemetry = Text(
            parent=camera.ui,
            text="Telemetri yükleniyor...",
            origin=(-0.5, 0.5),
            position=(panel_x - 0.18, -0.06),
            scale=0.82,
            color=color.rgb(228, 235, 242),
            line_height=1.15,
        )
        self.help_text = Text(
            parent=camera.ui,
            text="W/S gaz-fren  A/D direksiyon  Space başlat-duraklat  R sıfırla  Tab mod  C kamera  Esc/Q çıkış",
            origin=(0.0, 0.0),
            position=(0.0, -0.47),
            scale=0.86,
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

        normalized_risk = max(0.0, min(100.0, risk_value)) / 100.0
        self.risk_bar_fill.scale_x = max(0.002, 0.30 * normalized_risk)
        if risk_value >= 75.0:
            self.risk_bar_fill.color = color.red
        elif risk_value >= 45.0:
            self.risk_bar_fill.color = color.yellow
        else:
            self.risk_bar_fill.color = color.lime
