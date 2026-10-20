from __future__ import annotations

import numpy

from .Items import (
    ChairCollection,
    LaptopCollection,
    ScannerPickupItem,
    PaintingCollection,
    ChipsaEntityManager,
    TelevisionCollection,
    MonsterEntityManager,
    CornerShadowCollection
)

# Unified Item Renderer

class ItemRenderer:
    def __init__(self) -> None:
        self.televisions:    TelevisionCollection    = TelevisionCollection()
        self.scanner:        ScannerPickupItem       = ScannerPickupItem()
        self.sprite:         ChipsaEntityManager     = ChipsaEntityManager()
        self.monster:        MonsterEntityManager    = MonsterEntityManager()
        self.paintings:      PaintingCollection      = PaintingCollection()
        self.chairs:         ChairCollection         = ChairCollection()
        self.laptops:        LaptopCollection        = LaptopCollection()
        self.shadows:        CornerShadowCollection  = CornerShadowCollection()

    def build_televisions_mesh(
            self,
            cell_scale_units: float,
            maze_dimension:   int,
            world_grid_array: numpy.ndarray
        ) -> None:

        self.televisions.build_mesh(cell_scale_units, maze_dimension, world_grid_array)
        self.chairs.build_mesh(cell_scale_units, maze_dimension, world_grid_array)
        self.laptops.build_mesh(cell_scale_units, maze_dimension, world_grid_array)
        self.shadows.build_mesh(cell_scale_units, maze_dimension, world_grid_array)

    def build_scanner_mesh(self, device_world_position: numpy.ndarray) -> None:
        self.scanner.build_mesh(device_world_position)

    def build_sprite_mesh(self, aspect_ratio: float) -> None:
        self.sprite.build_mesh(aspect_ratio)

    def build_monster_mesh(self) -> None:
        self.monster.build_mesh()

    def build_falling_paintings(
            self,
            available_paintings_count: int,
            maze_dimension:            int,
            cell_scale_units:          float,
            world_grid_array:          numpy.ndarray,
            player_camera_position:    numpy.ndarray
        ) -> None:

        self.paintings.build_falling_paintings(
            available_paintings_count,
            maze_dimension,
            cell_scale_units,
            world_grid_array,
            player_camera_position
        )

    def update_paintings_fall(
            self,
            delta_time_seconds:     float,
            player_camera_position: numpy.ndarray,
            calculate_audio_pan:    object
        ) -> None:

        self.televisions.update_ambient_audio(delta_time_seconds, player_camera_position, calculate_audio_pan)
        self.paintings.update_falling(delta_time_seconds, player_camera_position, calculate_audio_pan)
        self.laptops.update(delta_time_seconds)
        self.shadows.update(player_camera_position)

    def render_televisions(self) -> None:
        self.televisions.draw()
        self.chairs.draw()
        self.laptops.draw()
        self.shadows.draw()

    def render_paintings(self, model_uniform_location: int) -> None:
        self.paintings.render(model_uniform_location)

    def render_scanner(self) -> None:
        self.scanner.draw()

    def render_sprite(
            self,
            model_uniform_location: int,
            sprite_position:        numpy.ndarray,
            player_camera_position: numpy.ndarray
        ) -> None:

        self.sprite.render(model_uniform_location, sprite_position, player_camera_position)

    def render_monster(
            self,
            monster_shader_program: int,
            uniform_locations:      dict[str, int],
            monster_position:       numpy.ndarray,
            player_camera_position: numpy.ndarray,
            projection_matrix:      numpy.ndarray,
            view_matrix:            numpy.ndarray,
            elapsed_time_seconds:   float
        ) -> None:

        self.monster.render(
            monster_shader_program,
            uniform_locations,
            monster_position,
            player_camera_position,
            projection_matrix,
            view_matrix,
            elapsed_time_seconds
        )

    def cleanup(self) -> None:
        self.televisions.cleanup()
        self.chairs.cleanup()
        self.laptops.cleanup()
        self.shadows.cleanup()
        self.scanner.cleanup()
        self.sprite.cleanup()
        self.monster.cleanup()
        self.paintings.cleanup()