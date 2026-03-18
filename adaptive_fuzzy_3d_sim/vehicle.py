"""Vehicle state models and simple primitive-based 3D car visuals."""

from __future__ import annotations

from dataclasses import dataclass

from ursina import Entity, color


@dataclass
class EgoVehicleState:
    """Arcade-style ego vehicle state."""

    lateral_x: float
    forward_z: float
    speed_mps: float
    heading_deg: float = 0.0
    steering_state: float = 0.0


@dataclass
class TrafficVehicleState:
    """Simple NPC/front-vehicle state."""

    lateral_x: float
    forward_z: float
    speed_mps: float
    braking: bool = False


@dataclass
class EnvironmentState:
    """Environment inputs sampled by the fuzzy controller."""

    road_condition: float
    slope: float
    traffic_density: float


@dataclass
class ControlCommand:
    """Normalized longitudinal and lateral command outputs."""

    throttle: float
    brake: float
    steering: float


class VehicleVisual(Entity):
    """Simple primitive car model suitable for a classroom demo."""

    def __init__(self, body_color, *, with_brake_lights: bool = True, scale_factor: float = 1.0) -> None:
        super().__init__()
        self.scale_factor = scale_factor
        self.body = Entity(
            parent=self,
            model="cube",
            color=body_color,
            scale=(1.8 * scale_factor, 0.7 * scale_factor, 4.0 * scale_factor),
            position=(0.0, 0.45 * scale_factor, 0.0),
            collider="box",
        )
        self.cabin = Entity(
            parent=self,
            model="cube",
            color=color.rgba(220, 235, 255, 180),
            scale=(1.2 * scale_factor, 0.55 * scale_factor, 1.6 * scale_factor),
            position=(0.0, 0.95 * scale_factor, -0.2 * scale_factor),
        )
        self.windshield = Entity(
            parent=self,
            model="cube",
            color=color.rgba(160, 210, 255, 120),
            scale=(1.05 * scale_factor, 0.32 * scale_factor, 0.25 * scale_factor),
            position=(0.0, 1.0 * scale_factor, 0.55 * scale_factor),
        )
        self.wheels = [
            Entity(
                parent=self,
                model="cube",
                color=color.black90,
                scale=(0.35 * scale_factor, 0.35 * scale_factor, 0.75 * scale_factor),
                position=(wheel_x, 0.18 * scale_factor, wheel_z),
            )
            for wheel_x in (-0.95 * scale_factor, 0.95 * scale_factor)
            for wheel_z in (-1.25 * scale_factor, 1.25 * scale_factor)
        ]
        self.brake_lights = []
        if with_brake_lights:
            for light_x in (-0.55 * scale_factor, 0.55 * scale_factor):
                self.brake_lights.append(
                    Entity(
                        parent=self,
                        model="cube",
                        color=color.rgba(90, 10, 10, 255),
                        scale=(0.22 * scale_factor, 0.14 * scale_factor, 0.08 * scale_factor),
                        position=(light_x, 0.52 * scale_factor, -2.04 * scale_factor),
                    )
                )

    def sync_ego(self, state: EgoVehicleState, visual_yaw_scale: float) -> None:
        """Update transform from the ego state."""

        self.position = (state.lateral_x, 0.0, state.forward_z)
        self.rotation_y = state.heading_deg + (state.steering_state * visual_yaw_scale)

    def sync_traffic(self, state: TrafficVehicleState) -> None:
        """Update transform from an NPC state."""

        self.position = (state.lateral_x, 0.0, state.forward_z)
        self.rotation_y = 0.0
        self.set_brake_lights(state.braking)

    def set_brake_lights(self, active: bool) -> None:
        """Set brake-light emissive color."""

        if not self.brake_lights:
            return

        target_color = color.rgb(255, 50, 50) if active else color.rgb(90, 10, 10)
        for brake_light in self.brake_lights:
            brake_light.color = target_color
