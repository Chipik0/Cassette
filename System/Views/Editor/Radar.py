from __future__ import annotations

import math
import numpy

from PyQt6.QtGui import (
    QPen,
    QFont,
    QBrush,
    QColor,
    QImage,
    QRegion,
    QPainter,
    QPolygon
)

from PyQt6.QtCore import (
    Qt,
    QPoint
)

from . import Constants

# Scanner Radar Generator

def render_radar_to_image(
        target_image:           QImage,
        camera_position:        numpy.ndarray,
        camera_yaw_degrees:     float,
        grid_matrix:            numpy.ndarray,
        cell_scale_units:       float,
        maze_dimension:         int,
        path_waypoints:         list[tuple[int, int]],
        current_waypoint_index: int,
        scenario_status_text:   str,
        is_glitch_scenario:     bool,
        bogus_waypoint:         numpy.ndarray,
        elapsed_time_seconds:   float,
        chase_counter:          int,
        sprite_active:          bool,
        sprite_position:        numpy.ndarray,
        monster_active:         bool,
        monster_position:       numpy.ndarray,
        finale_sequence_active: bool
    ) -> None:

    target_image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(target_image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(QPen(QColor(16, 20, 18), 4))
    painter.setBrush(QBrush(QColor(28, 34, 31)))
    painter.drawRoundedRect(16, 16, 224, 224, 18, 18)

    center_x      = 128
    center_y      = 120
    radius_pixels = 75

    painter.setPen(QPen(QColor(12, 38, 18), 3))
    painter.setBrush(QBrush(QColor(4, 18, 8, 245)))
    painter.drawEllipse(QPoint(center_x, center_y), radius_pixels, radius_pixels)

    radar_scale          = radius_pixels / Constants.RADAR_RANGE_METERS
    camera_x             = camera_position[0]
    camera_z             = camera_position[2]
    camera_yaw_radians   = math.radians(camera_yaw_degrees)

    def world_to_screen(world_x: float, world_z: float) -> tuple[float, float, float]:
        delta_x  = world_x - camera_x
        delta_z  = world_z - camera_z
        distance = math.hypot(delta_x, delta_z)
        angle    = math.atan2(delta_z, delta_x) - camera_yaw_radians
        screen_x = center_x + distance * radar_scale * math.sin(angle)
        screen_y = center_y - distance * radar_scale * math.cos(angle)
        return screen_x, screen_y, distance

    painter.setClipRegion(
        QRegion(
            center_x - radius_pixels,
            center_y - radius_pixels,
            radius_pixels * 2,
            radius_pixels * 2,
            QRegion.RegionType.Ellipse
        )
    )

    painter.setPen(QPen(QColor(20, 110, 40, 180), 1))
    painter.setBrush(QBrush(QColor(8, 48, 18, 200)))

    current_grid_x   = int(camera_x / cell_scale_units)
    current_grid_z   = int(camera_z / cell_scale_units)
    scan_tile_radius = int(Constants.RADAR_RANGE_METERS / cell_scale_units) + 1

    for grid_x in range(max(0, current_grid_x - scan_tile_radius), min(maze_dimension, current_grid_x + scan_tile_radius + 1)):
        for grid_z in range(max(0, current_grid_z - scan_tile_radius), min(maze_dimension, current_grid_z + scan_tile_radius + 1)):
            if grid_matrix[grid_x, grid_z] != 0:
                continue

            point_one   = world_to_screen(grid_x * cell_scale_units, grid_z * cell_scale_units)
            point_two   = world_to_screen((grid_x + 1) * cell_scale_units, grid_z * cell_scale_units)
            point_three = world_to_screen((grid_x + 1) * cell_scale_units, (grid_z + 1) * cell_scale_units)
            point_four  = world_to_screen(grid_x * cell_scale_units, (grid_z + 1) * cell_scale_units)

            cell_polygon = QPolygon([
                QPoint(int(point_one[0]),   int(point_one[1])),
                QPoint(int(point_two[0]),   int(point_two[1])),
                QPoint(int(point_three[0]), int(point_three[1])),
                QPoint(int(point_four[0]),  int(point_four[1]))
            ])
            painter.drawPolygon(cell_polygon)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(30, 140, 50, 90), 1, Qt.PenStyle.DashLine))
    painter.drawEllipse(QPoint(center_x, center_y), int(radius_pixels * 0.33), int(radius_pixels * 0.33))
    painter.drawEllipse(QPoint(center_x, center_y), int(radius_pixels * 0.66), int(radius_pixels * 0.66))

    if not finale_sequence_active and path_waypoints and scenario_status_text != Constants.FATE_TEXTS["burnout_no_exit"]:
        screen_points = [QPoint(center_x, center_y)]

        if is_glitch_scenario:
            painter.setPen(QPen(QColor(255, 140, 30, 220), 2, Qt.PenStyle.DashDotLine))
            bogus_screen_x, bogus_screen_y, _ = world_to_screen(bogus_waypoint[0], bogus_waypoint[1])
            jitter_x = (center_x + bogus_screen_x) * 0.5 + math.sin(elapsed_time_seconds * 14.0) * 18.0
            jitter_y = (center_y + bogus_screen_y) * 0.5 + math.cos(elapsed_time_seconds * 12.0) * 18.0
            screen_points.append(QPoint(int(jitter_x), int(jitter_y)))
            screen_points.append(QPoint(int(bogus_screen_x), int(bogus_screen_y)))
            target_render_x = bogus_screen_x
            target_render_y = bogus_screen_y

        else:
            painter.setPen(QPen(QColor(40, 255, 130, 235), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

            for point_index in range(current_waypoint_index, min(len(path_waypoints), current_waypoint_index + 8)):
                grid_node = path_waypoints[point_index]
                screen_point_x, screen_point_y, _ = world_to_screen((grid_node[0] + 0.5) * cell_scale_units, (grid_node[1] + 0.5) * cell_scale_units)
                screen_points.append(QPoint(int(screen_point_x), int(screen_point_y)))

            target_node     = path_waypoints[min(len(path_waypoints) - 1, current_waypoint_index + 3)]
            target_render_x, target_render_y, _ = world_to_screen((target_node[0] + 0.5) * cell_scale_units, (target_node[1] + 0.5) * cell_scale_units)

        if len(screen_points) > 1:
            painter.drawPolyline(screen_points)

        pulse_radius = 5.0 + 2.5 * math.sin(elapsed_time_seconds * 8.0)

        if is_glitch_scenario:
            painter.setPen(QPen(QColor(255, 170, 50, 240), 2))
            painter.setBrush(QBrush(QColor(255, 100, 20, 140)))

        else:
            painter.setPen(QPen(QColor(100, 255, 160, 240), 2))
            painter.setBrush(QBrush(QColor(50, 255, 100, 100)))

        painter.drawEllipse(QPoint(int(target_render_x), int(target_render_y)), int(pulse_radius), int(pulse_radius))

    painter.setPen(QPen(QColor(0, 0, 0), 1))
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    player_cursor = QPolygon([
        QPoint(center_x, center_y - 8),
        QPoint(center_x + 4, center_y + 5),
        QPoint(center_x, center_y + 2),
        QPoint(center_x - 4, center_y + 5)
    ])
    painter.drawPolygon(player_cursor)

    if sprite_active:
        sprite_screen_x, sprite_screen_y, sprite_distance = world_to_screen(sprite_position[0], sprite_position[2])

        if sprite_distance <= Constants.RADAR_RANGE_METERS:
            painter.setPen(QPen(QColor(255, 220, 50, 220), 1))
            painter.setBrush(QBrush(QColor(255, 240, 100, 240)))
            painter.drawEllipse(QPoint(int(sprite_screen_x), int(sprite_screen_y)), 5, 5)

    if monster_active:
        monster_screen_x, monster_screen_y, monster_distance = world_to_screen(monster_position[0], monster_position[2])

        if monster_distance <= Constants.RADAR_RANGE_METERS:
            painter.setPen(QPen(QColor(255, 30, 30, 160), 1))
            painter.setBrush(QBrush(QColor(255, 15, 15, 245)))
            painter.drawEllipse(QPoint(int(monster_screen_x), int(monster_screen_y)), 6, 6)

    painter.setClipping(False)
    painter.setFont(QFont("Monospace", 6, QFont.Weight.Bold))

    if scenario_status_text == Constants.FATE_TEXTS["burnout_no_exit"]:
        painter.setPen(QColor(255, 80, 80))

    elif is_glitch_scenario:
        painter.setPen(QColor(255, 150, 40))

    else:
        painter.setPen(QColor(50, 240, 90))

    painter.drawText(24, 218, scenario_status_text)
    painter.end()