from __future__ import annotations

import math
import numpy

from OpenGL import GL

from .GLMesh import GLMesh
from . import Lamps

# Lamp Collection and Renderer

class LampRenderer:
    def __init__(self) -> None:
        self.lamps_list:            list[Lamps.FluorescentLamp] = []
        self.wall_height_units:     float                       = 2.8

        self.fixtures_mesh:         GLMesh | None               = None
        self.tubes_mesh:            GLMesh | None               = None
        self.sparks_mesh:           GLMesh | None               = None

        self.tubes_need_rebuild:    bool                        = False
        self.sparks_need_rebuild:   bool                        = False
        self.cached_spark_vertices: list[float]                 = []
        self.cached_light_positions: numpy.ndarray              = numpy.zeros((8, 3), dtype = numpy.float32)
        self.cached_light_colors:    numpy.ndarray              = numpy.zeros((8, 3), dtype = numpy.float32)
        self.base_lamp_color:        numpy.ndarray              = numpy.array([1.35, 1.28, 1.05], dtype = numpy.float32)

    def initialize_lamps(
            self,
            lamp_world_positions: list[tuple[float, float]],
            wall_height_units:    float
        ) -> None:

        self.wall_height_units = wall_height_units
        self.lamps_list.clear()

        for position_x, position_z in lamp_world_positions:
            self.lamps_list.append(Lamps.instantiate_random_lamp(position_x, position_z))

        self.build_fixtures_mesh()
        self.upload_tubes_mesh()

    def build_fixtures_mesh(self) -> None:
        collected_vertices = []
        half_width         = 0.35
        half_length        = 0.85
        ceiling_height     = self.wall_height_units
        bottom_height      = self.wall_height_units - 0.08

        for lamp in self.lamps_list:
            lamp_x = lamp.position_x
            lamp_z = lamp.position_z

            quads = [
                ([lamp_x - half_width, bottom_height, lamp_z - half_length], [lamp_x + half_width, bottom_height, lamp_z - half_length], [lamp_x + half_width, ceiling_height, lamp_z - half_length], [lamp_x - half_width, ceiling_height, lamp_z - half_length], [0.0, 0.0, -1.0]),
                ([lamp_x + half_width, bottom_height, lamp_z + half_length], [lamp_x - half_width, bottom_height, lamp_z + half_length], [lamp_x - half_width, ceiling_height, lamp_z + half_length], [lamp_x + half_width, ceiling_height, lamp_z + half_length], [0.0, 0.0, 1.0]),
                ([lamp_x - half_width, bottom_height, lamp_z + half_length], [lamp_x - half_width, bottom_height, lamp_z - half_length], [lamp_x - half_width, ceiling_height, lamp_z - half_length], [lamp_x - half_width, ceiling_height, lamp_z + half_length], [-1.0, 0.0, 0.0]),
                ([lamp_x + half_width, bottom_height, lamp_z - half_length], [lamp_x + half_width, bottom_height, lamp_z + half_length], [lamp_x + half_width, ceiling_height, lamp_z + half_length], [lamp_x + half_width, ceiling_height, lamp_z - half_length], [1.0, 0.0, 0.0])
            ]

            for point_one, point_two, point_three, point_four, normal in quads:
                for vertex_position, texture_coordinate in [
                    (point_one,   [0.0, 1.0]),
                    (point_two,   [1.0, 1.0]),
                    (point_three, [1.0, 0.0]),
                    (point_one,   [0.0, 1.0]),
                    (point_three, [1.0, 0.0]),
                    (point_four,  [0.0, 0.0])
                ]:
                    collected_vertices.extend([*vertex_position, *normal, *texture_coordinate, 4.0])

        layout             = [(0, 3), (1, 3), (2, 2), (3, 1)]
        self.fixtures_mesh = GLMesh(numpy.array(collected_vertices, dtype = numpy.float32), layout)

    def upload_tubes_mesh(self) -> None:
        collected_vertices = []
        half_width         = 0.35
        half_length        = 0.85
        bottom_height      = self.wall_height_units - 0.081

        for lamp in self.lamps_list:
            lamp_x    = lamp.position_x
            lamp_z    = lamp.position_z
            wall_type = 4.0 if (lamp.is_broken or lamp.flicker_factor <= 0.05) else 3.0

            point_one   = [lamp_x - half_width + 0.06, bottom_height, lamp_z + half_length - 0.06]
            point_two   = [lamp_x + half_width - 0.06, bottom_height, lamp_z + half_length - 0.06]
            point_three = [lamp_x + half_width - 0.06, bottom_height, lamp_z - half_length + 0.06]
            point_four  = [lamp_x - half_width + 0.06, bottom_height, lamp_z - half_length + 0.06]

            for vertex_position, texture_coordinate in [
                (point_one,   [0.0, 1.0]),
                (point_two,   [1.0, 1.0]),
                (point_three, [1.0, 0.0]),
                (point_one,   [0.0, 1.0]),
                (point_three, [1.0, 0.0]),
                (point_four,  [0.0, 0.0])
            ]:
                collected_vertices.extend([*vertex_position, 0.0, -1.0, 0.0, *texture_coordinate, wall_type])

        layout           = [(0, 3), (1, 3), (2, 2), (3, 1)]
        raw_buffer_bytes = numpy.array(collected_vertices, dtype = numpy.float32)

        if self.tubes_mesh is None:
            self.tubes_mesh = GLMesh(raw_buffer_bytes, layout, usage_pattern = GL.GL_DYNAMIC_DRAW)

        else:
            self.tubes_mesh.rebuild(raw_buffer_bytes)

    def upload_sparks_mesh(self) -> None:
        if not self.cached_spark_vertices:
            if self.sparks_mesh is not None:
                self.sparks_mesh.vertex_count = 0

            return

        raw_buffer_bytes = numpy.array(self.cached_spark_vertices, dtype = numpy.float32)
        layout           = [(0, 3), (1, 3), (2, 2), (3, 1)]

        if self.sparks_mesh is None:
            self.sparks_mesh = GLMesh(raw_buffer_bytes, layout, usage_pattern = GL.GL_DYNAMIC_DRAW)

        else:
            self.sparks_mesh.rebuild(raw_buffer_bytes)

    def update(
            self,
            delta_time_seconds:     float,
            calculate_audio_pan:    object,
            player_camera_position: numpy.ndarray
        ) -> None:

        all_spark_vertices = []
        player_position_x  = float(player_camera_position[0])
        player_position_z  = float(player_camera_position[2])

        for lamp in self.lamps_list:
            distance_to_player   = math.hypot(lamp.position_x - player_position_x, lamp.position_z - player_position_z)
            visual_state_changed = lamp.update(
                delta_time_seconds,
                calculate_audio_pan,
                self.wall_height_units,
                distance_to_player
            )

            if visual_state_changed:
                self.tubes_need_rebuild = True

            self.update_lamp_sparks(lamp, delta_time_seconds, all_spark_vertices)

        self.cached_spark_vertices = all_spark_vertices
        self.sparks_need_rebuild   = True

    def update_lamp_sparks(
            self,
            lamp:               Lamps.FluorescentLamp,
            delta_time_seconds: float,
            all_spark_vertices: list[float]
        ) -> None:

        if not lamp.active_sparks_list:
            return

        alive_sparks         = []
        gravity_acceleration = 9.8

        for spark in lamp.active_sparks_list:
            spark.life_seconds -= delta_time_seconds

            if spark.life_seconds <= 0.0:
                continue

            spark.velocity_y -= gravity_acceleration * delta_time_seconds
            spark.position_x += spark.velocity_x * delta_time_seconds
            spark.position_y += spark.velocity_y * delta_time_seconds
            spark.position_z += spark.velocity_z * delta_time_seconds

            if spark.position_y < 0.02:
                spark.position_y  = 0.02
                spark.velocity_y  = -spark.velocity_y * 0.35
                spark.velocity_x *= 0.65
                spark.velocity_z *= 0.65

            alive_sparks.append(spark)

            spark_size  = 0.028 * (spark.life_seconds / spark.total_life_duration_seconds)
            pixel_x     = spark.position_x
            pixel_y     = spark.position_y
            pixel_z     = spark.position_z
            point_one   = [pixel_x - spark_size, pixel_y - spark_size, pixel_z]
            point_two   = [pixel_x + spark_size, pixel_y - spark_size, pixel_z]
            point_three = [pixel_x + spark_size, pixel_y + spark_size, pixel_z]
            point_four  = [pixel_x - spark_size, pixel_y + spark_size, pixel_z]

            for position, texture_coordinate in [
                (point_one,   [0.0, 1.0]),
                (point_two,   [1.0, 1.0]),
                (point_three, [1.0, 0.0]),
                (point_one,   [0.0, 1.0]),
                (point_three, [1.0, 0.0]),
                (point_four,  [0.0, 0.0])
            ]:
                all_spark_vertices.extend([*position, 0.0, 0.0, 1.0, *texture_coordinate, 82.0])

        lamp.active_sparks_list = alive_sparks

    def get_active_lamp_lighting_data(
            self,
            player_camera_position: numpy.ndarray,
            maximum_lights:         int = 8
        ) -> tuple[numpy.ndarray, numpy.ndarray, int]:

        player_x = float(player_camera_position[0])
        player_z = float(player_camera_position[2])

        positions_array = self.cached_light_positions
        colors_array    = self.cached_light_colors

        if positions_array.shape[0] != maximum_lights:
            positions_array = numpy.zeros((maximum_lights, 3), dtype = numpy.float32)
            colors_array    = numpy.zeros((maximum_lights, 3), dtype = numpy.float32)
            self.cached_light_positions = positions_array
            self.cached_light_colors    = colors_array

        positions_array.fill(0.0)
        colors_array.fill(0.0)

        if maximum_lights == 0:
            return positions_array, colors_array, 0

        selected_lamps: list[tuple[float, Lamps.FluorescentLamp]] = []

        for lamp in self.lamps_list:
            if lamp.is_broken or lamp.flicker_factor <= 0.02:
                continue

            distance = math.hypot(lamp.position_x - player_x, lamp.position_z - player_z)
            if len(selected_lamps) == maximum_lights and distance >= selected_lamps[-1][0]:
                continue

            insertion_index = 0

            while insertion_index < len(selected_lamps) and selected_lamps[insertion_index][0] <= distance:
                insertion_index += 1

            selected_lamps.insert(insertion_index, (distance, lamp))

            if len(selected_lamps) > maximum_lights:
                selected_lamps.pop()

        for lamp_index, (_, lamp) in enumerate(selected_lamps):
            positions_array[lamp_index] = (lamp.position_x, self.wall_height_units - 0.12, lamp.position_z)
            numpy.multiply(self.base_lamp_color, lamp.flicker_factor, out = colors_array[lamp_index])

        return positions_array, colors_array, len(selected_lamps)

    def render_fixtures(self) -> None:
        if self.fixtures_mesh is not None:
            self.fixtures_mesh.draw()

    def render_tubes(self) -> None:
        if self.tubes_need_rebuild:
            self.tubes_need_rebuild = False
            self.upload_tubes_mesh()

        if self.tubes_mesh is not None:
            self.tubes_mesh.draw()

    def render_sparks(self) -> None:
        if self.sparks_need_rebuild:
            self.sparks_need_rebuild = False
            self.upload_sparks_mesh()

        if self.sparks_mesh is not None:
            self.sparks_mesh.draw()

    def cleanup(self) -> None:
        if self.fixtures_mesh is not None:
            self.fixtures_mesh.cleanup()
            self.fixtures_mesh = None

        if self.tubes_mesh is not None:
            self.tubes_mesh.cleanup()
            self.tubes_mesh = None

        if self.sparks_mesh is not None:
            self.sparks_mesh.cleanup()
            self.sparks_mesh = None