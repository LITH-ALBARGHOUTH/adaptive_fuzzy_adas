"""3D hiyerarşik bulanık sürüş demosunun giriş noktası."""

from __future__ import annotations

from ursina import Entity, Ursina, color, time, window

from config import DemoConfig
from simulation_manager import SimulationManager


class DemoRuntime(Entity):
    """Thin Ursina runtime wrapper around the simulation manager."""

    def __init__(self) -> None:
        super().__init__()
        self.manager = SimulationManager(DemoConfig())

    def update(self) -> None:
        self.manager.update(time.dt)

    def input(self, key: str) -> None:
        self.manager.handle_input(key)


def main() -> None:
    """Sınıf sunumuna uygun 3D simülasyonu başlat."""

    app = Ursina(
        title="Uyarlanabilir Bulanık 3D Sürüş Demosu",
        borderless=False,
        development_mode=False,
    )
    window.color = color.rgb(170, 214, 255)
    window.exit_button.visible = True
    window.fps_counter.enabled = True

    DemoRuntime()
    app.run()


if __name__ == "__main__":
    main()
