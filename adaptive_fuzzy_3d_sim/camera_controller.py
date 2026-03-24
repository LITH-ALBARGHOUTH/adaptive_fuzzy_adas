"""Camera controller for chase and top-down views."""

from __future__ import annotations

from ursina import Vec3, camera, lerp

from config import DemoConfig
from vehicle import EgoVehicleState


class CameraController:
    """Maintains a classroom-friendly set of camera modes."""

    def __init__(self, config: DemoConfig) -> None:
        self.config = config
        self._modes = ["CHASE", "TOP-DOWN"]
        self._index = 0

    @property
    def mode_name(self) -> str:
        """Return the active camera mode name."""

        return self._modes[self._index]

    def toggle_mode(self) -> str:
        """Switch to the next camera mode."""

        self._index = (self._index + 1) % len(self._modes)
        return self.mode_name

    def update(
        self,
        ego_state: EgoVehicleState,
        dt: float,
        render_x: float | None = None,
        road_height: float = 0.0,
    ) -> None:
        """Update the camera transform."""

        focus_x = ego_state.lateral_x if render_x is None else render_x

        if self.mode_name == "CHASE":
            desired_position = Vec3(
                focus_x,
                road_height + self.config.chase_camera_height,
                ego_state.forward_z - self.config.chase_camera_distance,
            )
            camera.position = lerp(camera.position, desired_position, min(1.0, dt * 4.0))
            camera.look_at(Vec3(focus_x, road_height + 0.8, ego_state.forward_z + 14.0))
            return

        desired_position = Vec3(
            focus_x,
            road_height + self.config.topdown_camera_height,
            ego_state.forward_z + self.config.topdown_follow_distance,
        )
        camera.position = lerp(camera.position, desired_position, min(1.0, dt * 5.0))
        camera.rotation_x = 89.0
        camera.rotation_y = 0.0
        camera.rotation_z = 0.0
