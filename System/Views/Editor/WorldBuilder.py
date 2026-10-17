from __future__ import annotations

import math
from collections import deque

import numpy

# Tile Collision Detection

def check_tile_collision(
        point_x:    float,
        point_z:    float,
        radius:     float,
        grid:       numpy.ndarray,
        cell_scale: float,
        dimension:  int
    ) -> bool:

    minimum_grid_x = int(math.floor((point_x - radius) / cell_scale))
    maximum_grid_x = int(math.floor((point_x + radius) / cell_scale))
    minimum_grid_z = int(math.floor((point_z - radius) / cell_scale))
    maximum_grid_z = int(math.floor((point_z + radius) / cell_scale))

    for grid_x in range(minimum_grid_x, maximum_grid_x + 1):
        for grid_z in range(minimum_grid_z, maximum_grid_z + 1):
            if not (0 <= grid_x < dimension and 0 <= grid_z < dimension):
                continue

            if grid[grid_x, grid_z] != 1:
                continue

            closest_x = max(grid_x * cell_scale, min(point_x, (grid_x + 1) * cell_scale))
            closest_z = max(grid_z * cell_scale, min(point_z, (grid_z + 1) * cell_scale))

            if (point_x - closest_x) ** 2 + (point_z - closest_z) ** 2 < radius * radius:
                return True

    return False

# Raycasting Line of Sight

def test_line_of_sight(
        point_source: numpy.ndarray,
        point_target: numpy.ndarray,
        grid:         numpy.ndarray,
        cell_scale:   float,
        dimension:    int
    ) -> bool:

    delta_x        = point_target[0] - point_source[0]
    delta_z        = point_target[2] - point_source[2]
    total_distance = math.hypot(delta_x, delta_z)

    if total_distance > 28.0:
        return False

    ray_steps = max(2, int(total_distance / 0.35))

    for step_index in range(1, ray_steps):
        interpolation = step_index / float(ray_steps)
        current_x     = point_source[0] + delta_x * interpolation
        current_z     = point_source[2] + delta_z * interpolation

        grid_x = int(current_x / cell_scale)
        grid_z = int(current_z / cell_scale)

        if not (0 <= grid_x < dimension and 0 <= grid_z < dimension):
            continue

        if grid[grid_x, grid_z] == 1:
            return False

    return True

# Grid Breadth First Search

def find_shortest_grid_path(
        start_position:  numpy.ndarray,
        target_position: numpy.ndarray,
        grid:            numpy.ndarray,
        cell_scale:      float,
        dimension:       int
    ) -> list[tuple[int, int]]:

    start_grid_x  = max(0, min(dimension - 1, int(start_position[0] / cell_scale)))
    start_grid_z  = max(0, min(dimension - 1, int(start_position[2] / cell_scale)))
    target_grid_x = max(0, min(dimension - 1, int(target_position[0] / cell_scale)))
    target_grid_z = max(0, min(dimension - 1, int(target_position[2] / cell_scale)))

    if start_grid_x == target_grid_x and start_grid_z == target_grid_z:
        return [(target_grid_x, target_grid_z)]

    if grid[target_grid_x, target_grid_z] == 1:
        nearest_free_tile = None

        for radius_ring in range(1, 4):
            for offset_x in range(-radius_ring, radius_ring + 1):
                for offset_z in range(-radius_ring, radius_ring + 1):
                    neighbor_x = target_grid_x + offset_x
                    neighbor_z = target_grid_z + offset_z

                    if 0 <= neighbor_x < dimension and 0 <= neighbor_z < dimension:
                        if grid[neighbor_x, neighbor_z] == 0:
                            nearest_free_tile = (neighbor_x, neighbor_z)
                            break

                if nearest_free_tile is not None:
                    break

            if nearest_free_tile is not None:
                break

        if nearest_free_tile is not None:
            target_grid_x, target_grid_z = nearest_free_tile

        else:
            return []

    frontier_queue      = deque([(start_grid_x, start_grid_z)])
    came_from_map       = {(start_grid_x, start_grid_z): None}
    path_found          = False
    cardinal_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    while frontier_queue:
        current_x, current_z = frontier_queue.popleft()

        if current_x == target_grid_x and current_z == target_grid_z:
            path_found = True
            break

        for direction_x, direction_z in cardinal_directions:
            next_x = current_x + direction_x
            next_z = current_z + direction_z

            if not (0 <= next_x < dimension and 0 <= next_z < dimension):
                continue

            if grid[next_x, next_z] == 0 and (next_x, next_z) not in came_from_map:
                came_from_map[(next_x, next_z)] = (current_x, current_z)
                frontier_queue.append((next_x, next_z))

    if not path_found:
        return []

    reconstructed_path = []
    crawl_pointer      = (target_grid_x, target_grid_z)

    while crawl_pointer is not None:
        reconstructed_path.append(crawl_pointer)
        crawl_pointer = came_from_map[crawl_pointer]

    reconstructed_path.reverse()

    if len(reconstructed_path) > 1 and reconstructed_path[0] == (start_grid_x, start_grid_z):
        reconstructed_path.pop(0)

    return reconstructed_path