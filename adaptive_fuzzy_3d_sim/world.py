"""3D world construction and debug visualization."""

from __future__ import annotations

from ursina import AmbientLight, DirectionalLight, Entity, Sky, Vec3, color

from config import DemoConfig
from vehicle import EgoVehicleState, TrafficVehicleState


class DrivingWorld:
    """Builds the lightweight road scene and debug markers."""

    def __init__(self, config: DemoConfig) -> None:
        self.config = config
        self._lane_markers = []
        self._roadside_props = []
        self._lane_center_entities = []
        self._debug_entities = []
        self._build_scene()

    def _build_scene(self) -> None:
        road_width = (
            self.config.road_lane_count * self.config.lane_width_m
            + (2.0 * self.config.road_width_margin_m)
        )

        Sky(color=color.rgb(168, 214, 255))
        AmbientLight(color=color.rgba(160, 160, 180, 0.9))
        sun = DirectionalLight()
        sun.look_at(Vec3(1.0, -1.0, 0.4))

        self.ground = Entity(
            model="plane",
            scale=(self.config.environment_floor_size, 1.0, self.config.environment_floor_size),
            texture="white_cube",
            texture_scale=(80, 80),
            color=color.rgb(78, 130, 84),
            position=(0.0, -0.02, self.config.road_length_m * 0.45),
        )
        self.road = Entity(
            model="cube",
            scale=(road_width, 0.05, self.config.road_length_m),
            color=color.rgb(54, 54, 58),
            position=(0.0, 0.0, self.config.road_length_m * 0.45),
        )

        lane_offsets = [
            (index - (self.config.road_lane_count // 2)) * self.config.lane_width_m
            for index in range(self.config.road_lane_count + 1)
        ]
        for lane_offset in lane_offsets:
            line = Entity(
                model="cube",
                color=color.white if lane_offset not in (lane_offsets[0], lane_offsets[-1]) else color.gray,
                scale=(0.08, 0.02, self.config.road_length_m),
                position=(lane_offset - (self.config.lane_width_m * 0.5), 0.03, self.config.road_length_m * 0.45),
            )
            self._lane_markers.append(line)

        dash_positions = range(0, int(self.config.road_length_m), 12)
        for lane_center in (-self.config.lane_width_m, 0.0, self.config.lane_width_m):
            for dash_z in dash_positions:
                dash = Entity(
                    model="cube",
                    color=color.rgb(242, 242, 242),
                    scale=(0.14, 0.025, 5.0),
                    position=(lane_center, 0.035, dash_z),
                )
                self._lane_markers.append(dash)

        for side_x in (-road_width * 0.6, road_width * 0.6):
            for prop_z in range(20, int(self.config.road_length_m), 45):
                prop = Entity(
                    model="cube",
                    color=color.rgb(90, 160, 92),
                    scale=(2.2, 5.5, 2.2),
                    position=(side_x, 2.75, prop_z),
                )
                self._roadside_props.append(prop)

        self.target_lane_line = Entity(
            model="cube",
            color=color.rgba(60, 240, 255, 160),
            scale=(0.10, 0.03, self.config.road_length_m),
            position=(0.0, 0.045, self.config.road_length_m * 0.45),
            enabled=True,
        )
        self._lane_center_entities.append(self.target_lane_line)

        self.sensor_ray = Entity(
            model="cube",
            color=color.rgba(255, 70, 70, 170),
            scale=(0.08, 0.08, 0.01),
            position=(0.0, 0.25, 0.0),
            enabled=False,
        )
        self.front_target_marker = Entity(
            model="sphere",
            color=color.rgba(255, 170, 40, 220),
            scale=0.45,
            position=(0.0, 0.7, 0.0),
            enabled=False,
        )
        self._debug_entities.extend([self.sensor_ray, self.front_target_marker])

    def set_debug_visible(self, visible: bool) -> None:
        """Toggle debug-only entities."""

        for entity in self._debug_entities:
            entity.enabled = visible and entity.enabled
        if not visible:
            self.sensor_ray.enabled = False
            self.front_target_marker.enabled = False

    def set_lane_center_visible(self, visible: bool) -> None:
        """Toggle the target lane center visualization."""

        for entity in self._lane_center_entities:
            entity.enabled = visible

    def update_debug_visuals(
        self,
        ego_state: EgoVehicleState,
        front_state: TrafficVehicleState,
        front_distance: float,
        show_debug: bool,
    ) -> None:
        """Update sensor-ray and guide marker positions."""

        if not show_debug or front_distance <= 0.0:
            self.sensor_ray.enabled = False
            self.front_target_marker.enabled = False
            return

        clipped_distance = max(0.1, min(front_distance, 120.0))
        mid_z = ego_state.forward_z + (clipped_distance * 0.5)
        mid_x = (ego_state.lateral_x + front_state.lateral_x) * 0.5

        self.sensor_ray.enabled = True
        self.sensor_ray.scale = (0.08, 0.08, clipped_distance)
        self.sensor_ray.position = (mid_x, 0.18, mid_z)
        self.sensor_ray.rotation_y = 0.0

        self.front_target_marker.enabled = True
        self.front_target_marker.position = (front_state.lateral_x, 0.55, front_state.forward_z)
