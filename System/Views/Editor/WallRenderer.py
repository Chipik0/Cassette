from __future__ import annotations

import numpy
from OpenGL import GL

from .GLMesh import GLMesh
from . import WallTypes

# Quad Mesh Helpers

def append_vertex_quad_data(
        target_buffer:    list[float],
        point_one:        list[float],
        point_two:        list[float],
        point_three:      list[float],
        point_four:       list[float],
        normal_vector:    list[float],
        wall_type_factor: float
    ) -> None:

    vertices_sequence = [
        (point_one,   [0.0, 1.0]),
        (point_two,   [1.0, 1.0]),
        (point_three, [1.0, 0.0]),
        (point_one,   [0.0, 1.0]),
        (point_three, [1.0, 0.0]),
        (point_four,  [0.0, 0.0])
    ]

    for vertex_position, texture_coordinate in vertices_sequence:
        target_buffer.extend([*vertex_position, *normal_vector, *texture_coordinate, wall_type_factor])

# Maze Wall Renderer

class WallRenderer:
    def __init__(self) -> None:
        self.mesh:                   GLMesh | None         = None
        self.white_noise_walls_list: list[tuple[int, int]] = []
        self.cached_vertex_buffer:   numpy.ndarray | None  = None
        self.needs_mesh_rebuild:     bool                  = False

    def build_monolithic_maze_mesh(
            self,
            cell_scale_units:  float,
            maze_dimension:    int,
            wall_height_units: float,
            world_grid_array:  numpy.ndarray,
            floor_active:      bool = True
        ) -> None:

        collected_vertices = []
        total_span         = maze_dimension * cell_scale_units
        self.white_noise_walls_list.clear()

        if floor_active:
            append_vertex_quad_data(collected_vertices, [0.0, 0.0, 0.0], [0.0, 0.0, total_span], [total_span, 0.0, total_span], [total_span, 0.0, 0.0], [0.0, 1.0, 0.0], 0.0)

        append_vertex_quad_data(collected_vertices, [0.0, wall_height_units, 0.0], [total_span, wall_height_units, 0.0], [total_span, wall_height_units, total_span], [0.0, wall_height_units, total_span], [0.0, -1.0, 0.0], 0.0)

        for tile_x in range(maze_dimension):
            for tile_z in range(maze_dimension):
                if world_grid_array[tile_x, tile_z] != 1:
                    continue

                descriptor = WallTypes.determine_wall_type_from_grid_coordinate(tile_x, tile_z)

                if descriptor.has_proximity_glitch_effect:
                    self.white_noise_walls_list.append((tile_x, tile_z))

                origin_minimum_x = tile_x * cell_scale_units
                origin_maximum_x = (tile_x + 1) * cell_scale_units
                origin_minimum_z = tile_z * cell_scale_units
                origin_maximum_z = (tile_z + 1) * cell_scale_units

                append_vertex_quad_data(collected_vertices, [origin_minimum_x, 0.0, origin_maximum_z], [origin_maximum_x, 0.0, origin_maximum_z], [origin_maximum_x, wall_height_units, origin_maximum_z], [origin_minimum_x, wall_height_units, origin_maximum_z], [0.0, 0.0, 1.0], descriptor.type_identifier)
                append_vertex_quad_data(collected_vertices, [origin_maximum_x, 0.0, origin_minimum_z], [origin_minimum_x, 0.0, origin_minimum_z], [origin_minimum_x, wall_height_units, origin_minimum_z], [origin_maximum_x, wall_height_units, origin_minimum_z], [0.0, 0.0, -1.0], descriptor.type_identifier)
                append_vertex_quad_data(collected_vertices, [origin_minimum_x, 0.0, origin_minimum_z], [origin_minimum_x, 0.0, origin_maximum_z], [origin_minimum_x, wall_height_units, origin_maximum_z], [origin_minimum_x, wall_height_units, origin_minimum_z], [-1.0, 0.0, 0.0], descriptor.type_identifier)
                append_vertex_quad_data(collected_vertices, [origin_maximum_x, 0.0, origin_maximum_z], [origin_maximum_x, 0.0, origin_minimum_z], [origin_maximum_x, wall_height_units, origin_minimum_z], [origin_maximum_x, wall_height_units, origin_maximum_z], [1.0, 0.0, 0.0], descriptor.type_identifier)

        self.cached_vertex_buffer = numpy.array(collected_vertices, dtype = numpy.float32)
        self.needs_mesh_rebuild   = True

    def render_walls(self) -> None:
        if self.needs_mesh_rebuild and self.cached_vertex_buffer is not None:
            self.needs_mesh_rebuild = False
            layout                  = [(0, 3), (1, 3), (2, 2), (3, 1)]

            if self.mesh is None:
                self.mesh = GLMesh(self.cached_vertex_buffer, layout, usage_pattern = GL.GL_DYNAMIC_DRAW)

            else:
                self.mesh.rebuild(self.cached_vertex_buffer)

        if self.mesh is not None:
            self.mesh.draw()

    def cleanup(self) -> None:
        if self.mesh is not None:
            self.mesh.cleanup()
            self.mesh = None

        self.cached_vertex_buffer = None
        self.needs_mesh_rebuild   = False