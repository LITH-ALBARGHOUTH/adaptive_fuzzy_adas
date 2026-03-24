"""3D world construction and debug visualization."""

from __future__ import annotations

import math

from ursina import AmbientLight, DirectionalLight, Entity, Sky, Vec3, color

from config import DemoConfig
from vehicle import EgoVehicleState, TrafficVehicleState


class DrivingWorld:
    """Builds the lightweight road scene and debug markers."""

    def __init__(self, config: DemoConfig) -> None:
        self.config = config
        self.current_scenario_name = "normal_driving"
        self._lane_markers = []
        self._roadside_props = []
        self._lane_center_entities = []
        self._debug_entities = []
        self._poor_road_entities = []
        self._build_scene()

    def _build_scene(self) -> None:
        road_width = (
            self.config.road_lane_count * self.config.lane_width_m
            + (2.0 * self.config.road_width_margin_m)
        )
        half_road_width = road_width * 0.5
        center_yellow_offset = 0.11

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
        self.ego_lane_band = Entity(
            model="cube",
            color=color.rgba(55, 175, 230, 48),
            scale=(self.config.lane_width_m * 0.92, 0.012, self.config.road_length_m),
            position=(self.config.ego_lane_visual_offset_m, 0.028, self.config.road_length_m * 0.45),
        )
        self.oncoming_lane_band = Entity(
            model="cube",
            color=color.rgba(225, 105, 75, 36),
            scale=(self.config.lane_width_m * 0.92, 0.011, self.config.road_length_m),
            position=(-self.config.ego_lane_visual_offset_m, 0.027, self.config.road_length_m * 0.45),
        )

        for edge_x in (-half_road_width + 0.15, half_road_width - 0.15):
            self._lane_markers.append(
                Entity(
                    model="cube",
                    color=color.rgb(236, 236, 236),
                    scale=(0.10, 0.02, self.config.road_length_m),
                    position=(edge_x, 0.03, self.config.road_length_m * 0.45),
                )
            )

        for divider_x in (-center_yellow_offset, center_yellow_offset):
            self._lane_markers.append(
                Entity(
                    model="cube",
                    color=color.rgb(240, 198, 54),
                    scale=(0.10, 0.022, self.config.road_length_m),
                    position=(divider_x, 0.032, self.config.road_length_m * 0.45),
                )
            )

        dash_positions = range(0, int(self.config.road_length_m), 16)
        lane_centers = [
            self.config.ego_lane_visual_offset_m,
            -self.config.ego_lane_visual_offset_m,
        ]
        lane_colors = [
            color.rgba(80, 225, 255, 150),
            color.rgba(255, 170, 120, 125),
        ]
        for lane_center, dash_color in zip(lane_centers, lane_colors):
            for dash_z in dash_positions:
                self._lane_markers.append(
                    Entity(
                        model="cube",
                        color=dash_color,
                        scale=(0.14, 0.025, 6.0),
                        position=(lane_center, 0.035, dash_z),
                    )
                )

        for side_x in (-road_width * 0.6, road_width * 0.6):
            for prop_z in range(20, int(self.config.road_length_m), 45):
                prop = Entity(
                    model="cube",
                    color=color.rgb(90, 160, 92),
                    scale=(2.2, 5.5, 2.2),
                    position=(side_x, 2.75, prop_z),
                )
                self._roadside_props.append(prop)

        poor_road_layout = [
            (self.config.ego_lane_visual_offset_m - 0.55, 110.0, 1.10, 10.0),
            (self.config.ego_lane_visual_offset_m + 0.35, 182.0, 0.95, 8.0),
            (self.config.ego_lane_visual_offset_m - 0.20, 265.0, 1.35, 11.0),
            (self.config.ego_lane_visual_offset_m + 0.60, 338.0, 1.05, 9.0),
        ]
        for patch_x, patch_z, patch_width, patch_length in poor_road_layout:
            crater = Entity(
                model="cube",
                color=color.rgb(35, 35, 38),
                scale=(patch_width, 0.03, patch_length),
                position=(patch_x, -0.01, patch_z),
                enabled=False,
            )
            warning_plate = Entity(
                model="cube",
                color=color.rgba(245, 160, 48, 170),
                scale=(patch_width * 0.85, 0.012, patch_length * 0.35),
                position=(patch_x, 0.035, patch_z - (patch_length * 0.2)),
                enabled=False,
            )
            self._poor_road_entities.extend([crater, warning_plate])

        self.target_lane_line = Entity(
            model="cube",
            color=color.rgba(60, 240, 255, 160),
            scale=(0.10, 0.03, self.config.road_length_m),
            position=(self.config.ego_lane_visual_offset_m, 0.045, self.config.road_length_m * 0.45),
            enabled=True,
        )
        self._lane_center_entities.append(self.target_lane_line)
        ramp_length = self.config.uphill_ramp_end_m - self.config.uphill_ramp_start_m
        ramp_center_z = self.config.uphill_ramp_start_m + (ramp_length * 0.5)
        ramp_pitch_deg = self.uphill_pitch_degrees()
        ramp_center_y = self.config.uphill_ramp_height_m * 0.5
        self.uphill_ramp = Entity(
            model="cube",
            color=color.rgb(73, 73, 77),
            scale=(road_width, 0.18, ramp_length),
            position=(0.0, ramp_center_y, ramp_center_z),
            rotation_x=-ramp_pitch_deg,
            enabled=False,
        )
        self.uphill_lane_highlight = Entity(
            model="cube",
            color=color.rgba(70, 200, 255, 88),
            scale=(self.config.lane_width_m * 0.82, 0.06, ramp_length),
            position=(self.config.ego_lane_visual_offset_m, ramp_center_y + 0.07, ramp_center_z),
            rotation_x=-ramp_pitch_deg,
            enabled=False,
        )

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

    def uphill_pitch_degrees(self) -> float:
        """Return the pitch angle for the visible uphill ramp."""

        ramp_length = max(1.0, self.config.uphill_ramp_end_m - self.config.uphill_ramp_start_m)
        return math.degrees(math.atan2(self.config.uphill_ramp_height_m, ramp_length))

    def configure_for_scenario(self, scenario_name: str) -> None:
        """Toggle scenario-specific world visuals."""

        self.current_scenario_name = scenario_name
        show_uphill = scenario_name == "uphill_grade_challenge"
        show_poor_road = scenario_name == "poor_road_condition"
        self.uphill_ramp.enabled = show_uphill
        self.uphill_lane_highlight.enabled = show_uphill
        for entity in self._poor_road_entities:
            entity.enabled = show_poor_road

    def lane_visual_x(self, lateral_x: float, lane_center_offset: float) -> float:
        """Map the controller's lateral state into the rendered lane space."""

        return lane_center_offset + (lateral_x * self.config.lane_visual_scale)

    def lane_id_from_visual_x(self, visual_x: float) -> int:
        """Return rendered lane identity: 1 right, -1 left, 0 divider."""

        if visual_x > 0.35:
            return 1
        if visual_x < -0.35:
            return -1
        return 0

    def offroad_limit_x(self) -> float:
        """Return the lateral limit beyond which the vehicle is considered off-road."""

        road_width = (
            self.config.road_lane_count * self.config.lane_width_m
            + (2.0 * self.config.road_width_margin_m)
        )
        return (road_width * 0.5) - 0.35

    def road_height_and_pitch(self, forward_z: float) -> tuple[float, float]:
        """Return rendered road height and pitch for the active scenario."""

        if self.current_scenario_name != "uphill_grade_challenge":
            return 0.0, 0.0

        start_z = self.config.uphill_ramp_start_m
        end_z = self.config.uphill_ramp_end_m
        if forward_z <= start_z:
            return 0.0, 0.0
        if forward_z >= end_z:
            return self.config.uphill_ramp_height_m, self.uphill_pitch_degrees()

        progress = (forward_z - start_z) / max(1.0, end_z - start_z)
        return self.config.uphill_ramp_height_m * progress, self.uphill_pitch_degrees()

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
        lane_visual_offset: float = 0.0,
    ) -> None:
        """Update sensor-ray and guide marker positions."""

        if not show_debug or front_distance <= 0.0:
            self.sensor_ray.enabled = False
            self.front_target_marker.enabled = False
            return

        clipped_distance = max(0.1, min(front_distance, 120.0))
        mid_z = ego_state.forward_z + (clipped_distance * 0.5)
        mid_x = self.lane_visual_x(
            (ego_state.lateral_x + front_state.lateral_x) * 0.5,
            lane_visual_offset,
        )
        road_height, road_pitch = self.road_height_and_pitch(mid_z)

        self.sensor_ray.enabled = True
        self.sensor_ray.scale = (0.08, 0.08, clipped_distance)
        self.sensor_ray.position = (mid_x, road_height + 0.18, mid_z)
        self.sensor_ray.rotation_y = 0.0
        self.sensor_ray.rotation_x = road_pitch

        self.front_target_marker.enabled = True
        front_height, _ = self.road_height_and_pitch(front_state.forward_z)
        self.front_target_marker.position = (
            self.lane_visual_x(front_state.lateral_x, lane_visual_offset),
            front_height + 0.55,
            front_state.forward_z,
        )
