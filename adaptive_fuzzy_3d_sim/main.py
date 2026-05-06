"""3D hiyerarşik bulanık sürüş demosunun giriş noktası."""

from __future__ import annotations

import argparse

from ursina import Entity, Ursina, color, time, window

from config import DemoConfig
from simulation_manager import SimulationManager


class DemoRuntime(Entity):
    """Thin Ursina runtime wrapper around the simulation manager."""

    def __init__(self, use_neuro_fuzzy: bool, neuro_fuzzy_epochs: int, neuro_fuzzy_lr: float) -> None:
        super().__init__()
        self.manager = SimulationManager(
            DemoConfig(),
            use_neuro_fuzzy=use_neuro_fuzzy,
            neuro_fuzzy_epochs=neuro_fuzzy_epochs,
            neuro_fuzzy_lr=neuro_fuzzy_lr,
        )

    def update(self) -> None:
        self.manager.update(time.dt)

    def input(self, key: str) -> None:
        self.manager.handle_input(key)


def main() -> None:
    """Sınıf sunumuna uygun 3D simülasyonu başlat."""

    parser = argparse.ArgumentParser(description="3D hiyerarşik bulanık sürüş demosunu çalıştır.")
    parser.add_argument(
        "--plain-fuzzy",
        action="store_true",
        help="Nöro-fuzzy ön uyarlamayı kapat ve saf Mamdani kural ağırlıklarıyla başlat.",
    )
    parser.add_argument(
        "--neuro-fuzzy-epochs",
        type=int,
        default=4,
        help="3D nöro-fuzzy ön uyarlama epoch sayısı.",
    )
    parser.add_argument(
        "--neuro-fuzzy-lr",
        type=float,
        default=0.05,
        help="3D nöro-fuzzy ön uyarlama öğrenme oranı.",
    )
    args = parser.parse_args()

    app = Ursina(
        title="Uyarlanabilir Bulanık 3D Sürüş Demosu",
        borderless=False,
        development_mode=False,
    )
    window.color = color.rgb(170, 214, 255)
    window.exit_button.visible = True
    window.fps_counter.enabled = True

    DemoRuntime(
        use_neuro_fuzzy=not args.plain_fuzzy,
        neuro_fuzzy_epochs=max(1, args.neuro_fuzzy_epochs),
        neuro_fuzzy_lr=max(0.001, args.neuro_fuzzy_lr),
    )
    app.run()


if __name__ == "__main__":
    main()
