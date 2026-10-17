from __future__ import annotations

import math
import numpy

# Matrix Transformations

def perspective_matrix(
        field_of_view_y: float,
        aspect_ratio:    float,
        near_plane:      float,
        far_plane:       float
    ) -> numpy.ndarray:

    radians  = math.radians(field_of_view_y)
    tan_half = math.tan(radians / 2.0)

    result_matrix       = numpy.zeros((4, 4), dtype = numpy.float32)
    result_matrix[0, 0] = 1.0 / (aspect_ratio * tan_half)
    result_matrix[1, 1] = 1.0 / tan_half
    result_matrix[2, 2] = -(far_plane + near_plane) / (far_plane - near_plane)
    result_matrix[2, 3] = -1.0
    result_matrix[3, 2] = -(2.0 * far_plane * near_plane) / (far_plane - near_plane)

    return result_matrix


def look_at(
        eye_position:    numpy.ndarray,
        target_position: numpy.ndarray,
        up_vector:       numpy.ndarray
    ) -> numpy.ndarray:

    forward_vector = target_position - eye_position
    forward_length = numpy.linalg.norm(forward_vector)

    normalized_forward = (
        forward_vector / forward_length
        if forward_length != 0.0
        else numpy.array([0.0, 0.0, 1.0], dtype = numpy.float32)
    )

    side_vector = numpy.cross(normalized_forward, up_vector)
    side_length = numpy.linalg.norm(side_vector)

    normalized_side = (
        side_vector / side_length
        if side_length != 0.0
        else numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)
    )

    orthogonal_up = numpy.cross(normalized_side, normalized_forward)

    result_matrix         = numpy.identity(4, dtype = numpy.float32)
    result_matrix[0, 0:3] = normalized_side
    result_matrix[1, 0:3] = orthogonal_up
    result_matrix[2, 0:3] = -normalized_forward
    result_matrix[0, 3]   = -numpy.dot(normalized_side, eye_position)
    result_matrix[1, 3]   = -numpy.dot(orthogonal_up, eye_position)
    result_matrix[2, 3]   = numpy.dot(normalized_forward, eye_position)

    return numpy.ascontiguousarray(result_matrix.T)

# Mesh Builders

def generate_painting_vertex_buffer(picture_index: int) -> numpy.ndarray:
    vertex_data = []
    width_half  = 0.44
    height_half = 0.56
    depth_half  = 0.05

    normal_vector  = numpy.array([0.0, 0.0, 1.0], dtype = numpy.float32)
    tangent_vector = numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)
    up_vector      = numpy.array([0.0, 1.0, 0.0], dtype = numpy.float32)

    def append_quad(
            vertex_one:     numpy.ndarray,
            vertex_two:     numpy.ndarray,
            vertex_three:   numpy.ndarray,
            vertex_four:    numpy.ndarray,
            normal_vector:  numpy.ndarray,
            wall_type:      float
        ) -> None:

        for vertex, texture_coordinates in [
            (vertex_one, (0.0, 1.0)),
            (vertex_two, (1.0, 1.0)),
            (vertex_three, (1.0, 0.0)),
            (vertex_one, (0.0, 1.0)),
            (vertex_three, (1.0, 0.0)),
            (vertex_four, (0.0, 0.0))
        ]:
            vertex_data.extend([*vertex, *normal_vector, *texture_coordinates, wall_type])

    canvas_center = numpy.array([0.0, 0.0, 0.038], dtype = numpy.float32)
    point_one     = canvas_center - tangent_vector * (width_half * 0.84) - up_vector * (height_half * 0.84)
    point_two     = canvas_center + tangent_vector * (width_half * 0.84) - up_vector * (height_half * 0.84)
    point_three   = canvas_center + tangent_vector * (width_half * 0.84) + up_vector * (height_half * 0.84)
    point_four    = canvas_center - tangent_vector * (width_half * 0.84) + up_vector * (height_half * 0.84)

    append_quad(point_one, point_two, point_three, point_four, normal_vector, 100.0 + picture_index)

    border_size = 0.05

    def append_frame_box(
            center_point: numpy.ndarray,
            half_tangent: float,
            half_up:      float,
            half_normal:  float
        ) -> None:

        corner_points = []

        for sign_x in [-1.0, 1.0]:
            for sign_y in [-1.0, 1.0]:
                for sign_z in [-1.0, 1.0]:
                    corner_points.append(
                        center_point +
                        tangent_vector * (half_tangent * sign_x) +
                        up_vector * (half_up * sign_y)           +
                        normal_vector * (half_normal * sign_z)
                    )

        append_quad(corner_points[4], corner_points[5], corner_points[7], corner_points[6], normal_vector, 6.0)
        append_quad(corner_points[0], corner_points[4], corner_points[6], corner_points[2], -tangent_vector, 6.0)
        append_quad(corner_points[5], corner_points[1], corner_points[3], corner_points[7], tangent_vector, 6.0)
        append_quad(corner_points[2], corner_points[6], corner_points[7], corner_points[3], up_vector, 6.0)
        append_quad(corner_points[0], corner_points[1], corner_points[5], corner_points[4], -up_vector, 6.0)

    middle_depth = depth_half * 0.5
    append_frame_box(normal_vector * middle_depth + up_vector * (height_half - border_size * 0.5), width_half, border_size * 0.5, middle_depth)
    append_frame_box(normal_vector * middle_depth - up_vector * (height_half - border_size * 0.5), width_half, border_size * 0.5, middle_depth)
    append_frame_box(normal_vector * middle_depth - tangent_vector * (width_half - border_size * 0.5), border_size * 0.5, height_half - border_size, middle_depth)
    append_frame_box(normal_vector * middle_depth + tangent_vector * (width_half - border_size * 0.5), border_size * 0.5, height_half - border_size, middle_depth)

    return numpy.array(vertex_data, dtype = numpy.float32)


def generate_stalker_monster_vertex_buffer() -> numpy.ndarray:
    vertex_data = []

    def append_triangle(
            point_one:     numpy.ndarray,
            point_two:     numpy.ndarray,
            point_three:   numpy.ndarray,
            material_type: float = 0.0
        ) -> None:

        vertex_a = numpy.array(point_one, dtype = numpy.float32)
        vertex_b = numpy.array(point_two, dtype = numpy.float32)
        vertex_c = numpy.array(point_three, dtype = numpy.float32)

        normal_vector = numpy.cross(vertex_b - vertex_a, vertex_c - vertex_a)
        length_value  = numpy.linalg.norm(normal_vector)
        normalized    = normal_vector / length_value if length_value > 1e-6 else numpy.array([0.0, 1.0, 0.0], dtype = numpy.float32)

        for vertex in [vertex_a, vertex_b, vertex_c]:
            vertex_data.extend([*vertex, *normalized, material_type])

    def append_tube_section(
            point_start:   numpy.ndarray,
            point_end:     numpy.ndarray,
            radius_start:  float,
            radius_end:    float,
            segment_steps: int   = 8,
            material_type: float = 0.0
        ) -> None:

        start_vector = numpy.array(point_start, dtype = numpy.float32)
        end_vector   = numpy.array(point_end,   dtype = numpy.float32)

        direction_axis = end_vector - start_vector
        distance_total = numpy.linalg.norm(direction_axis)

        if distance_total < 1e-6:
            return

        direction_axis /= distance_total

        reference_up = (
            numpy.array([0.0, 1.0, 0.0], dtype = numpy.float32)
            if abs(direction_axis[1]) < 0.9
            else numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)
        )

        orthogonal_side = numpy.cross(direction_axis, reference_up)
        orthogonal_side /= numpy.linalg.norm(orthogonal_side)
        perpendicular_up = numpy.cross(orthogonal_side, direction_axis)

        ring_start = []
        ring_end   = []

        for step in range(segment_steps):
            angle         = 2.0 * math.pi * step / segment_steps
            radial_offset = orthogonal_side * math.cos(angle) + perpendicular_up * math.sin(angle)
            ring_start.append(start_vector + radial_offset * radius_start)
            ring_end.append(end_vector     + radial_offset * radius_end)

        for step in range(segment_steps):
            next_step = (step + 1) % segment_steps
            append_triangle(ring_start[step], ring_end[step], ring_end[next_step], material_type)
            append_triangle(ring_start[step], ring_end[next_step], ring_start[next_step], material_type)

    spine_positions = [
        numpy.array([math.sin(elevation * 4.5) * 0.12 - 0.05, elevation, math.cos(elevation * 3.5) * 0.14 - 0.12])
        for elevation in numpy.linspace(0.4, 2.5, 20)
    ]

    for index in range(len(spine_positions) - 1):
        append_tube_section(spine_positions[index], spine_positions[index + 1], 0.075, 0.065, 8, 0.0)

    head_origin = spine_positions[-1]
    skull_peak  = head_origin + numpy.array([0.08, 0.38, 0.18])
    append_tube_section(head_origin, skull_peak, 0.07, 0.13, 8, 0.0)

    for lateral_side in [-1.0, 1.0]:
        shoulder_joint = head_origin + numpy.array([lateral_side * 0.28, -0.05, -0.05])
        elbow_joint    = shoulder_joint + numpy.array([lateral_side * 0.45, -0.85, 0.25])
        wrist_joint    = elbow_joint + numpy.array([lateral_side * 0.15, -0.95, -0.35])

        append_tube_section(shoulder_joint, elbow_joint, 0.055, 0.045, 6, 0.0)
        append_tube_section(elbow_joint, wrist_joint, 0.045, 0.032, 6, 0.0)

    return numpy.array(vertex_data, dtype = numpy.float32)