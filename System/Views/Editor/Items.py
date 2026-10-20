from __future__ import annotations

import math
import numpy
import random
from collections.abc import Callable
from dataclasses import dataclass

from OpenGL import GL

from System.Services import Player
from . import Constants, Geometry
from .GLMesh import GLMesh

IDENTITY_MATRIX_4 = numpy.eye(4, dtype = numpy.float32)


def fill_rotation_matrix(
        target_matrix:    numpy.ndarray,
        cosine_yaw:      float,
        sine_yaw:        float,
        cosine_pitch:    float,
        sine_pitch:      float,
        cosine_roll:     float,
        sine_roll:       float,
        translation_x:   float,
        translation_y:   float,
        translation_z:   float
    ) -> None:

    target_matrix[...] = IDENTITY_MATRIX_4
    target_matrix[0, 0] = cosine_roll * cosine_yaw
    target_matrix[0, 1] = cosine_roll * sine_yaw * sine_pitch - sine_roll * cosine_pitch
    target_matrix[0, 2] = cosine_roll * sine_yaw * cosine_pitch + sine_roll * sine_pitch
    target_matrix[1, 0] = sine_roll * cosine_yaw
    target_matrix[1, 1] = sine_roll * sine_yaw * sine_pitch + cosine_roll * cosine_pitch
    target_matrix[1, 2] = sine_roll * sine_yaw * cosine_pitch - cosine_roll * sine_pitch
    target_matrix[2, 0] = -sine_yaw
    target_matrix[2, 1] = cosine_yaw * sine_pitch
    target_matrix[2, 2] = cosine_yaw * cosine_pitch
    target_matrix[0, 3] = translation_x
    target_matrix[1, 3] = translation_y
    target_matrix[2, 3] = translation_z

# Painting Item Structure

@dataclass
class RuntimePaintingItem:
    mesh:                 GLMesh | None
    picture_index:        int
    position:             numpy.ndarray
    yaw_radians:          float
    falling:              bool  = False
    can_fall:             bool  = False
    fall_elapsed_seconds: float = 0.0
    impact_sound_played:  bool  = False
    fall_tilt_direction:  float = 1.0

# Television Geometry Generator

def append_box_volume_geometry(
        target_buffer:    list[float],
        box_center:       numpy.ndarray,
        box_extents:      numpy.ndarray,
        rotation_yaw:     float,
        wall_type_factor: float
    ) -> None:

    half_width  = box_extents[0] * 0.5
    half_height = box_extents[1] * 0.5
    half_depth  = box_extents[2] * 0.5

    cosine_yaw = math.cos(rotation_yaw)
    sine_yaw   = math.sin(rotation_yaw)

    def transform_local_point(
            local_x: float,
            local_y: float,
            local_z: float
        ) -> list[float]:

        rotated_x = local_x * cosine_yaw + local_z * sine_yaw
        rotated_z = -local_x * sine_yaw + local_z * cosine_yaw
        return [
            box_center[0] + rotated_x,
            box_center[1] + local_y,
            box_center[2] + rotated_z
        ]

    face_definitions = [
        ([0.0, 0.0, 1.0],  [(-half_width, -half_height,  half_depth), ( half_width, -half_height,  half_depth), ( half_width,  half_height,  half_depth), (-half_width,  half_height,  half_depth)]),
        ([0.0, 0.0, -1.0], [( half_width, -half_height, -half_depth), (-half_width, -half_height, -half_depth), (-half_width,  half_height, -half_depth), ( half_width,  half_height, -half_depth)]),
        ([-1.0, 0.0, 0.0], [(-half_width, -half_height, -half_depth), (-half_width, -half_height,  half_depth), (-half_width,  half_height,  half_depth), (-half_width,  half_height, -half_depth)]),
        ([1.0, 0.0, 0.0],  [( half_width, -half_height,  half_depth), ( half_width, -half_height, -half_depth), ( half_width,  half_height, -half_depth), ( half_width,  half_height,  half_depth)]),
        ([0.0, 1.0, 0.0],  [(-half_width,  half_height,  half_depth), ( half_width,  half_height,  half_depth), ( half_width,  half_height, -half_depth), (-half_width,  half_height, -half_depth)]),
        ([0.0, -1.0, 0.0], [(-half_width, -half_height, -half_depth), ( half_width, -half_height, -half_depth), ( half_width, -half_height,  half_depth), (-half_width, -half_height,  half_depth)])
    ]

    for normal_direction, corners in face_definitions:
        rotated_normal = [
            normal_direction[0] * cosine_yaw + normal_direction[2] * sine_yaw,
            normal_direction[1],
            -normal_direction[0] * sine_yaw + normal_direction[2] * cosine_yaw
        ]

        point_one   = transform_local_point(*corners[0])
        point_two   = transform_local_point(*corners[1])
        point_three = transform_local_point(*corners[2])
        point_four  = transform_local_point(*corners[3])

        for position, texture_coordinate in [
            (point_one,   [0.0, 1.0]),
            (point_two,   [1.0, 1.0]),
            (point_three, [1.0, 0.0]),
            (point_one,   [0.0, 1.0]),
            (point_three, [1.0, 0.0]),
            (point_four,  [0.0, 0.0])
        ]:
            target_buffer.extend([*position, *rotated_normal, *texture_coordinate, wall_type_factor])


def append_television_unit_geometry(
        target_buffer:     list[float],
        position_center:   numpy.ndarray,
        television_width:  float,
        television_height: float,
        television_depth:  float,
        rotation_yaw:      float,
        screen_wall_type:  float = 81.0
    ) -> None:

    cabinet_extents = numpy.array([television_width, television_height, television_depth], dtype = numpy.float32)
    append_box_volume_geometry(target_buffer, position_center, cabinet_extents, rotation_yaw, 80.0)

    screen_width       = television_width * 0.74
    screen_height      = television_height * 0.72
    half_screen_width  = screen_width * 0.5
    half_screen_height = screen_height * 0.5

    cosine_yaw   = math.cos(rotation_yaw)
    sine_yaw     = math.sin(rotation_yaw)
    front_offset = television_depth * 0.5 + 0.005

    def transform_screen_point(
            offset_horizontal: float,
            offset_vertical:   float
        ) -> list[float]:

        rotated_x = offset_horizontal * cosine_yaw + front_offset * sine_yaw
        rotated_z = -offset_horizontal * sine_yaw + front_offset * cosine_yaw
        return [
            position_center[0] + rotated_x,
            position_center[1] + offset_vertical,
            position_center[2] + rotated_z
        ]

    point_one   = transform_screen_point(-half_screen_width, -half_screen_height)
    point_two   = transform_screen_point( half_screen_width, -half_screen_height)
    point_three = transform_screen_point( half_screen_width,  half_screen_height)
    point_four  = transform_screen_point(-half_screen_width,  half_screen_height)

    screen_normal = [sine_yaw, 0.0, cosine_yaw]

    for position, texture_coordinate in [
        (point_one,   [0.0, 1.0]),
        (point_two,   [1.0, 1.0]),
        (point_three, [1.0, 0.0]),
        (point_one,   [0.0, 1.0]),
        (point_three, [1.0, 0.0]),
        (point_four,  [0.0, 0.0])
    ]:
        target_buffer.extend([*position, *screen_normal, *texture_coordinate, screen_wall_type])

# CRT Television Item Manager

class TelevisionCollection:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None
        self.sound_positions: list[tuple[float, float]] = []
        self.sound_check_timer_seconds: float = random.uniform(*Constants.TV_SOUND_CHECK_INTERVAL_SECONDS)

    def build_mesh(
            self,
            cell_scale_units: float,
            maze_dimension:   int,
            world_grid_array: numpy.ndarray
        ) -> None:

        candidate_floor_tiles = []
        cluster_count         = random.randint(12, 18)
        self.sound_positions.clear()

        for tile_x in range(2, maze_dimension - 2):
            for tile_z in range(2, maze_dimension - 2):
                if world_grid_array[tile_x, tile_z] != 0:
                    continue

                adjacent_wall_directions = []

                if world_grid_array[tile_x, tile_z - 1] == 1:
                    adjacent_wall_directions.append((0.0, -1.0, 0.0))

                if world_grid_array[tile_x, tile_z + 1] == 1:
                    adjacent_wall_directions.append((0.0, 1.0, math.pi))

                if world_grid_array[tile_x - 1, tile_z] == 1:
                    adjacent_wall_directions.append((-1.0, 0.0, math.pi * 0.5))

                if world_grid_array[tile_x + 1, tile_z] == 1:
                    adjacent_wall_directions.append((1.0, 0.0, -math.pi * 0.5))

                if not adjacent_wall_directions:
                    continue

                candidate_floor_tiles.append((tile_x, tile_z, random.choice(adjacent_wall_directions)))

        if not candidate_floor_tiles:
            return

        random.shuffle(candidate_floor_tiles)
        selected_tiles     = candidate_floor_tiles[:cluster_count]
        collected_vertices = []

        base_template_width  = 0.50
        base_template_height = 0.42
        base_template_depth  = 0.40

        def select_random_screen_type() -> float:
            if random.random() < 0.35:
                return 81.0

            return float(Constants.TV_BROADCAST_WALL_TYPE_BASE + random.randint(0, Constants.TV_CHANNEL_COUNT - 1))

        for tile_x, tile_z, (direction_x, direction_z, base_yaw) in selected_tiles:
            tile_center_x = (tile_x + 0.5) * cell_scale_units
            tile_center_z = (tile_z + 0.5) * cell_scale_units

            position_x = tile_center_x + direction_x * (cell_scale_units * 0.36)
            position_z = tile_center_z + direction_z * (cell_scale_units * 0.36)
            wobble_yaw = base_yaw + random.uniform(-0.20, 0.20)
            self.sound_positions.append((position_x, position_z))

            tangent_x = -direction_z
            tangent_z =  direction_x

            stack_configuration = random.choices(
                population = ["SINGLE", "TWO_FLOOR", "TWO_STACKED", "THREE_PYRAMID"],
                weights    = [0.30, 0.30, 0.20, 0.20],
                k          = 1
            )[0]

            if stack_configuration == "SINGLE":
                scale_factor      = random.uniform(0.75, 1.25)
                television_width  = base_template_width * scale_factor
                television_height = base_template_height * scale_factor
                television_depth  = base_template_depth * scale_factor

                cabinet_center = numpy.array([position_x, television_height * 0.5, position_z], dtype = numpy.float32)
                append_television_unit_geometry(
                    collected_vertices,
                    cabinet_center,
                    television_width,
                    television_height,
                    television_depth,
                    wobble_yaw,
                    select_random_screen_type()
                )

            elif stack_configuration == "TWO_FLOOR":
                scale_one      = random.uniform(0.72, 1.15)
                scale_two      = random.uniform(0.72, 1.15)
                width_one      = base_template_width * scale_one
                height_one     = base_template_height * scale_one
                depth_one      = base_template_depth * scale_one
                width_two      = base_template_width * scale_two
                height_two     = base_template_height * scale_two
                depth_two      = base_template_depth * scale_two
                spacing_offset = (width_one + width_two) * 0.52

                center_one = numpy.array([
                    position_x - tangent_x * (spacing_offset * 0.5),
                    height_one * 0.5,
                    position_z - tangent_z * (spacing_offset * 0.5)
                ], dtype = numpy.float32)

                center_two = numpy.array([
                    position_x + tangent_x * (spacing_offset * 0.5),
                    height_two * 0.5,
                    position_z + tangent_z * (spacing_offset * 0.5)
                ], dtype = numpy.float32)

                append_television_unit_geometry(
                    collected_vertices,
                    center_one,
                    width_one,
                    height_one,
                    depth_one,
                    wobble_yaw + random.uniform(-0.15, 0.15),
                    select_random_screen_type()
                )
                append_television_unit_geometry(
                    collected_vertices,
                    center_two,
                    width_two,
                    height_two,
                    depth_two,
                    wobble_yaw + random.uniform(-0.15, 0.15),
                    select_random_screen_type()
                )

            elif stack_configuration == "TWO_STACKED":
                scale_bottom  = random.uniform(0.95, 1.28)
                scale_top     = scale_bottom * random.uniform(0.68, 0.88)
                width_bottom  = base_template_width * scale_bottom
                height_bottom = base_template_height * scale_bottom
                depth_bottom  = base_template_depth * scale_bottom
                width_top     = base_template_width * scale_top
                height_top    = base_template_height * scale_top
                depth_top     = base_template_depth * scale_top

                center_bottom = numpy.array([position_x, height_bottom * 0.5, position_z], dtype = numpy.float32)
                center_top    = numpy.array([
                    position_x + random.uniform(-0.03, 0.03),
                    height_bottom + height_top * 0.5,
                    position_z + random.uniform(-0.03, 0.03)
                ], dtype = numpy.float32)

                append_television_unit_geometry(
                    collected_vertices,
                    center_bottom,
                    width_bottom,
                    height_bottom,
                    depth_bottom,
                    wobble_yaw,
                    select_random_screen_type()
                )
                append_television_unit_geometry(
                    collected_vertices,
                    center_top,
                    width_top,
                    height_top,
                    depth_top,
                    wobble_yaw + random.uniform(-0.25, 0.25),
                    select_random_screen_type()
                )

            elif stack_configuration == "THREE_PYRAMID":
                scale_one      = random.uniform(0.85, 1.15)
                scale_two      = random.uniform(0.85, 1.15)
                width_one      = base_template_width * scale_one
                height_one     = base_template_height * scale_one
                depth_one      = base_template_depth * scale_one
                width_two      = base_template_width * scale_two
                height_two     = base_template_height * scale_two
                depth_two      = base_template_depth * scale_two
                spacing_offset = (width_one + width_two) * 0.51

                center_one = numpy.array([
                    position_x - tangent_x * (spacing_offset * 0.5),
                    height_one * 0.5,
                    position_z - tangent_z * (spacing_offset * 0.5)
                ], dtype = numpy.float32)

                center_two = numpy.array([
                    position_x + tangent_x * (spacing_offset * 0.5),
                    height_two * 0.5,
                    position_z + tangent_z * (spacing_offset * 0.5)
                ], dtype = numpy.float32)

                scale_top      = min(scale_one, scale_two) * random.uniform(0.72, 0.90)
                width_top      = base_template_width * scale_top
                height_top     = base_template_height * scale_top
                depth_top      = base_template_depth * scale_top
                support_height = max(height_one, height_two)

                center_top = numpy.array([
                    position_x + random.uniform(-0.04, 0.04),
                    support_height + height_top * 0.5,
                    position_z + random.uniform(-0.04, 0.04)
                ], dtype = numpy.float32)

                append_television_unit_geometry(
                    collected_vertices,
                    center_one,
                    width_one,
                    height_one,
                    depth_one,
                    wobble_yaw + random.uniform(-0.12, 0.12),
                    select_random_screen_type()
                )
                append_television_unit_geometry(
                    collected_vertices,
                    center_two,
                    width_two,
                    height_two,
                    depth_two,
                    wobble_yaw + random.uniform(-0.12, 0.12),
                    select_random_screen_type()
                )
                append_television_unit_geometry(
                    collected_vertices,
                    center_top,
                    width_top,
                    height_top,
                    depth_top,
                    wobble_yaw + random.uniform(-0.25, 0.25),
                    select_random_screen_type()
                )

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(numpy.array(collected_vertices, dtype = numpy.float32), layout)

    def update_ambient_audio(
            self,
            delta_time_seconds:     float,
            player_camera_position: numpy.ndarray,
            calculate_audio_pan:    Callable[[float, float], float]
        ) -> None:

        self.sound_check_timer_seconds -= delta_time_seconds

        if self.sound_check_timer_seconds > 0.0:
            return

        self.sound_check_timer_seconds = random.uniform(*Constants.TV_SOUND_CHECK_INTERVAL_SECONDS)
        player_x = float(player_camera_position[0])
        player_z = float(player_camera_position[2])
        nearby_televisions = [
            (math.hypot(position_x - player_x, position_z - player_z), position_x, position_z)
            for position_x, position_z in self.sound_positions
            if math.hypot(position_x - player_x, position_z - player_z) <= Constants.TV_SOUND_PROXIMITY_RADIUS
        ]

        if not nearby_televisions or random.random() >= Constants.TV_SOUND_CHANCE_PER_CHECK:
            return

        source_distance, source_x, source_z = min(nearby_televisions)
        distance_gain = max(
            0.0,
            1.0 - source_distance / Constants.TV_SOUND_PROXIMITY_RADIUS
        ) ** Constants.TV_SOUND_DISTANCE_FALLOFF_POWER
        Player.ui_player.play_sound(
            f"{Constants.ANOMALY_SOUND_DIRECTORY}/{Constants.TV_SOUND_NAME}",
            volume                 = Constants.TV_SOUND_VOLUME * distance_gain,
            pan                    = calculate_audio_pan(source_x, source_z),
            loop                   = Constants.TV_SOUND_LOOP,
            enable_tone_randomizer = Constants.TV_SOUND_TONE_RANDOMIZER
        )
        self.sound_check_timer_seconds = random.uniform(*Constants.TV_SOUND_COOLDOWN_SECONDS)

    def draw(self) -> None:
        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

# Scanner Pickup Item Manager

class ScannerPickupItem:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None

    def build_mesh(self, device_world_position: numpy.ndarray) -> None:
        device_x, device_y, device_z = device_world_position
        half_box                     = 0.28
        scanner_vertices             = []

        for position, texture_coordinate in [
            ([device_x - half_box, device_y + 0.12, device_z - half_box], [0.0, 1.0]),
            ([device_x + half_box, device_y + 0.12, device_z - half_box], [1.0, 1.0]),
            ([device_x + half_box, device_y + 0.12, device_z + half_box], [1.0, 0.0]),
            ([device_x - half_box, device_y + 0.12, device_z - half_box], [0.0, 1.0]),
            ([device_x + half_box, device_y + 0.12, device_z + half_box], [1.0, 0.0]),
            ([device_x - half_box, device_y + 0.12, device_z + half_box], [0.0, 0.0])
        ]:
            scanner_vertices.extend([*position, 0.0, 1.0, 0.0, *texture_coordinate, 5.0])

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(numpy.array(scanner_vertices, dtype = numpy.float32), layout)

    def draw(self) -> None:
        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

# Sprite Entity Manager

class ChipsaEntityManager:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None

    def build_mesh(self, aspect_ratio: float) -> None:
        height_span = 0.8
        half_width  = height_span * aspect_ratio * 0.5
        sprite_data = numpy.array([
            -half_width, 0.0,         0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 301.0,
             half_width, 0.0,         0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 301.0,
             half_width, height_span, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 301.0,
            -half_width, 0.0,         0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 301.0,
             half_width, height_span, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 301.0,
            -half_width, height_span, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 301.0
        ], dtype = numpy.float32)

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(sprite_data, layout)

    def render(
            self,
            model_uniform_location: int,
            sprite_position:        numpy.ndarray,
            player_camera_position: numpy.ndarray
        ) -> None:

        if self.mesh is None:
            return

        delta_x = player_camera_position[0] - sprite_position[0]
        delta_z = player_camera_position[2] - sprite_position[2]
        yaw_rad = math.atan2(delta_x, delta_z)

        cosine_yaw = math.cos(yaw_rad)
        sine_yaw   = math.sin(yaw_rad)

        model_matrix = numpy.empty((4, 4), dtype = numpy.float32)
        model_matrix[...] = IDENTITY_MATRIX_4
        model_matrix[0, 0] = cosine_yaw
        model_matrix[0, 2] = sine_yaw
        model_matrix[2, 0] = -sine_yaw
        model_matrix[2, 2] = cosine_yaw
        model_matrix[0, 3] = sprite_position[0]
        model_matrix[1, 3] = sprite_position[1]
        model_matrix[2, 3] = sprite_position[2]

        GL.glUniformMatrix4fv(model_uniform_location, 1, GL.GL_FALSE, numpy.ascontiguousarray(model_matrix.T))
        self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

# Stalker Monster Manager

class MonsterEntityManager:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None

    def build_mesh(self) -> None:
        vertex_data = Geometry.generate_stalker_monster_vertex_buffer()
        layout      = [(0, 3), (1, 3), (2, 1)]
        self.mesh   = GLMesh(vertex_data, layout)

    def render(
            self,
            monster_shader_program: int,
            uniform_locations:      dict[str, int],
            monster_position:       numpy.ndarray,
            player_camera_position: numpy.ndarray,
            projection_matrix:      numpy.ndarray,
            view_matrix:            numpy.ndarray,
            elapsed_time_seconds:   float
        ) -> None:

        if self.mesh is None:
            return

        GL.glUseProgram(monster_shader_program)
        GL.glUniformMatrix4fv(uniform_locations["projection"], 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(uniform_locations["view"], 1, GL.GL_FALSE, view_matrix)

        offset_player = player_camera_position - monster_position
        facing_angle  = math.atan2(offset_player[0], offset_player[2])

        cosine_facing = math.cos(facing_angle)
        sine_facing   = math.sin(facing_angle)

        monster_matrix = numpy.empty((4, 4), dtype = numpy.float32)
        monster_matrix[...] = IDENTITY_MATRIX_4
        monster_matrix[0, 0] = cosine_facing
        monster_matrix[0, 2] = sine_facing
        monster_matrix[2, 0] = -sine_facing
        monster_matrix[2, 2] = cosine_facing
        monster_matrix[0, 3] = monster_position[0]
        monster_matrix[1, 3] = monster_position[1]
        monster_matrix[2, 3] = monster_position[2]

        GL.glUniformMatrix4fv(uniform_locations["model"], 1, GL.GL_FALSE, numpy.ascontiguousarray(monster_matrix.T))
        GL.glUniform3fv(uniform_locations["viewPos"], 1, player_camera_position)
        GL.glUniform1f(uniform_locations["time"], elapsed_time_seconds)
        GL.glUniform1f(uniform_locations["twitchIntensity"], 2.2)

        self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

# Painting Collection Manager

class PaintingCollection:
    def __init__(self) -> None:
        self.paintings_runtime_list: list[RuntimePaintingItem] = []
        self.fall_duration_seconds:  float                     = 0.65
        self.render_matrix:          numpy.ndarray             = numpy.empty((4, 4), dtype = numpy.float32)
        self.render_matrix_upload:   numpy.ndarray             = numpy.empty((4, 4), dtype = numpy.float32)
        self.static_mesh:            GLMesh | None              = None
        self.static_vertex_chunks:   list[numpy.ndarray]       = []

    def build_falling_paintings(
            self,
            available_paintings_count: int,
            maze_dimension:            int,
            cell_scale_units:          float,
            world_grid_array:          numpy.ndarray,
            player_camera_position:    numpy.ndarray
        ) -> None:

        if available_paintings_count == 0:
            return

        spawned_indices   = {painting.picture_index for painting in self.paintings_runtime_list}
        unspawned_indices = [index for index in range(available_paintings_count) if index not in spawned_indices]

        if not unspawned_indices:
            return

        wall_sides = [
            (0, -1, 0.0),
            (0, 1, math.pi),
            (-1, 0, math.pi / 2.0),
            (1, 0, -math.pi / 2.0)
        ]
        candidates = []

        for floor_x in range(1, maze_dimension - 1):
            for floor_z in range(1, maze_dimension - 1):
                if world_grid_array[floor_x, floor_z] != 0:
                    continue

                for offset_x, offset_z, yaw_radians in wall_sides:
                    wall_x = floor_x + offset_x
                    wall_z = floor_z + offset_z

                    if world_grid_array[wall_x, wall_z] != 1:
                        continue

                    if offset_x == -1:
                        position_x = floor_x * cell_scale_units + 0.05
                        position_z = (floor_z + 0.5) * cell_scale_units

                    elif offset_x == 1:
                        position_x = (floor_x + 1) * cell_scale_units - 0.05
                        position_z = (floor_z + 0.5) * cell_scale_units

                    elif offset_z == -1:
                        position_x = (floor_x + 0.5) * cell_scale_units
                        position_z = floor_z * cell_scale_units + 0.05

                    else:
                        position_x = (floor_x + 0.5) * cell_scale_units
                        position_z = (floor_z + 1) * cell_scale_units - 0.05

                    distance_from_player = math.hypot(
                        position_x - float(player_camera_position[0]),
                        position_z - float(player_camera_position[2])
                    )

                    if distance_from_player < 5.0:
                        continue

                    candidates.append((position_x, position_z, yaw_radians))

        painting_count = min(len(unspawned_indices), len(candidates))

        if painting_count == 0:
            return

        selected_positions = random.sample(candidates, painting_count)
        selected_indices   = random.sample(unspawned_indices, painting_count)
        layout             = [(0, 3), (1, 3), (2, 2), (3, 1)]
        static_vertex_chunks = []

        for (position_x, position_z, yaw_radians), picture_index in zip(selected_positions, selected_indices):
            vertex_data = Geometry.generate_painting_vertex_buffer(picture_index)
            can_fall    = random.random() < 0.01
            painting_mesh = GLMesh(vertex_data, layout) if can_fall else None

            if not can_fall:
                vertices = vertex_data.reshape(-1, 9)
                local_positions = vertices[:, :3].copy()
                local_normals = vertices[:, 3:6].copy()
                cosine_yaw = math.cos(yaw_radians)
                sine_yaw = math.sin(yaw_radians)

                vertices[:, 0] = position_x + local_positions[:, 0] * cosine_yaw + local_positions[:, 2] * sine_yaw
                vertices[:, 1] = 1.55 + local_positions[:, 1]
                vertices[:, 2] = position_z - local_positions[:, 0] * sine_yaw + local_positions[:, 2] * cosine_yaw
                vertices[:, 3] = local_normals[:, 0] * cosine_yaw + local_normals[:, 2] * sine_yaw
                vertices[:, 4] = local_normals[:, 1]
                vertices[:, 5] = -local_normals[:, 0] * sine_yaw + local_normals[:, 2] * cosine_yaw
                static_vertex_chunks.append(vertex_data)

            self.paintings_runtime_list.append(
                RuntimePaintingItem(
                    mesh                = painting_mesh,
                    picture_index       = picture_index,
                    position            = numpy.array([position_x, 1.55, position_z], dtype = numpy.float32),
                    yaw_radians         = yaw_radians,
                    can_fall            = can_fall,
                    fall_tilt_direction = random.choice([-1.0, 1.0])
                )
            )

        if static_vertex_chunks:
            self.static_vertex_chunks.extend(static_vertex_chunks)
            combined_vertices = numpy.concatenate(self.static_vertex_chunks)

            if self.static_mesh is None:
                self.static_mesh = GLMesh(combined_vertices, layout)
            else:
                self.static_mesh.rebuild(combined_vertices)

    def update_falling(
            self,
            delta_time_seconds:     float,
            player_camera_position: numpy.ndarray,
            calculate_audio_pan:    object
        ) -> None:

        for painting in self.paintings_runtime_list:
            if not painting.can_fall:
                continue

            distance_to_player = math.hypot(
                float(player_camera_position[0] - painting.position[0]),
                float(player_camera_position[2] - painting.position[2])
            )

            if not painting.falling and distance_to_player < 4.5:
                painting.falling  = True
                audio_pan         = calculate_audio_pan(float(painting.position[0]), float(painting.position[2]))
                Player.ui_player.play_sound(".vault/Anomaly/SparkPop", pan = audio_pan)

            if not painting.falling or painting.impact_sound_played:
                continue

            painting.fall_elapsed_seconds += delta_time_seconds

            if painting.fall_elapsed_seconds >= self.fall_duration_seconds * 0.58:
                painting.impact_sound_played = True
                audio_pan                    = calculate_audio_pan(float(painting.position[0]), float(painting.position[2]))
                Player.ui_player.play_sound(".vault/Anomaly/PaintingCrash", volume = 0.85, pan = audio_pan)

    def render(self, model_uniform_location: int) -> None:
        if self.static_mesh is not None:
            GL.glUniformMatrix4fv(model_uniform_location, 1, GL.GL_FALSE, IDENTITY_MATRIX_4)
            self.static_mesh.draw()

        for painting in self.paintings_runtime_list:
            if not painting.can_fall or painting.mesh is None:
                continue

            if not painting.falling:
                rotation_pitch      = 0.0
                rotation_roll       = 0.0
                rotation_yaw_wobble = 0.0
                position_y          = 1.55
                forward_offset      = 0.0

            else:
                progress_total = min(1.0, painting.fall_elapsed_seconds / self.fall_duration_seconds)
                impact_point   = 0.58

                if progress_total < impact_point:
                    fall_progress  = progress_total / impact_point
                    quadratic_fall = fall_progress * fall_progress

                    position_y          = 1.55 - (1.55 - 0.12) * quadratic_fall
                    forward_offset      = 0.22 * quadratic_fall
                    rotation_pitch      = quadratic_fall * (math.pi * 0.38)
                    rotation_roll       = math.sin(fall_progress * math.pi * 0.5) * 0.25 * painting.fall_tilt_direction
                    rotation_yaw_wobble = fall_progress * 0.12 * painting.fall_tilt_direction

                else:
                    settle_progress = (progress_total - impact_point) / (1.0 - impact_point)
                    damped_wave     = math.sin(settle_progress * math.pi * 3.0) * math.exp(-settle_progress * 4.2)

                    position_y          = 0.06 + max(0.0, damped_wave * 0.08)
                    forward_offset      = 0.22 + 0.06 * settle_progress
                    rotation_pitch      = math.pi * 0.5 - (1.0 - settle_progress) * 0.16
                    rotation_roll       = 0.25 * painting.fall_tilt_direction * math.exp(-settle_progress * 4.5) * math.cos(settle_progress * math.pi * 2.5)
                    rotation_yaw_wobble = (0.12 + 0.06 * settle_progress) * painting.fall_tilt_direction

            cosine_yaw = math.cos(painting.yaw_radians + rotation_yaw_wobble)
            sine_yaw   = math.sin(painting.yaw_radians + rotation_yaw_wobble)

            cosine_pitch = math.cos(rotation_pitch)
            sine_pitch   = math.sin(rotation_pitch)

            cosine_roll = math.cos(rotation_roll)
            sine_roll   = math.sin(rotation_roll)

            fill_rotation_matrix(
                self.render_matrix,
                cosine_yaw,
                sine_yaw,
                cosine_pitch,
                sine_pitch,
                cosine_roll,
                sine_roll,
                painting.position[0] + sine_yaw * forward_offset,
                position_y,
                painting.position[2] + cosine_yaw * forward_offset
            )

            self.render_matrix_upload[...] = self.render_matrix.T
            GL.glUniformMatrix4fv(model_uniform_location, 1, GL.GL_FALSE, self.render_matrix_upload)
            painting.mesh.draw()

    def cleanup(self) -> None:
        for painting in self.paintings_runtime_list:
            if painting.mesh is not None:
                painting.mesh.cleanup()

        if self.static_mesh is not None:
            self.static_mesh.cleanup()
            self.static_mesh = None

        self.paintings_runtime_list.clear()
        self.static_vertex_chunks.clear()

# Atmospheric Office Chair Collection

class ChairCollection:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None

    def build_mesh(
            self,
            cell_scale_units: float,
            maze_dimension:   int,
            world_grid_array: numpy.ndarray
        ) -> None:

        chair_count        = random.randint(14, 24)
        valid_tiles        = []
        collected_vertices = []

        for tile_x in range(2, maze_dimension - 2):
            for tile_z in range(2, maze_dimension - 2):
                if world_grid_array[tile_x, tile_z] == 0:
                    valid_tiles.append((tile_x, tile_z))

        if not valid_tiles:
            return

        selected_tiles = random.sample(valid_tiles, min(len(valid_tiles), chair_count))

        for tile_x, tile_z in selected_tiles:
            position_x = (tile_x + random.uniform(0.3, 0.7)) * cell_scale_units
            position_z = (tile_z + random.uniform(0.3, 0.7)) * cell_scale_units
            chair_yaw  = random.uniform(0.0, math.pi * 2.0)

            seat_center  = numpy.array([position_x, 0.44, position_z], dtype = numpy.float32)
            seat_extents = numpy.array([0.42, 0.08, 0.42], dtype = numpy.float32)
            append_box_volume_geometry(collected_vertices, seat_center, seat_extents, chair_yaw, 86.0)

            backrest_offset_x = math.sin(chair_yaw) * (-0.18)
            backrest_offset_z = math.cos(chair_yaw) * (-0.18)
            backrest_center   = numpy.array([position_x + backrest_offset_x, 0.72, position_z + backrest_offset_z], dtype = numpy.float32)
            backrest_extents  = numpy.array([0.40, 0.48, 0.06], dtype = numpy.float32)
            append_box_volume_geometry(collected_vertices, backrest_center, backrest_extents, chair_yaw, 86.0)

            pedestal_center  = numpy.array([position_x, 0.20, position_z], dtype = numpy.float32)
            pedestal_extents = numpy.array([0.08, 0.40, 0.08], dtype = numpy.float32)
            append_box_volume_geometry(collected_vertices, pedestal_center, pedestal_extents, chair_yaw, 80.0)

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(numpy.array(collected_vertices, dtype = numpy.float32), layout)

    def draw(self) -> None:
        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

# Interactive Dead Laptop Props

@dataclass
class RuntimeLaptopProp:
    position:             numpy.ndarray
    booted:               bool  = False
    boot_elapsed_seconds: float = 0.0

class LaptopCollection:
    def __init__(self) -> None:
        self.mesh:        GLMesh | None          = None
        self.laptop_list: list[RuntimeLaptopProp] = []

    def build_mesh(
            self,
            cell_scale_units: float,
            maze_dimension:   int,
            world_grid_array: numpy.ndarray
        ) -> None:

        self.laptop_list.clear()
        collected_vertices = []
        valid_tiles        = []

        for tile_x in range(3, maze_dimension - 3):
            for tile_z in range(3, maze_dimension - 3):
                if world_grid_array[tile_x, tile_z] == 0:
                    valid_tiles.append((tile_x, tile_z))

        if not valid_tiles:
            return

        selected_tiles = random.sample(valid_tiles, min(len(valid_tiles), 4))

        for tile_x, tile_z in selected_tiles:
            position_x = (tile_x + 0.5) * cell_scale_units
            position_z = (tile_z + 0.5) * cell_scale_units
            yaw_angle  = random.uniform(0.0, math.pi * 2.0)

            self.laptop_list.append(
                RuntimeLaptopProp(position = numpy.array([position_x, 0.04, position_z], dtype = numpy.float32))
            )

            base_center  = numpy.array([position_x, 0.02, position_z], dtype = numpy.float32)
            base_extents = numpy.array([0.34, 0.03, 0.24], dtype = numpy.float32)
            append_box_volume_geometry(collected_vertices, base_center, base_extents, yaw_angle, 80.0)

            screen_offset_x = math.sin(yaw_angle) * (-0.10)
            screen_offset_z = math.cos(yaw_angle) * (-0.10)
            screen_center   = numpy.array([position_x + screen_offset_x, 0.14, position_z + screen_offset_z], dtype = numpy.float32)
            screen_extents  = numpy.array([0.32, 0.22, 0.02], dtype = numpy.float32)
            append_box_volume_geometry(collected_vertices, screen_center, screen_extents, yaw_angle, 87.0)

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(numpy.array(collected_vertices, dtype = numpy.float32), layout)

    def update(self, delta_time_seconds: float) -> None:
        for laptop in self.laptop_list:
            if not laptop.booted:
                continue

            laptop.boot_elapsed_seconds += delta_time_seconds

    def check_interaction(self, player_position: numpy.ndarray) -> str | None:
        for laptop in self.laptop_list:
            distance = numpy.linalg.norm(player_position - laptop.position)

            if distance < 2.0:
                if not laptop.booted:
                    laptop.booted = True
                    return Constants.LAPTOP_TEXTS[0]

                return Constants.LAPTOP_TEXTS[1]

        return None

    def draw(self) -> None:
        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

        self.laptop_list.clear()

# Corner Shadows

class CornerShadowCollection:
    def __init__(self) -> None:
        self.mesh: GLMesh | None = None

    def build_mesh(
            self,
            cell_scale_units: float,
            maze_dimension:   int,
            world_grid_array: numpy.ndarray
        ) -> None:

        collected_vertices = []
        corner_count       = random.randint(8, 14)
        junction_tiles     = []

        for tile_x in range(2, maze_dimension - 2):
            for tile_z in range(2, maze_dimension - 2):
                if world_grid_array[tile_x, tile_z] == 0:
                    wall_neighbors = sum([
                        world_grid_array[tile_x + 1, tile_z],
                        world_grid_array[tile_x - 1, tile_z],
                        world_grid_array[tile_x, tile_z + 1],
                        world_grid_array[tile_x, tile_z - 1]
                    ])

                    if wall_neighbors >= 2:
                        junction_tiles.append((tile_x, tile_z))

        if not junction_tiles:
            return

        selected_junctions = random.sample(junction_tiles, min(len(junction_tiles), corner_count))

        for tile_x, tile_z in selected_junctions:
            center_x = (tile_x + 0.5) * cell_scale_units
            center_z = (tile_z + 0.5) * cell_scale_units

            for position, normal, texture_coordinate in [
                ([center_x - 0.45, 0.0, center_z], [0.0, 0.0, 1.0], [0.0, 1.0]),
                ([center_x + 0.45, 0.0, center_z], [0.0, 0.0, 1.0], [1.0, 1.0]),
                ([center_x + 0.45, 2.3, center_z], [0.0, 0.0, 1.0], [1.0, 0.0]),
                ([center_x - 0.45, 0.0, center_z], [0.0, 0.0, 1.0], [0.0, 1.0]),
                ([center_x + 0.45, 2.3, center_z], [0.0, 0.0, 1.0], [1.0, 0.0]),
                ([center_x - 0.45, 2.3, center_z], [0.0, 0.0, 1.0], [0.0, 0.0])
            ]:
                collected_vertices.extend([*position, *normal, *texture_coordinate, 78.0])

        layout    = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.mesh = GLMesh(numpy.array(collected_vertices, dtype = numpy.float32), layout)

    def update(self, player_position: numpy.ndarray) -> None:
        pass

    def draw(self) -> None:
        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None
