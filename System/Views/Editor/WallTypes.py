from __future__ import annotations

from dataclasses import dataclass

# Wall Data Definition

@dataclass(frozen = True)
class WallTypeDescriptor:
    type_identifier:             float
    type_name:                   str
    has_proximity_glitch_effect: bool = False

# Wall Types Registry

WALL_TYPE_STANDARD    = WallTypeDescriptor(0.0,  "STANDARD",   False)
WALL_TYPE_WHITE_NOISE = WallTypeDescriptor(50.0, "WHITE_NOISE", True)
WALL_TYPE_JITTER      = WallTypeDescriptor(51.0, "JITTER",      False)
WALL_TYPE_HOLE        = WallTypeDescriptor(52.0, "HOLE",        False)
WALL_TYPE_STRIPE      = WallTypeDescriptor(53.0, "STRIPE",      False)
WALL_TYPE_PANEL       = WallTypeDescriptor(54.0, "PANEL",       False)
WALL_TYPE_CONCRETE    = WallTypeDescriptor(55.0, "CONCRETE",    False)
WALL_TYPE_BRICK_TEAR  = WallTypeDescriptor(56.0, "BRICK_TEAR",  False)
WALL_TYPE_TILE        = WallTypeDescriptor(57.0, "TILE",        False)

REGISTERED_WALL_TYPES: list[tuple[int, WallTypeDescriptor]] = [
    (24,  WALL_TYPE_WHITE_NOISE),
    (44,  WALL_TYPE_JITTER),
    (64,  WALL_TYPE_HOLE),
    (84,  WALL_TYPE_STRIPE),
    (114, WALL_TYPE_PANEL),
    (144, WALL_TYPE_CONCRETE),
    (174, WALL_TYPE_BRICK_TEAR),
    (204, WALL_TYPE_TILE)
]

# Wall Resolvers

def determine_wall_type_from_grid_coordinate(
        grid_coordinate_x: int,
        grid_coordinate_z: int
    ) -> WallTypeDescriptor:

    hash_value = (grid_coordinate_x * 73856093 ^ grid_coordinate_z * 19349663) % 1000

    for threshold, wall_descriptor in REGISTERED_WALL_TYPES:
        if hash_value < threshold:
            return wall_descriptor

    return WALL_TYPE_STANDARD