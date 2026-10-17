from __future__ import annotations

import os
import math
import time
import numpy
import random
from collections import deque
from dataclasses import dataclass

from OpenGL import GL
from OpenGL.GL import shaders

from PyQt6.QtGui import (
    QPen,
    QFont,
    QBrush,
    QColor,
    QImage,
    QImageReader,
    QCursor,
    QPainter,
    QShowEvent,
    QKeyEvent,
    QMouseEvent
)

from PyQt6.QtCore import (
    Qt,
    QPoint,
    QSize,
    QTimer,
    QElapsedTimer
)

from PyQt6.QtWidgets import (
    QWidget,
    QApplication
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from System.Common import Constants as ApplicationConstants
from System.Services import Player
from System.Interface import Timing
from System.Interface.Animation import LoomEngine

from . import (
    Fates,
    Radar,
    Effects,
    Shaders,
    Geometry,
    Constants,
    WorldBuilder
)

from .GLMesh import GLMesh
from .WallRenderer import WallRenderer
from .ItemRenderer import ItemRenderer
from .LampRenderer import LampRenderer

SCARY_SOUND_PLAYED_IN_SESSION = False

# Runtime Hum State

@dataclass
class RuntimeLampHum:
    sound:  Player.UISound
    volume: float = 0.0
    pan:    float = 0.0

# Audit Simulation Widget

class AuditSimulationWidget(QOpenGLWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.cell_scale_units:         float = Constants.CELL_SCALE_UNITS
        self.maze_dimension:           int   = Constants.MAZE_DIMENSION
        self.wall_height_units:        float = Constants.WALL_HEIGHT_UNITS
        self.intro_timer_seconds:      float = 2.5
        self.intro_active:             bool  = True
        self.simulation_terminated:    bool  = False

        self.camera_position:          numpy.ndarray = numpy.array([5.0, 1.4, 5.0], dtype = numpy.float32)
        self.velocity_vector:          numpy.ndarray = numpy.zeros(3, dtype = numpy.float32)
        self.camera_front:             numpy.ndarray = numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)
        self.camera_up:                numpy.ndarray = numpy.array([0.0, 1.0, 0.0], dtype = numpy.float32)

        self.flashlight_position:      numpy.ndarray = numpy.array([5.0, 1.4, 5.0], dtype = numpy.float32)
        self.flashlight_front:         numpy.ndarray = numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)
        self.flashlight_bobbing_phase: float         = 0.0
        self.flashlight_idle_phase:    float         = 0.0

        self.yaw_degrees:            float         = 0.0
        self.pitch_degrees:          float         = -10.0
        self.target_yaw_degrees:     float         = 0.0
        self.target_pitch_degrees:   float         = -10.0
        self.camera_turn_vector:     numpy.ndarray = numpy.zeros(2, dtype = numpy.float32)
        self.camera_turn_blur:       float         = 0.0
        self.roll_degrees:           float         = 0.0
        self.walk_cycle_phase:       float         = 0.0
        self.camera_bobbing_x:       float         = 0.0
        self.camera_bobbing_y:       float         = 0.0
        self.field_of_view_offset:   float         = 0.0

        self.first_mouse_movement:   bool          = True
        self.mouse_cursor_locked:    bool          = True
        self.pressed_key_codes:      set           = set()
        self.elapsed_time_seconds:   float         = 0.0
        self.scary_sound_timer_seconds: float      = random.uniform(*Constants.SCARY_SOUND_DELAY_SECONDS)

        random_scenario_name:        str                = random.choice(list(Fates.AVAILABLE_FATE_REGISTRY.keys()))
        self.run_fate_scenario:      str                = random_scenario_name
        self.active_scenario:        Fates.FateScenario = Fates.create_fate_scenario(random_scenario_name)
        self.gravity_tilt:           float              = 0.0

        self.device_picked_up:       bool          = False
        self.device_world_position:  numpy.ndarray = numpy.zeros(3, dtype = numpy.float32)
        self.current_waypoint_index: int           = 0
        self.radar_refresh_timer:    float         = 0.0
        self.scanner_texture_dirty:  bool          = False
        self.scanner_qimage:         QImage        = QImage(
            Constants.RADAR_SCANNER_TEXTURE_SIZE,
            Constants.RADAR_SCANNER_TEXTURE_SIZE,
            QImage.Format.Format_RGBA8888
        )

        self.bogus_waypoint_position:      numpy.ndarray = numpy.zeros(2, dtype = numpy.float32)
        self.radar_chase_count:            int           = 0
        self.white_noise_proximity_glitch: float         = 0.0

        self.madness_ratio:          float = 0.0
        self.reality_tear_ratio:     float = 0.0
        self.finale_sequence_active: bool  = False
        self.finale_timer_seconds:   float = 0.0
        self.cut_to_black_factor:    float = 0.0

        self.lobotomy_intensity:     float = 0.0
        self.heavy_eyelids_factor:   float = 0.0
        self.white_bloom_factor:     float = 0.0
        self.cold_desaturation:      float = 0.0

        self.lamp_hum_sounds:        dict[int, RuntimeLampHum] = {}

        self.emergency_red_intensity:    float         = 0.0
        self.corridor_entrance_position: numpy.ndarray = numpy.zeros(3, dtype = numpy.float32)
        self.corridor_end_position:      numpy.ndarray = numpy.zeros(3, dtype = numpy.float32)

        self.sprite_entity_active:   bool          = False
        self.sprite_entity_position: numpy.ndarray = numpy.array([0.0, -100.0, 0.0], dtype = numpy.float32)
        self.chipsa_following_state: bool          = False
        self.chipsa_follow_timer:    float         = 30.0
        self.chipsa_path_waypoints:  list          = []
        self.chipsa_repath_timer:    float         = 0.0
        self.chipsa_already_spawned: bool          = False

        self.monster_entity_position: numpy.ndarray = numpy.array([0.0, -100.0, 0.0], dtype = numpy.float32)
        self.monster_entity_active:   bool          = False
        self.monster_movement_speed:  float         = Constants.MONSTER_MOVE_SPEED
        self.monster_path_waypoints:  list          = []
        self.monster_repath_timer:    float         = 0.0
        self.jumpscare_blood_factor:  float         = 0.0
        self.heartbeat_timer_seconds: float         = 0.0

        self.light_flicker_ratio:    float = 1.0

        self.scene_uniform_locations:   dict[str, int] = {}
        self.monster_uniform_locations: dict[str, int] = {}
        self.hud_uniform_locations:     dict[str, int] = {}
        self.vhs_uniform_locations:     dict[str, int] = {}

        self.wall_renderer:   WallRenderer                 = WallRenderer()
        self.item_renderer:   ItemRenderer                 = ItemRenderer()
        self.lamp_renderer:   LampRenderer                 = LampRenderer()
        self.anomaly_manager: Effects.AnomalyEventManager  = Effects.AnomalyEventManager()

        self.framebuffer_object_id:      int | None = None
        self.screen_texture_id:          int | None = None
        self.renderbuffer_depth_id:      int | None = None
        self.identity_matrix_4:          numpy.ndarray = numpy.identity(4, dtype = numpy.float32)
        self.projection_matrix_cache_key: tuple[float, float, float, float] | None = None
        self.projection_matrix_cache:     numpy.ndarray | None = None
        self.view_matrix_cache_key:       tuple[float, ...] | None = None
        self.view_matrix_cache:           numpy.ndarray | None = None

        self.render_profiler_enabled: bool = os.environ.get("CASSSETTE_EDITOR_PROFILE", "0").lower() in {"1", "true", "yes", "on"}
        self.render_profile_samples: deque[dict[str, float]] = deque(maxlen = 60)
        self.render_profile_current: dict[str, float] = {}
        self.render_profile_frame_index: int = 0
        self.render_profile_previous_frame_start: float | None = None
        self.gpu_profile_query_ids: dict[str, list[int]] = {}
        self.gpu_profile_pending_queries: deque[tuple[str, int]] = deque()
        self.gpu_profile_active_query: tuple[str, int] | None = None

        self.decal_atlas_texture_id:      int | None = None
        self.scanner_display_texture_id:  int | None = None
        self.paintings_atlas_texture_id:  int | None = None
        self.memory_atlas_texture_id:     int | None = None
        self.television_atlas_texture_id: int | None = None
        self.procedural_noise_texture_id: int | None = None
        self.available_paintings_count:   int        = 0

        self.fullscreen_quad_mesh: GLMesh | None = None
        self.hud_quad_mesh:        GLMesh | None = None

        self.world_grid_array:     numpy.ndarray         = numpy.ones((self.maze_dimension, self.maze_dimension), dtype = int)
        self.solution_path_points: list[tuple[int, int]] = []
        self.lamp_world_positions: list[tuple[float, float]] = []

        self.frame_stopwatch: QElapsedTimer = QElapsedTimer()
        self.frame_stopwatch.start()

        self.setup_animation_handles()
        self.construct_world_layout()

        self.simulation_timer = Timing.Timer(
            interval    = Constants.FPS_120,
            callback    = self.process_game_loop_tick,
            parent      = self,
            fps_managed = True
        )

        Player.ui_player.play_sound(
            name                   = ".vault/Anomaly/Load",
            enable_tone_randomizer = False
        )

        self.simulation_timer.start()

    # Animation Handles

    def setup_animation_handles(self) -> None:
        self.glitch_intensity_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "simulation_glitch_intensity",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE
        )

        self.eyelids_closure_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "simulation_eyelids_closure",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE
        )

        self.camera_fov_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "simulation_camera_fov_vertigo",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE
        )

    # World Layout

    def construct_world_layout(self) -> None:
        dimension  = self.maze_dimension
        scale_unit = self.cell_scale_units

        self.world_grid_array = numpy.ones((dimension, dimension), dtype = int)

        if self.run_fate_scenario == "BURNOUT":
            self.active_scenario.setup_world(self)
            return

        for room_index in range(random.randint(7, 12)):
            room_width  = random.randint(3, 6)
            room_height = random.randint(3, 6)
            origin_x    = random.randint(2, dimension - room_width - 3)
            origin_z    = random.randint(2, dimension - room_height - 3)
            self.world_grid_array[origin_x:origin_x + room_width, origin_z:origin_z + room_height] = 0

        def carve_corridors_recursive(current_x: int, current_z: int) -> None:
            directions = [(0, 2), (0, -2), (2, 0), (-2, 0)]
            random.shuffle(directions)

            for step_x, step_z in directions:
                target_x = current_x + step_x
                target_z = current_z + step_z

                if 2 <= target_x < dimension - 2 and 2 <= target_z < dimension - 2:
                    if self.world_grid_array[target_x, target_z] == 1:
                        self.world_grid_array[current_x + step_x // 2, current_z + step_z // 2] = 0
                        self.world_grid_array[target_x, target_z] = 0
                        carve_corridors_recursive(target_x, target_z)

        for spawn_x in range(3, dimension - 3, 6):
            for spawn_z in range(3, dimension - 3, 6):
                if self.world_grid_array[spawn_x, spawn_z] == 1:
                    self.world_grid_array[spawn_x, spawn_z] = 0
                    carve_corridors_recursive(spawn_x, spawn_z)

        start_coordinate = (3, 3)
        self.world_grid_array[2:5, 2:5] = 0
        self.camera_position = numpy.array([(start_coordinate[0] + 0.5) * scale_unit, 1.4, (start_coordinate[1] + 0.5) * scale_unit], dtype = numpy.float32)

        frontier_queue = deque([start_coordinate])
        visited_nodes  = {start_coordinate: None}
        farthest_node  = start_coordinate

        while frontier_queue:
            node          = frontier_queue.popleft()
            farthest_node = node

            for step_x, step_z in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor_x = node[0] + step_x
                neighbor_z = node[1] + step_z

                if 1 <= neighbor_x < dimension - 1 and 1 <= neighbor_z < dimension - 1:
                    if self.world_grid_array[neighbor_x, neighbor_z] == 0 and (neighbor_x, neighbor_z) not in visited_nodes:
                        visited_nodes[(neighbor_x, neighbor_z)] = node
                        frontier_queue.append((neighbor_x, neighbor_z))

        extracted_path  = []
        crawler_pointer = farthest_node

        while crawler_pointer is not None:
            extracted_path.append(crawler_pointer)
            crawler_pointer = visited_nodes[crawler_pointer]

        extracted_path.reverse()
        self.solution_path_points = extracted_path

        self.yaw_degrees          = 0.0
        self.target_yaw_degrees   = 0.0
        self.pitch_degrees        = -10.0
        self.target_pitch_degrees = -10.0

        self.device_world_position = numpy.array([
            (start_coordinate[0] + 1.2) * scale_unit,
            0.18,
            (start_coordinate[1] + 0.5) * scale_unit
        ], dtype = numpy.float32)

        terminal_point = self.solution_path_points[-1]
        entrance_point = self.solution_path_points[max(0, len(self.solution_path_points) - 9)]

        self.corridor_entrance_position = numpy.array([(entrance_point[0] + 0.5) * scale_unit, 0.0, (entrance_point[1] + 0.5) * scale_unit], dtype = numpy.float32)
        self.corridor_end_position      = numpy.array([(terminal_point[0] + 0.5) * scale_unit, 1.4, (terminal_point[1] + 0.5) * scale_unit], dtype = numpy.float32)

        self.active_scenario.setup_world(self)

        self.lamp_world_positions = []

        for index in range(0, len(self.solution_path_points), 3):
            path_x, path_z = self.solution_path_points[index]
            self.lamp_world_positions.append(((path_x + 0.5) * scale_unit, (path_z + 0.5) * scale_unit))

    def choose_random_floor_coordinate(self, minimum_distance_from_player: float = 8.0) -> tuple[float, float]:
        scale_unit          = self.cell_scale_units
        dimension           = self.maze_dimension
        candidate_positions = []

        for tile_x in range(2, dimension - 2):
            for tile_z in range(2, dimension - 2):
                if self.world_grid_array[tile_x, tile_z] != 0:
                    continue

                world_x  = (tile_x + 0.5) * scale_unit
                world_z  = (tile_z + 0.5) * scale_unit
                distance = math.hypot(world_x - self.camera_position[0], world_z - self.camera_position[2])

                if distance >= minimum_distance_from_player:
                    candidate_positions.append((world_x, world_z))

        if candidate_positions:
            return random.choice(candidate_positions)

        return ((dimension // 2) * scale_unit, (dimension // 2) * scale_unit)

    # Navigation Helpers

    def spawn_chipsa_behind_player(self) -> None:
        if self.chipsa_already_spawned:
            return

        self.chipsa_already_spawned = True
        forward_vector              = numpy.array([self.camera_front[0], 0.0, self.camera_front[2]], dtype = numpy.float32)
        normalized_length           = numpy.linalg.norm(forward_vector)

        if normalized_length > 1e-4:
            forward_vector /= normalized_length

        else:
            forward_vector = numpy.array([1.0, 0.0, 0.0], dtype = numpy.float32)

        rear_direction  = -forward_vector
        right_direction = numpy.array([-forward_vector[2], 0.0, forward_vector[0]], dtype = numpy.float32)

        resolved_position = None
        angle_offsets     = [0.0, 15.0, -15.0, 30.0, -30.0, 45.0, -45.0, 60.0, -60.0]
        distances         = [3.8, 3.2, 2.7, 2.2, 1.8]

        for distance in distances:
            for angle in angle_offsets:
                radians             = math.radians(angle)
                candidate_direction = rear_direction * math.cos(radians) + right_direction * math.sin(radians)
                candidate_position  = self.camera_position + candidate_direction * distance
                candidate_position[1] = 0.0

                if WorldBuilder.check_tile_collision(candidate_position[0], candidate_position[2], 0.42, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    continue

                if not WorldBuilder.test_line_of_sight(self.camera_position, candidate_position, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    continue

                resolved_position = candidate_position
                break

            if resolved_position is not None:
                break

        if resolved_position is None:
            resolved_position    = self.camera_position - forward_vector * 2.0
            resolved_position[1] = 0.0

        self.sprite_entity_position = numpy.copy(resolved_position)
        self.sprite_entity_active   = True
        self.chipsa_following_state = True
        self.display_message(Constants.EDITOR_UI_TEXTS["sprite_hello"])

    def step_entity_navigation(
            self,
            current_position:   numpy.ndarray,
            path_waypoints:     list[tuple[int, int]],
            speed:              float,
            delta_time_seconds: float,
            radius:             float = 0.28,
            is_monster:         bool  = False
        ) -> numpy.ndarray:

        if is_monster:
            direction_to_player    = self.camera_position - current_position
            direction_to_player[1] = 0.0
            distance_to_player     = numpy.linalg.norm(direction_to_player)

            if distance_to_player > 0.05 and WorldBuilder.test_line_of_sight(current_position, self.camera_position, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                normalized_direction = direction_to_player / distance_to_player
                step_vector          = normalized_direction * speed * delta_time_seconds

                next_position_x = current_position[0] + step_vector[0]
                next_position_z = current_position[2] + step_vector[2]

                if not WorldBuilder.check_tile_collision(next_position_x, current_position[2], radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    current_position[0] = next_position_x

                if not WorldBuilder.check_tile_collision(current_position[0], next_position_z, radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    current_position[2] = next_position_z

                return current_position

        if not path_waypoints:
            return current_position

        scale_unit = self.cell_scale_units

        while len(path_waypoints) > 1:
            target_node  = path_waypoints[0]
            target_world = numpy.array([(target_node[0] + 0.5) * scale_unit, current_position[1], (target_node[1] + 0.5) * scale_unit], dtype = numpy.float32)
            distance     = math.hypot(target_world[0] - current_position[0], target_world[2] - current_position[2])

            if distance < 0.6:
                path_waypoints.pop(0)

            else:
                break

        target_node  = path_waypoints[0]
        target_world = numpy.array([(target_node[0] + 0.5) * scale_unit, current_position[1], (target_node[1] + 0.5) * scale_unit], dtype = numpy.float32)

        offset_difference    = target_world - current_position
        offset_difference[1] = 0.0
        distance             = numpy.linalg.norm(offset_difference)

        if distance > 1e-4:
            movement_direction = offset_difference / distance
            step_vector        = movement_direction * speed * delta_time_seconds

            next_position_x = current_position[0] + step_vector[0]
            next_position_z = current_position[2] + step_vector[2]

            if not WorldBuilder.check_tile_collision(next_position_x, next_position_z, radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                current_position[0] = next_position_x
                current_position[2] = next_position_z

            else:
                if not WorldBuilder.check_tile_collision(next_position_x, current_position[2], radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    current_position[0] = next_position_x

                if not WorldBuilder.check_tile_collision(current_position[0], next_position_z, radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
                    current_position[2] = next_position_z

        return current_position

    # Texture Atlases

    def create_broadcast_atlas_texture(self) -> int:
        atlas_dimension = Constants.TV_ATLAS_SIZE
        tile_dimension  = Constants.TV_CHANNEL_SIZE

        atlas_image = QImage(atlas_dimension, atlas_dimension, QImage.Format.Format_RGBA8888)
        atlas_image.fill(QColor(*Constants.TV_ATLAS_BACKGROUND_COLOR))

        painter = QPainter(atlas_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for channel_index, (title_text, subtitle_template) in enumerate(Constants.TV_BROADCAST_PROGRAMS):
            column   = channel_index % Constants.TV_ATLAS_COLUMNS
            row      = channel_index // Constants.TV_ATLAS_COLUMNS
            origin_x = column * tile_dimension
            origin_y = row * tile_dimension

            painter.save()
            painter.translate(origin_x, origin_y)

            painter.setBrush(QBrush(QColor(*Constants.TV_CHANNEL_BACKGROUND_COLOR)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, 0, tile_dimension, tile_dimension)

            if channel_index in Constants.TV_FACE_CHANNELS:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(210, 215, 205, 230)))
                painter.drawEllipse(78, 45, 100, 140)

                painter.setBrush(QBrush(QColor(0, 0, 0)))
                painter.drawEllipse(95, 85, 26, 36)
                painter.drawEllipse(135, 85, 26, 36)

                painter.setPen(QPen(QColor(0, 0, 0), 4))
                painter.drawArc(100, 135, 56, 35, 0, -180 * 16)

            elif channel_index in Constants.TV_EYE_CHANNELS:
                painter.setPen(QPen(QColor(180, 25, 25), 3))
                painter.setBrush(QBrush(QColor(20, 0, 0)))
                painter.drawEllipse(48, 68, 160, 100)

                painter.setBrush(QBrush(QColor(215, 220, 210)))
                painter.drawEllipse(98, 88, 60, 60)

                painter.setBrush(QBrush(QColor(0, 0, 0)))
                painter.drawEllipse(116, 106, 24, 24)

            elif channel_index in Constants.TV_COLOR_BAR_CHANNELS:
                bar_width = tile_dimension // len(Constants.TV_COLOR_BARS)

                for bar_index, bar_color in enumerate(Constants.TV_COLOR_BARS):
                    painter.setBrush(QBrush(QColor(*bar_color)))
                    painter.drawRect(bar_index * bar_width, 0, bar_width, 140)

            subtitle_text = subtitle_template.format(user_name = Constants.USER_NAME)

            painter.setBrush(QBrush(QColor(*Constants.TV_HEADER_BACKGROUND_COLOR)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(8, 12, tile_dimension - 16, 24)

            painter.setFont(QFont("Impact", 11))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(10, 14, tile_dimension - 20, 20, int(Qt.AlignmentFlag.AlignCenter), title_text)

            painter.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            painter.setPen(QColor(220, 225, 215))
            painter.drawText(12, 175, tile_dimension - 24, 75, int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap), subtitle_text)

            painter.restore()

        painter.end()

        raw_bits = atlas_image.constBits()
        raw_bits.setsize(atlas_image.sizeInBytes())

        texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, atlas_dimension, atlas_dimension, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(raw_bits))
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        return texture_id

    def create_paintings_atlas_texture(self) -> int:
        atlas_dimension = 2048
        tile_dimension  = 512

        atlas_image = QImage(atlas_dimension, atlas_dimension, QImage.Format.Format_RGBA8888)
        atlas_image.fill(QColor(0, 0, 0, 0))

        painter = QPainter(atlas_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        source_images_directory = "System/Assets/Image"
        supported_extensions = (".png", ".jpg", ".jpeg", ".webp")
        source_image_paths = []

        if os.path.exists(source_images_directory):
            for filename in sorted(os.listdir(source_images_directory)):
                if filename.lower().endswith(supported_extensions):
                    source_image_paths.append(os.path.join(source_images_directory, filename))

        self.available_paintings_count = 0

        for source_image_path in source_image_paths:
            if self.available_paintings_count >= 16:
                break

            image_reader = QImageReader(source_image_path)
            source_size = image_reader.size()
            maximum_source_dimension = tile_dimension * 2

            if source_size.width() > maximum_source_dimension or source_size.height() > maximum_source_dimension:
                scale_factor = maximum_source_dimension / max(source_size.width(), source_size.height())
                image_reader.setScaledSize(QSize(
                    max(1, round(source_size.width() * scale_factor)),
                    max(1, round(source_size.height() * scale_factor))
                ))

            source_frame = image_reader.read()

            if source_frame.isNull():
                continue

            scaled_frame = source_frame.scaled(
                tile_dimension,
                tile_dimension,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            cropped_x = (scaled_frame.width() - tile_dimension) // 2
            cropped_y = (scaled_frame.height() - tile_dimension) // 2
            cropped_frame = scaled_frame.copy(cropped_x, cropped_y, tile_dimension, tile_dimension)

            index = self.available_paintings_count
            painter.drawImage((index % 4) * tile_dimension, (index // 4) * tile_dimension, cropped_frame)
            self.available_paintings_count += 1

        if self.available_paintings_count == 0:
            for fallback_index in range(16):
                placeholder_image = QImage(tile_dimension, tile_dimension, QImage.Format.Format_ARGB32)
                placeholder_image.fill(QColor(35, 26, 20))
                placeholder_painter = QPainter(placeholder_image)
                placeholder_painter.setPen(QColor(180, 140, 80))
                placeholder_painter.setFont(QFont("Times New Roman", 22, QFont.Weight.Bold))
                placeholder_painter.drawText(
                    20,
                    180,
                    tile_dimension - 40,
                    80,
                    int(Qt.AlignmentFlag.AlignCenter),
                    Constants.EDITOR_UI_TEXTS["archive_placeholder"].format(index = fallback_index + 1)
                )
                placeholder_painter.end()
                painter.drawImage((fallback_index % 4) * tile_dimension, (fallback_index // 4) * tile_dimension, placeholder_image)

            self.available_paintings_count = 16

        painter.end()

        raw_bits = atlas_image.constBits()
        raw_bits.setsize(atlas_image.sizeInBytes())

        texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, atlas_dimension, atlas_dimension, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(raw_bits))
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        return texture_id

    def create_memory_atlas_texture(self) -> int:
        atlas_dimension = 1024
        tile_dimension  = 256

        atlas_image = QImage(atlas_dimension, atlas_dimension, QImage.Format.Format_RGBA8888)
        atlas_image.fill(QColor(0, 0, 0, 0))

        painter = QPainter(atlas_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        extracted_code_lines = Constants.FALLBACK_SOURCE_CODE_LINES
        color_palette        = [
            QColor(196, 178, 130, 230),
            QColor(156, 163, 125, 220),
            QColor(184, 144, 99, 225),
            QColor(168, 130, 110, 215)
        ]

        for index in range(16):
            column   = index % 4
            row      = index // 4
            origin_x = column * tile_dimension
            origin_y = row * tile_dimension

            for line_index in range(random.randint(6, 10)):
                text_line = random.choice(extracted_code_lines)
                painter.setFont(QFont("Monospace", random.randint(8, 12), QFont.Weight.Bold))
                painter.save()
                position_x = origin_x + random.uniform(15, tile_dimension - 60)
                position_y = origin_y + random.uniform(25, tile_dimension - 25)

                painter.translate(position_x, position_y)
                painter.rotate(random.uniform(-25.0, 25.0))
                painter.setPen(random.choice(color_palette))
                painter.drawText(0, 0, text_line)
                painter.restore()

        painter.end()

        raw_bits = atlas_image.constBits()
        raw_bits.setsize(atlas_image.sizeInBytes())

        texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, atlas_dimension, atlas_dimension, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(raw_bits))
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        return texture_id

    def create_decal_atlas_texture(self) -> int:
        atlas_dimension = 1024
        tile_dimension  = 256

        atlas_image = QImage(atlas_dimension, atlas_dimension, QImage.Format.Format_RGBA8888)
        atlas_image.fill(QColor(0, 0, 0, 0))

        painter = QPainter(atlas_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        text_font = QFont("Impact", 20)
        text_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(text_font)

        for index, text in enumerate(Constants.WALL_DECAL_TEXT_COLLECTION):
            row      = index // 4
            column   = index % 4
            origin_x = column * tile_dimension
            origin_y = row * tile_dimension

            painter.save()
            painter.translate(origin_x + 128, origin_y + 128)
            painter.rotate(random.uniform(-4.0, 4.0))
            painter.setPen(QPen(QColor(185, 10, 10, 250), 7))
            painter.drawText(-120, -60, 240, 120, int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap), text)
            painter.restore()

        painter.end()

        raw_bits = atlas_image.constBits()
        raw_bits.setsize(atlas_image.sizeInBytes())

        texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, atlas_dimension, atlas_dimension, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(raw_bits))
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        return texture_id

    def create_procedural_noise_texture(self) -> int:
        texture_size = 2048
        noise_axis   = (numpy.arange(texture_size, dtype = numpy.float32) + 0.5) / texture_size
        coordinate_x, coordinate_y = numpy.meshgrid(noise_axis, noise_axis)

        coordinate_offset = (
            coordinate_x * (coordinate_x + 45.32) +
            coordinate_y * (coordinate_y + 45.32)
        )

        fractional_x = numpy.mod(coordinate_x + coordinate_offset, 1.0)
        fractional_y = numpy.mod(coordinate_y + coordinate_offset, 1.0)
        noise_values = numpy.mod(fractional_x * fractional_y, 1.0).astype(numpy.float32)

        texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_R32F,
            texture_size,
            texture_size,
            0,
            GL.GL_RED,
            GL.GL_FLOAT,
            noise_values
        )
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)

        return texture_id

    # OpenGL Lifecycle

    def initializeGL(self) -> None:
        GL.glEnable(GL.GL_DEPTH_TEST)

        if self.render_profiler_enabled:
            self.gpu_profile_query_ids = {
                phase_name: [int(query_id) for query_id in numpy.asarray(GL.glGenQueries(4)).reshape(-1)]
                for phase_name in ("gpu_scene", "gpu_postprocess")
            }

        scene_vertex_shader       = shaders.compileShader(Shaders.SCENE_VERTEX_SHADER_SOURCE, GL.GL_VERTEX_SHADER)
        scene_fragment_shader     = shaders.compileShader(Shaders.SCENE_FRAGMENT_SHADER_SOURCE, GL.GL_FRAGMENT_SHADER)
        self.scene_shader_program = shaders.compileProgram(scene_vertex_shader, scene_fragment_shader)

        hud_vertex_shader       = shaders.compileShader(Shaders.HUD_VERTEX_SHADER_SOURCE, GL.GL_VERTEX_SHADER)
        hud_fragment_shader     = shaders.compileShader(Shaders.HUD_FRAGMENT_SHADER_SOURCE, GL.GL_FRAGMENT_SHADER)
        self.hud_shader_program = shaders.compileProgram(hud_vertex_shader, hud_fragment_shader)

        monster_vertex_shader       = shaders.compileShader(Shaders.MONSTER_VERTEX_SHADER_SOURCE, GL.GL_VERTEX_SHADER)
        monster_fragment_shader     = shaders.compileShader(Shaders.MONSTER_FRAGMENT_SHADER_SOURCE, GL.GL_FRAGMENT_SHADER)
        self.monster_shader_program = shaders.compileProgram(monster_vertex_shader, monster_fragment_shader)

        vhs_vertex_shader       = shaders.compileShader(Shaders.QUAD_VERTEX_SHADER_SOURCE, GL.GL_VERTEX_SHADER)
        vhs_fragment_shader     = shaders.compileShader(Shaders.VHS_FRAGMENT_SHADER_SOURCE, GL.GL_FRAGMENT_SHADER)
        self.vhs_shader_program = shaders.compileProgram(vhs_vertex_shader, vhs_fragment_shader)

        program_uniform_pairs = [
            (
                self.scene_shader_program,
                self.scene_uniform_locations,
                [
                    "view",
                    "time",
                    "model",
                    "viewPos",
                    "madness",
                    "lampColors",
                    "cctvTexture",
                    "decalAtlas",
                    "projection",
                    "memoryAtlas",
                    "realityTear",
                    "lightFlicker",
                    "emergencyRed",
                    "lampPositions",
                    "activeLampCount",
                    "paintingsAtlas",
                    "televisionAtlas",
                    "proceduralNoiseTexture",
                    "lobotomyIntensity",
                    "flashlightPosition",
                    "flashlightDirection"
                ]
            ),
            (
                self.monster_shader_program,
                self.monster_uniform_locations,
                [
                    "view",
                    "time",
                    "model",
                    "viewPos",
                    "projection",
                    "twitchIntensity"
                ]
            ),
            (
                self.hud_shader_program,
                self.hud_uniform_locations,
                [
                    "uRect",
                    "hudTexture"
                ]
            ),
            (
                self.vhs_shader_program,
                self.vhs_uniform_locations,
                [
                    "time",
                    "coldDesat",
                    "introPhase",
                    "cutToBlack",
                    "whiteBloom",
                    "realityTear",
                    "heavyEyelids",
                    "screenTexture",
                    "cameraTurnBlur",
                    "jumpscareBlood",
                    "derealization",
                    "cameraTurnVector",
                    "glitchMultiplier",
                    "lobotomyIntensity"
                ]
            )
        ]

        for program, location_dictionary, uniform_names in program_uniform_pairs:
            for uniform_name in uniform_names:
                location_dictionary[uniform_name] = GL.glGetUniformLocation(program, uniform_name)

        self.television_atlas_texture_id = self.create_broadcast_atlas_texture()
        self.paintings_atlas_texture_id  = self.create_paintings_atlas_texture()
        self.memory_atlas_texture_id     = self.create_memory_atlas_texture()
        self.decal_atlas_texture_id      = self.create_decal_atlas_texture()
        self.procedural_noise_texture_id = self.create_procedural_noise_texture()

        self.wall_renderer.build_monolithic_maze_mesh(self.cell_scale_units, self.maze_dimension, self.wall_height_units, self.world_grid_array)
        self.lamp_renderer.initialize_lamps(self.lamp_world_positions, self.wall_height_units)
        self.item_renderer.build_televisions_mesh(self.cell_scale_units, self.maze_dimension, self.world_grid_array)
        self.item_renderer.build_scanner_mesh(self.device_world_position)
        self.item_renderer.build_sprite_mesh()
        self.item_renderer.build_monster_mesh()
        self.item_renderer.build_falling_paintings(self.available_paintings_count, self.maze_dimension, self.cell_scale_units, self.world_grid_array, self.camera_position)

        self.scanner_display_texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.scanner_display_texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 256, 256, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

        fullscreen_quad_vertices = numpy.array([
            -1.0,  1.0, 0.0, 1.0,
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 1.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0
        ], dtype = numpy.float32)

        self.fullscreen_quad_mesh = GLMesh(fullscreen_quad_vertices, [(0, 2), (1, 2)])

        hud_quad_vertices  = numpy.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype = numpy.float32)
        self.hud_quad_mesh = GLMesh(hud_quad_vertices, [(0, 2)])

        pixel_ratio = self.devicePixelRatio()
        self.rebuild_framebuffer(int(self.width() * pixel_ratio), int(self.height() * pixel_ratio))
        self.setCursor(Qt.CursorShape.BlankCursor)

    def rebuild_framebuffer(self, width: int, height: int) -> None:
        pixel_width  = max(1, width)
        pixel_height = max(1, height)

        if self.framebuffer_object_id is not None:
            GL.glDeleteFramebuffers(1, [self.framebuffer_object_id])

        if self.screen_texture_id is not None:
            GL.glDeleteTextures(1, [self.screen_texture_id])

        if self.renderbuffer_depth_id is not None:
            GL.glDeleteRenderbuffers(1, [self.renderbuffer_depth_id])

        self.framebuffer_object_id = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer_object_id)

        self.screen_texture_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.screen_texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, pixel_width, pixel_height, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.screen_texture_id, 0)

        self.renderbuffer_depth_id = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.renderbuffer_depth_id)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH24_STENCIL8, pixel_width, pixel_height)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_STENCIL_ATTACHMENT, GL.GL_RENDERBUFFER, self.renderbuffer_depth_id)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())

    def resizeGL(self, width: int, height: int) -> None:
        pixel_ratio = self.devicePixelRatio()
        self.rebuild_framebuffer(int(width * pixel_ratio), int(height * pixel_ratio))

        if hasattr(self.parent(), "reposition_hud_message"):
            self.parent().reposition_hud_message()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.activate_game_window)

    def activate_game_window(self) -> None:
        if not self.isVisible():
            return

        game_window = self.window()
        game_window.raise_()
        game_window.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def paintGL(self) -> None:
        if self.render_profiler_enabled:
            frame_start_time = time.perf_counter()
            self.render_profile_current = {}

            if self.render_profile_previous_frame_start is not None:
                self._record_render_profile(
                    "frame_interval",
                    (frame_start_time - self.render_profile_previous_frame_start) * 1000.0
                )

            self.render_profile_previous_frame_start = frame_start_time

        pixel_ratio  = self.devicePixelRatio()
        pixel_width  = float(max(1, int(self.width() * pixel_ratio)))
        pixel_height = float(max(1, int(self.height() * pixel_ratio)))

        if pixel_width <= 0 or pixel_height <= 0 or self.framebuffer_object_id is None:
            return

        if self.render_profiler_enabled:
            self._record_render_profile("frame_gate", (time.perf_counter() - frame_start_time) * 1000.0)
            self._poll_gpu_profile_queries()

        scene_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0

        if self.scanner_texture_dirty:
            self.scanner_texture_dirty = False
            raw_bits = self.scanner_qimage.constBits()
            raw_bits.setsize(self.scanner_qimage.sizeInBytes())
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.scanner_display_texture_id)
            GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, 256, 256, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(raw_bits))

        if self.render_profiler_enabled:
            self._begin_gpu_profile_query("gpu_scene")

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer_object_id)
        GL.glViewport(0, 0, int(pixel_width), int(pixel_height))
        GL.glDisable(GL.GL_BLEND)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(0.002, 0.002, 0.003, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        GL.glUseProgram(self.scene_shader_program)
        matrix_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        effective_field_of_view = 70.0 + self.field_of_view_offset + self.anomaly_manager.vertigo_fov_offset
        aspect_ratio = pixel_width / max(1.0, pixel_height)
        projection_key = (effective_field_of_view, aspect_ratio, 0.1, 100.0)

        if projection_key != self.projection_matrix_cache_key:
            self.projection_matrix_cache = Geometry.perspective_matrix(*projection_key)
            self.projection_matrix_cache_key = projection_key

        projection_matrix = self.projection_matrix_cache

        total_roll_angle = self.roll_degrees + self.gravity_tilt + self.camera_bobbing_x * 0.4 + self.anomaly_manager.vertigo_roll_offset
        up_x = math.sin(math.radians(total_roll_angle))
        up_y = math.cos(math.radians(total_roll_angle))

        camera_x = float(self.camera_position[0])
        camera_y = float(self.camera_position[1] + numpy.float32(self.camera_bobbing_y))
        camera_z = float(self.camera_position[2])
        view_key = (
            camera_x,
            camera_y,
            camera_z,
            camera_x + float(self.camera_front[0]),
            camera_y + float(self.camera_front[1]),
            camera_z + float(self.camera_front[2]),
            up_x,
            up_y,
            0.0
        )

        if view_key != self.view_matrix_cache_key:
            view_camera_coordinate = numpy.array([camera_x, camera_y, camera_z], dtype = numpy.float32)
            view_target_coordinate = view_camera_coordinate + self.camera_front
            up_orientation = numpy.array([up_x, up_y, 0.0], dtype = numpy.float32)
            self.view_matrix_cache = Geometry.look_at(view_camera_coordinate, view_target_coordinate, up_orientation)
            self.view_matrix_cache_key = view_key

        view_matrix = self.view_matrix_cache

        if self.render_profiler_enabled:
            self._record_render_profile("camera_matrices", (time.perf_counter() - matrix_start_time) * 1000.0)

        effective_light_flicker = 0.0 if self.anomaly_manager.blackout_active else self.light_flicker_ratio

        uniform_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        GL.glUniformMatrix4fv(self.scene_uniform_locations["projection"], 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(self.scene_uniform_locations["view"], 1, GL.GL_FALSE, view_matrix)
        GL.glUniformMatrix4fv(self.scene_uniform_locations["model"], 1, GL.GL_FALSE, self.identity_matrix_4)
        GL.glUniform3fv(self.scene_uniform_locations["viewPos"], 1, self.camera_position)
        GL.glUniform3fv(self.scene_uniform_locations["flashlightPosition"], 1, self.flashlight_position)
        GL.glUniform3fv(self.scene_uniform_locations["flashlightDirection"], 1, self.flashlight_front)
        GL.glUniform1f(self.scene_uniform_locations["time"], self.elapsed_time_seconds)
        GL.glUniform1f(self.scene_uniform_locations["lightFlicker"], effective_light_flicker)
        GL.glUniform1f(self.scene_uniform_locations["madness"], self.madness_ratio)
        effective_reality_tear = max(self.reality_tear_ratio, self.anomaly_manager.reality_tear_intensity)
        effective_lobotomy = max(self.lobotomy_intensity, self.anomaly_manager.lobotomy_intensity)
        GL.glUniform1f(self.scene_uniform_locations["realityTear"], effective_reality_tear)
        GL.glUniform1f(self.scene_uniform_locations["emergencyRed"], self.emergency_red_intensity)
        GL.glUniform1f(self.scene_uniform_locations["lobotomyIntensity"], effective_lobotomy)

        if self.render_profiler_enabled:
            self._record_render_profile("scene_uniforms", (time.perf_counter() - uniform_start_time) * 1000.0)

        lamp_selection_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        lamp_positions, lamp_colors, active_count = self.lamp_renderer.get_active_lamp_lighting_data(self.camera_position, 8)

        if self.render_profiler_enabled:
            self._record_render_profile("lamp_selection", (time.perf_counter() - lamp_selection_start_time) * 1000.0)

        if self.anomaly_manager.blackout_active:
            active_count = 0

        lamp_uniform_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        GL.glUniform1i(self.scene_uniform_locations["activeLampCount"], active_count)
        GL.glUniform3fv(self.scene_uniform_locations["lampPositions"], 8, lamp_positions.ravel())
        GL.glUniform3fv(self.scene_uniform_locations["lampColors"], 8, lamp_colors.ravel())

        if self.render_profiler_enabled:
            self._record_render_profile("lamp_uniforms", (time.perf_counter() - lamp_uniform_start_time) * 1000.0)

        texture_bind_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.decal_atlas_texture_id)
        GL.glUniform1i(self.scene_uniform_locations["decalAtlas"], 1)

        GL.glActiveTexture(GL.GL_TEXTURE3)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.paintings_atlas_texture_id)
        GL.glUniform1i(self.scene_uniform_locations["paintingsAtlas"], 3)

        GL.glActiveTexture(GL.GL_TEXTURE4)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.memory_atlas_texture_id)
        GL.glUniform1i(self.scene_uniform_locations["memoryAtlas"], 4)

        GL.glActiveTexture(GL.GL_TEXTURE5)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.television_atlas_texture_id)
        GL.glUniform1i(self.scene_uniform_locations["televisionAtlas"], 5)

        GL.glActiveTexture(GL.GL_TEXTURE6)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.procedural_noise_texture_id)
        GL.glUniform1i(self.scene_uniform_locations["proceduralNoiseTexture"], 6)

        if self.render_profiler_enabled:
            self._record_render_profile("scene_textures", (time.perf_counter() - texture_bind_start_time) * 1000.0)

        if self.render_profiler_enabled:
            self._record_render_profile("scene_setup", (time.perf_counter() - scene_start_time) * 1000.0)

        scene_draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)
        self.wall_renderer.render_walls()
        GL.glDisable(GL.GL_CULL_FACE)

        if self.render_profiler_enabled:
            self._record_render_profile("draw_walls", (time.perf_counter() - draw_start_time) * 1000.0)

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        self.lamp_renderer.render_fixtures()
        if self.render_profiler_enabled:
            self._record_render_profile("draw_lamp_fixtures", (time.perf_counter() - draw_start_time) * 1000.0)

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        self.lamp_renderer.render_tubes()
        if self.render_profiler_enabled:
            self._record_render_profile("draw_lamp_tubes", (time.perf_counter() - draw_start_time) * 1000.0)

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        self.lamp_renderer.render_sparks()
        if self.render_profiler_enabled:
            self._record_render_profile("draw_lamp_sparks", (time.perf_counter() - draw_start_time) * 1000.0)

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        self.item_renderer.render_televisions()
        if self.render_profiler_enabled:
            self._record_render_profile("draw_static_items", (time.perf_counter() - draw_start_time) * 1000.0)

        draw_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        self.item_renderer.render_paintings(self.scene_uniform_locations["model"])
        if self.render_profiler_enabled:
            self._record_render_profile("draw_paintings", (time.perf_counter() - draw_start_time) * 1000.0)

        if self.render_profiler_enabled:
            self._record_render_profile("scene_draw", (time.perf_counter() - scene_draw_start_time) * 1000.0)

        entity_hud_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0

        GL.glUniformMatrix4fv(self.scene_uniform_locations["model"], 1, GL.GL_FALSE, self.identity_matrix_4)

        if not self.device_picked_up:
            self.item_renderer.render_scanner()

        if self.sprite_entity_active:
            self.item_renderer.render_sprite(self.scene_uniform_locations["model"], self.sprite_entity_position, self.camera_position)
            GL.glUniformMatrix4fv(self.scene_uniform_locations["model"], 1, GL.GL_FALSE, self.identity_matrix_4)

        if self.monster_entity_active:
            self.item_renderer.render_monster(
                monster_shader_program = self.monster_shader_program,
                uniform_locations      = self.monster_uniform_locations,
                monster_position       = self.monster_entity_position,
                player_camera_position = self.camera_position,
                projection_matrix      = projection_matrix,
                view_matrix            = view_matrix,
                elapsed_time_seconds   = self.elapsed_time_seconds
            )

        if self.device_picked_up and self.cut_to_black_factor < 0.5 and not self.intro_active:
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            GL.glUseProgram(self.hud_shader_program)

            radar_physical_size = min(250.0 * pixel_ratio, pixel_height * 0.45, pixel_width * 0.45)
            margin_physical     = 24.0 * pixel_ratio

            width_ndc  = (radar_physical_size / pixel_width) * 2.0
            height_ndc = (radar_physical_size / pixel_height) * 2.0

            margin_x_ndc = (margin_physical / pixel_width) * 2.0
            margin_y_ndc = (margin_physical / pixel_height) * 2.0

            rect_x_ndc = 1.0 - margin_x_ndc - width_ndc
            rect_y_ndc = -1.0 + margin_y_ndc

            GL.glUniform4f(self.hud_uniform_locations["uRect"], rect_x_ndc, rect_y_ndc, width_ndc, height_ndc)

            GL.glActiveTexture(GL.GL_TEXTURE2)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.scanner_display_texture_id)
            GL.glUniform1i(self.hud_uniform_locations["hudTexture"], 2)

            if self.hud_quad_mesh is not None:
                self.hud_quad_mesh.draw()

            GL.glDisable(GL.GL_BLEND)

        if self.render_profiler_enabled:
            self._record_render_profile("entities_hud", (time.perf_counter() - entity_hud_start_time) * 1000.0)
            self._end_gpu_profile_query()

        postprocess_start_time = time.perf_counter() if self.render_profiler_enabled else 0.0
        if self.render_profiler_enabled:
            self._begin_gpu_profile_query("gpu_postprocess")

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.defaultFramebufferObject())
        GL.glViewport(0, 0, int(pixel_width), int(pixel_height))
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_BLEND)

        GL.glUseProgram(self.vhs_shader_program)
        GL.glUniform1f(self.vhs_uniform_locations["time"], self.elapsed_time_seconds)
        GL.glUniform1f(self.vhs_uniform_locations["glitchMultiplier"], self.white_noise_proximity_glitch)
        GL.glUniform1f(self.vhs_uniform_locations["introPhase"], 1.0 if self.intro_active else 0.0)
        GL.glUniform1f(self.vhs_uniform_locations["cutToBlack"], self.cut_to_black_factor)
        GL.glUniform1f(self.vhs_uniform_locations["realityTear"], effective_reality_tear)
        GL.glUniform1f(self.vhs_uniform_locations["jumpscareBlood"], self.jumpscare_blood_factor)
        GL.glUniform1f(self.vhs_uniform_locations["derealization"], self.anomaly_manager.derealization_intensity)
        GL.glUniform1f(self.vhs_uniform_locations["lobotomyIntensity"], effective_lobotomy)
        GL.glUniform1f(self.vhs_uniform_locations["heavyEyelids"], max(self.heavy_eyelids_factor, self.anomaly_manager.heavy_eyelids_intensity))
        GL.glUniform1f(self.vhs_uniform_locations["whiteBloom"], max(self.white_bloom_factor, self.anomaly_manager.white_bloom_intensity))
        GL.glUniform1f(self.vhs_uniform_locations["coldDesat"], max(self.cold_desaturation, self.anomaly_manager.cold_desaturation_intensity))
        GL.glUniform2fv(self.vhs_uniform_locations["cameraTurnVector"], 1, self.camera_turn_vector)
        GL.glUniform1f(self.vhs_uniform_locations["cameraTurnBlur"], self.camera_turn_blur)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.screen_texture_id)
        GL.glUniform1i(self.vhs_uniform_locations["screenTexture"], 0)

        if self.fullscreen_quad_mesh is not None:
            self.fullscreen_quad_mesh.draw()

        if self.render_profiler_enabled:
            self._record_render_profile("postprocess", (time.perf_counter() - postprocess_start_time) * 1000.0)
            self._end_gpu_profile_query()
            self._record_render_profile("frame_cpu_total", (time.perf_counter() - frame_start_time) * 1000.0)
            self.render_profile_frame_index += 1
            self.render_profile_samples.append(self.render_profile_current)

            if self.render_profile_frame_index % 60 == 0:
                self._emit_render_profile_summary()

    # Communication Helper

    def display_message(self, message_text: str) -> None:
        if hasattr(self.parent(), "display_onscreen_message"):
            self.parent().display_onscreen_message(message_text)

    def _record_render_profile(self, phase_name: str, elapsed_ms: float) -> None:
        if not self.render_profiler_enabled:
            return

        self.render_profile_current[phase_name] = float(elapsed_ms)

    def _poll_gpu_profile_queries(self) -> None:
        completed_queries: list[tuple[str, int]] = []

        for phase_name, query_id in self.gpu_profile_pending_queries:
            if GL.glGetQueryObjectiv(query_id, GL.GL_QUERY_RESULT_AVAILABLE):
                elapsed_nanoseconds = GL.glGetQueryObjectuiv(query_id, GL.GL_QUERY_RESULT)
                completed_queries.append((phase_name, query_id))
                self._record_render_profile(phase_name, float(elapsed_nanoseconds) / 1_000_000.0)

        for completed_query in completed_queries:
            self.gpu_profile_pending_queries.remove(completed_query)

    def _begin_gpu_profile_query(self, phase_name: str) -> None:
        if self.gpu_profile_active_query is not None:
            return

        pending_query_ids = {query_id for _, query_id in self.gpu_profile_pending_queries}

        for query_id in self.gpu_profile_query_ids.get(phase_name, []):
            if query_id in pending_query_ids:
                continue

            GL.glBeginQuery(GL.GL_TIME_ELAPSED, query_id)
            self.gpu_profile_active_query = (phase_name, query_id)
            return

    def _end_gpu_profile_query(self) -> None:
        if self.gpu_profile_active_query is None:
            return

        phase_name, query_id = self.gpu_profile_active_query
        GL.glEndQuery(GL.GL_TIME_ELAPSED)
        self.gpu_profile_pending_queries.append((phase_name, query_id))
        self.gpu_profile_active_query = None

    def _emit_render_profile_summary(self) -> None:
        if not self.render_profiler_enabled or not self.render_profile_samples:
            return

        lines = [f"[EditorProfile] frame={self.render_profile_frame_index} window={len(self.render_profile_samples)} cpu-clock=perf_counter"]
        phase_names = sorted({phase_name for frame in self.render_profile_samples for phase_name in frame})

        for phase_name in phase_names:
            values = sorted(frame[phase_name] for frame in self.render_profile_samples if phase_name in frame)
            percentile_95 = values[min(len(values) - 1, int((len(values) - 1) * 0.95))]
            lines.append(
                f"  {phase_name}: avg={sum(values) / len(values):.3f}ms p95={percentile_95:.3f}ms "
                f"min={values[0]:.3f}ms max={values[-1]:.3f}ms samples={len(values)}"
            )

        print("\n".join(lines), flush = True)

    # Game Loop

    def process_game_loop_tick(self) -> None:
        global SCARY_SOUND_PLAYED_IN_SESSION

        delta_time = min(0.04, max(0.001, self.frame_stopwatch.restart() / 1000.0))
        self.elapsed_time_seconds += delta_time

        if self.intro_active:
            self.intro_timer_seconds -= delta_time

            if self.intro_timer_seconds <= 0.0:
                self.intro_active = False

                if hasattr(self.parent(), "hide_intro_osd"):
                    self.parent().hide_intro_osd()

            self.update()
            return

        if self.simulation_terminated:
            self.update()
            return

        if not SCARY_SOUND_PLAYED_IN_SESSION:
            self.scary_sound_timer_seconds -= delta_time

            if self.scary_sound_timer_seconds <= 0.0:
                SCARY_SOUND_PLAYED_IN_SESSION = True
                scary_sound_name = random.choice(Constants.SCARY_SOUND_NAMES)
                Player.ui_player.play_sound(
                    f"{Constants.ANOMALY_SOUND_DIRECTORY}/{scary_sound_name}",
                    pan                    = random.uniform(*Constants.SCARY_SOUND_PAN_RANGE),
                    loop                   = Constants.SCARY_SOUND_LOOP,
                    enable_tone_randomizer = Constants.SCARY_SOUND_TONE_RANDOMIZER
                )

        self.anomaly_manager.update(delta_time)
        self.lamp_renderer.update(delta_time, self.calculate_audio_pan, self.camera_position)

        if self.device_picked_up:
            self.radar_refresh_timer -= delta_time

            if self.radar_refresh_timer <= 0.0:
                self.radar_refresh_timer = 0.055

                Radar.render_radar_to_image(
                    target_image           = self.scanner_qimage,
                    camera_position        = self.camera_position,
                    camera_yaw_degrees     = self.yaw_degrees,
                    grid_matrix            = self.world_grid_array,
                    cell_scale_units       = self.cell_scale_units,
                    maze_dimension         = self.maze_dimension,
                    path_waypoints         = self.solution_path_points,
                    current_waypoint_index = self.current_waypoint_index,
                    scenario_status_text   = self.active_scenario.get_radar_status_text(self),
                    is_glitch_scenario     = (self.run_fate_scenario in ("RADAR_GLITCH", "BROKEN_RADAR")),
                    bogus_waypoint         = self.bogus_waypoint_position,
                    elapsed_time_seconds   = self.elapsed_time_seconds,
                    chase_counter          = self.radar_chase_count,
                    sprite_active          = self.sprite_entity_active,
                    sprite_position        = self.sprite_entity_position,
                    monster_active         = self.monster_entity_active,
                    monster_position       = self.monster_entity_position,
                    finale_sequence_active = self.finale_sequence_active
                )

                self.scanner_texture_dirty = True

        scale_unit      = self.cell_scale_units
        player_x        = self.camera_position[0]
        player_z        = self.camera_position[2]
        glitch_strength = 0.0

        for wall_x, wall_z in self.wall_renderer.white_noise_walls_list:
            clamped_x = max(wall_x * scale_unit, min(player_x, (wall_x + 1) * scale_unit))
            clamped_z = max(wall_z * scale_unit, min(player_z, (wall_z + 1) * scale_unit))
            distance  = math.hypot(player_x - clamped_x, player_z - clamped_z)

            if distance < Constants.GLITCH_PROXIMITY_RADIUS:
                fade_factor     = 1.0 - (distance / Constants.GLITCH_PROXIMITY_RADIUS)
                glitch_strength = max(glitch_strength, (fade_factor ** 1.3) * 5)

        self.white_noise_proximity_glitch = glitch_strength

        if self.device_picked_up and not self.finale_sequence_active and self.solution_path_points:
            if self.run_fate_scenario not in ("RADAR_GLITCH", "BROKEN_RADAR"):
                furthest_reached_index = self.current_waypoint_index
                maximum_lookahead      = min(len(self.solution_path_points), self.current_waypoint_index + 10)

                for candidate_index in range(self.current_waypoint_index, maximum_lookahead):
                    candidate_node  = self.solution_path_points[candidate_index]
                    candidate_world = numpy.array([
                        (candidate_node[0] + 0.5) * scale_unit,
                        1.4,
                        (candidate_node[1] + 0.5) * scale_unit
                    ], dtype = numpy.float32)

                    distance_to_candidate = math.hypot(
                        self.camera_position[0] - candidate_world[0],
                        self.camera_position[2] - candidate_world[2]
                    )

                    if distance_to_candidate < 3.2:
                        has_line_of_sight = WorldBuilder.test_line_of_sight(
                            self.camera_position,
                            candidate_world,
                            self.world_grid_array,
                            scale_unit,
                            self.maze_dimension
                        )

                        if has_line_of_sight:
                            furthest_reached_index = max(furthest_reached_index, candidate_index)

                if furthest_reached_index > self.current_waypoint_index:
                    self.current_waypoint_index = min(len(self.solution_path_points) - 1, furthest_reached_index + 1)
                    Player.ui_player.play_sound(".vault/Anomaly/RadarBeep", volume = 0.1)

                else:
                    target_waypoint    = self.solution_path_points[self.current_waypoint_index]
                    distance_to_target = math.hypot(
                        self.camera_position[0] - (target_waypoint[0] + 0.5) * scale_unit,
                        self.camera_position[2] - (target_waypoint[1] + 0.5) * scale_unit
                    )

                    if distance_to_target < 2.5:
                        if self.current_waypoint_index < len(self.solution_path_points) - 1:
                            self.current_waypoint_index += 1
                            Player.ui_player.play_sound(".vault/Anomaly/RadarBeep", volume = 0.1)

        self.active_scenario.update(self, delta_time)

        smooth_damping         = 1.0 - math.exp(-delta_time * 26.0)
        previous_yaw_degrees   = self.yaw_degrees
        previous_pitch_degrees = self.pitch_degrees
        self.yaw_degrees      += (self.target_yaw_degrees   - self.yaw_degrees)   * smooth_damping
        self.pitch_degrees    += (self.target_pitch_degrees - self.pitch_degrees) * smooth_damping
        yaw_velocity           = (self.yaw_degrees - previous_yaw_degrees) / delta_time
        pitch_velocity         = (self.pitch_degrees - previous_pitch_degrees) / delta_time
        turn_speed             = math.hypot(yaw_velocity, pitch_velocity)
        target_turn_blur       = min(1.0, turn_speed / 150.0)
        blur_response          = 1.0 - math.exp(-delta_time * (18.0 if target_turn_blur > self.camera_turn_blur else 5.0))
        self.camera_turn_blur += (target_turn_blur - self.camera_turn_blur) * blur_response

        if turn_speed > 1e-3:
            self.camera_turn_vector = numpy.array([-yaw_velocity / turn_speed, pitch_velocity / turn_speed], dtype = numpy.float32)

        self.camera_front = numpy.array([
            math.cos(math.radians(self.yaw_degrees)) * math.cos(math.radians(self.pitch_degrees)),
            math.sin(math.radians(self.pitch_degrees)),
            math.sin(math.radians(self.yaw_degrees)) * math.cos(math.radians(self.pitch_degrees))
        ], dtype = numpy.float32)
        self.camera_front /= numpy.linalg.norm(self.camera_front)

        if not self.device_picked_up:
            distance_to_device = numpy.linalg.norm(self.camera_position - self.device_world_position)

            if distance_to_device < 1.8:
                self.device_picked_up = True
                self.display_message(Constants.EDITOR_UI_TEXTS["scanner_attached"].format(user_name = Constants.USER_NAME))

            else:
                interaction_message = self.item_renderer.laptops.check_interaction(self.camera_position)

                if interaction_message is not None:
                    self.display_message(interaction_message)

        forward_horizontal = numpy.array([self.camera_front[0], 0.0, self.camera_front[2]])

        if numpy.linalg.norm(forward_horizontal) > 0.0:
            forward_horizontal /= numpy.linalg.norm(forward_horizontal)

        right_horizontal = numpy.cross(forward_horizontal, self.camera_up)

        if numpy.linalg.norm(right_horizontal) > 0.0:
            right_horizontal /= numpy.linalg.norm(right_horizontal)

        movement_intent = numpy.zeros(3, dtype = numpy.float32)
        strafe_value    = 0.0

        if Qt.Key.Key_W in self.pressed_key_codes:
            movement_intent += forward_horizontal

        if Qt.Key.Key_S in self.pressed_key_codes:
            movement_intent -= forward_horizontal

        if Qt.Key.Key_A in self.pressed_key_codes:
            movement_intent -= right_horizontal
            strafe_value    -= 1.0

        if Qt.Key.Key_D in self.pressed_key_codes:
            movement_intent += right_horizontal
            strafe_value    += 1.0

        if numpy.linalg.norm(movement_intent) > 0.0:
            movement_intent /= numpy.linalg.norm(movement_intent)

        is_sprinting = (Qt.Key.Key_Shift in self.pressed_key_codes) and (Qt.Key.Key_W in self.pressed_key_codes)
        base_speed   = 3.6

        if self.run_fate_scenario == "BURNOUT":
            base_speed *= max(0.0, 1.0 - (self.elapsed_time_seconds / 45.0) * 0.85)

        effective_speed = base_speed * 1.5 if is_sprinting else base_speed
        target_velocity = movement_intent * effective_speed

        self.velocity_vector += (target_velocity - self.velocity_vector) * min(1.0, delta_time * 18.0)
        movement_step         = self.velocity_vector * delta_time

        previous_position_x = float(self.camera_position[0])
        previous_position_z = float(self.camera_position[2])
        radius          = 0.35
        next_position_x = self.camera_position[0] + movement_step[0]

        if not WorldBuilder.check_tile_collision(next_position_x, self.camera_position[2], radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
            self.camera_position[0] = next_position_x

        next_position_z = self.camera_position[2] + movement_step[2]

        if not WorldBuilder.check_tile_collision(self.camera_position[0], next_position_z, radius, self.world_grid_array, self.cell_scale_units, self.maze_dimension):
            self.camera_position[2] = next_position_z

        actual_movement_distance = math.hypot(
            float(self.camera_position[0]) - previous_position_x,
            float(self.camera_position[2]) - previous_position_z
        )
        speed_magnitude = numpy.linalg.norm(self.velocity_vector)

        if speed_magnitude > 0.1:
            previous_step_index = int(self.walk_cycle_phase / math.pi)
            step_rate           = Constants.SPRINT_CYCLE_RATE if is_sprinting else Constants.WALK_CYCLE_RATE
            self.walk_cycle_phase += delta_time * step_rate
            current_step_index = int(self.walk_cycle_phase / math.pi)
            bobbing_intensity      = 0.075 if is_sprinting else 0.038

            self.camera_bobbing_y = math.sin(self.walk_cycle_phase) * bobbing_intensity + math.cos(self.walk_cycle_phase * 2.0) * (bobbing_intensity * 0.3)
            self.camera_bobbing_x = math.cos(self.walk_cycle_phase * 0.5) * (bobbing_intensity * 1.2)

            if actual_movement_distance > Constants.FOOTSTEP_MOVEMENT_THRESHOLD and current_step_index > previous_step_index:
                step_sound = random.choice(Constants.FOOTSTEP_SOUND_NAMES)
                Player.ui_player.play_sound(
                    f"{Constants.ANOMALY_SOUND_DIRECTORY}/{step_sound}",
                    volume                 = Constants.FOOTSTEP_SOUND_VOLUME,
                    loop                   = Constants.FOOTSTEP_SOUND_LOOP,
                    enable_tone_randomizer = Constants.FOOTSTEP_SOUND_TONE_RANDOMIZER
                )

        else:
            self.camera_bobbing_y *= 0.85
            self.camera_bobbing_x *= 0.85

        self.flashlight_idle_phase += delta_time * 2.4
        flashlight_idle_sway_x      = math.sin(self.flashlight_idle_phase * 0.85) * 0.015
        flashlight_idle_sway_y      = math.cos(self.flashlight_idle_phase * 1.25) * 0.018

        if speed_magnitude > 0.1:
            footstep_rate                  = 14.5 if is_sprinting else 9.8
            self.flashlight_bobbing_phase += delta_time * footstep_rate
            step_scale                     = 1.45 if is_sprinting else 1.0

            flashlight_walk_sway_x = math.cos(self.flashlight_bobbing_phase * 0.5) * 0.048 * step_scale
            flashlight_walk_bob_y  = math.sin(self.flashlight_bobbing_phase) * 0.058 * step_scale

        else:
            self.flashlight_bobbing_phase *= 0.88
            flashlight_walk_sway_x         = 0.0
            flashlight_walk_bob_y          = 0.0

        hand_hold_offset = (
            right_horizontal * 0.24 -
            numpy.array([0.0, 0.28, 0.0], dtype = numpy.float32) +
            self.camera_front * 0.14
        )
        total_sway_horizontal = right_horizontal * (flashlight_walk_sway_x + flashlight_idle_sway_x)
        total_bob_vertical    = numpy.array([0.0, flashlight_walk_bob_y + flashlight_idle_sway_y, 0.0], dtype = numpy.float32)

        target_flashlight_position  = self.camera_position + hand_hold_offset + total_sway_horizontal + total_bob_vertical
        target_flashlight_direction = (
            self.camera_front +
            right_horizontal * (flashlight_walk_sway_x * 0.55 + flashlight_idle_sway_x * 0.75) +
            self.camera_up * (flashlight_walk_bob_y * 0.75 + flashlight_idle_sway_y * 0.75)
        )
        target_flashlight_direction /= numpy.linalg.norm(target_flashlight_direction)

        flashlight_position_lag_damping  = 1.0 - math.exp(-delta_time * 15.0)
        flashlight_direction_lag_damping = 1.0 - math.exp(-delta_time * 10.5)

        self.flashlight_position += (target_flashlight_position - self.flashlight_position) * flashlight_position_lag_damping
        self.flashlight_front    += (target_flashlight_direction - self.flashlight_front) * flashlight_direction_lag_damping
        self.flashlight_front    /= numpy.linalg.norm(self.flashlight_front)

        target_roll        = strafe_value * -6.5
        self.roll_degrees += (target_roll - self.roll_degrees) * min(1.0, delta_time * 12.0)

        self.update_lamp_hum(delta_time)
        self.item_renderer.update_paintings_fall(delta_time, self.camera_position, self.calculate_audio_pan)
        self.update()

    # Audio Calculation

    def calculate_audio_pan(self, source_x: float, source_z: float) -> float:
        offset_x        = source_x - float(self.camera_position[0])
        offset_z        = source_z - float(self.camera_position[2])
        source_distance = math.hypot(offset_x, offset_z)

        if source_distance <= 1e-6:
            return 0.0

        right_x      = -float(self.camera_front[2])
        right_z      = float(self.camera_front[0])
        right_length = math.hypot(right_x, right_z)

        if right_length <= 1e-6:
            return 0.0

        return (offset_x * right_x + offset_z * right_z) / (source_distance * right_length)

    def update_lamp_hum(self, delta_time_seconds: float) -> None:
        maximum_active_lamps = 6
        audible_range        = 24.0
        player_x             = float(self.camera_position[0])
        player_z             = float(self.camera_position[2])

        distances = [
            (
                math.hypot(lamp.position_x - player_x, lamp.position_z - player_z),
                lamp_index,
                lamp.position_x,
                lamp.position_z,
                lamp.is_broken,
                lamp.flicker_factor
            )
            for lamp_index, lamp in enumerate(self.lamp_renderer.lamps_list)
        ]
        nearby_lamps = [
            lamp for lamp in sorted(distances)
            if lamp[0] < audible_range and not lamp[4]
        ]
        selected_lamps = {
            lamp_index: (distance, lamp_x, lamp_z, flicker_factor)
            for distance, lamp_index, lamp_x, lamp_z, is_broken, flicker_factor in nearby_lamps[:maximum_active_lamps]
        }

        for lamp_index, state in tuple(self.lamp_hum_sounds.items()):
            if not state.sound.is_active():
                del self.lamp_hum_sounds[lamp_index]

        for distance, lamp_index, lamp_x, lamp_z, is_broken, flicker_factor in nearby_lamps:
            if len(self.lamp_hum_sounds) >= maximum_active_lamps:
                break

            if lamp_index in self.lamp_hum_sounds:
                continue

            sound = Player.ui_player.play_sound(
                ".vault/Anomaly/Hum",
                loop                   = True,
                volume                 = 0.0,
                pan                    = self.calculate_audio_pan(lamp_x, lamp_z),
                enable_tone_randomizer = False
            )

            if sound.sound_id >= 0:
                self.lamp_hum_sounds[lamp_index] = RuntimeLampHum(sound = sound)

        master_volume = ApplicationConstants.current_settings.get("sound_effect_volume", 100) / 100.0
        smoothing     = 1.0 - math.exp(-delta_time_seconds * 5.0)
        pan_smoothing = 1.0 - math.exp(-delta_time_seconds * 8.0)

        for lamp_index, state in tuple(self.lamp_hum_sounds.items()):
            target_volume = 0.0

            if lamp_index in selected_lamps:
                distance, lamp_x, lamp_z, flicker_factor = selected_lamps[lamp_index]
                distance_gain                            = 1.0 / (1.0 + (distance / 5.0) ** 2)
                range_fade                               = 1.0 - min(1.0, max(0.0, (distance - 16.0) / (audible_range - 16.0)))
                current_flicker                          = 0.0 if self.anomaly_manager.blackout_active else flicker_factor
                target_volume                            = 0.32 * distance_gain * range_fade * master_volume * 0.8 * current_flicker
                target_pan                               = self.calculate_audio_pan(lamp_x, lamp_z)
                state.pan                               += (target_pan - state.pan) * pan_smoothing
                state.sound.set_pan(state.pan)

            volume_smoothing = (
                1.0 - math.exp(-delta_time_seconds * 28.0)
                if target_volume <= 0.01 or state.volume <= 0.01
                else smoothing
            )
            state.volume += (target_volume - state.volume) * volume_smoothing
            state.sound.set_volume(state.volume)

            if target_volume == 0.0 and state.volume < 0.002:
                state.sound.stop()
                del self.lamp_hum_sounds[lamp_index]

    def finalize_easter_egg_termination(self, message: str) -> None:
        self.simulation_terminated = True
        self.cut_to_black_factor   = 1.0

        for state in self.lamp_hum_sounds.values():
            state.sound.stop()

        self.lamp_hum_sounds.clear()
        self.display_message(message)
        self.update()

        Player.ui_player.play_sound(".vault/Anomaly/Unload", enable_tone_randomizer = False)
        QTimer.singleShot(4000, self.terminate_application)

    def terminate_application(self) -> None:
        application = QApplication.instance()

        if application is not None:
            application.quit()

        os._exit(0)

    # User Input Events

    @staticmethod
    def normalized_key_code(event: QKeyEvent) -> int:
        event_text = event.text().casefold()
        normalized_text = Constants.KEYBOARD_LAYOUT_KEY_ALIASES.get(event_text)

        if normalized_text is None:
            return event.key()

        return ord(normalized_text.upper())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key_code = self.normalized_key_code(event)

        if key_code == Qt.Key.Key_Escape:
            self.mouse_cursor_locked = not self.mouse_cursor_locked
            self.setCursor(Qt.CursorShape.ArrowCursor if not self.mouse_cursor_locked else Qt.CursorShape.BlankCursor)

        elif key_code == Qt.Key.Key_E:
            if not self.device_picked_up and numpy.linalg.norm(self.camera_position - self.device_world_position) < 3.5:
                self.device_picked_up = True
                self.display_message(Constants.EDITOR_UI_TEXTS["scanner_attached"].format(user_name = Constants.USER_NAME))

            else:
                interaction_message = self.item_renderer.laptops.check_interaction(self.camera_position)

                if interaction_message is not None:
                    self.display_message(interaction_message)

        self.pressed_key_codes.add(key_code)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.pressed_key_codes.discard(self.normalized_key_code(event))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.mouse_cursor_locked or self.simulation_terminated or self.intro_active:
            return

        viewport_center = QPoint(self.width() // 2, self.height() // 2)

        if self.first_mouse_movement:
            self.first_mouse_movement = False
            QCursor.setPos(self.mapToGlobal(viewport_center))
            return

        cursor_delta = event.position().toPoint() - viewport_center

        if cursor_delta.isNull():
            return

        QCursor.setPos(self.mapToGlobal(viewport_center))

        sensitivity = 0.12
        self.target_yaw_degrees   += cursor_delta.x() * sensitivity
        self.target_pitch_degrees = max(-88.0, min(88.0, self.target_pitch_degrees - cursor_delta.y() * sensitivity))