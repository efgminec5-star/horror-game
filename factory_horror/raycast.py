"""DDA raycast on a tile grid. Player position in world pixels; grid cells TILE wide."""

from __future__ import annotations

import math
from typing import Callable, Tuple

DistSide = Tuple[float, int, int, int]  # world distance, side 0=x 1=y, tile x, tile y


def cast_ray(
    px: float,
    py: float,
    angle: float,
    tile: int,
    is_wall: Callable[[int, int], bool],
    map_w_tiles: int,
    map_h_tiles: int,
) -> DistSide:
    pos_x = px / tile
    pos_y = py / tile
    ray_dir_x = math.cos(angle)
    ray_dir_y = math.sin(angle)

    map_x = int(pos_x)
    map_y = int(pos_y)

    delta_dist_x = float("inf") if abs(ray_dir_x) < 1e-9 else abs(1.0 / ray_dir_x)
    delta_dist_y = float("inf") if abs(ray_dir_y) < 1e-9 else abs(1.0 / ray_dir_y)

    if ray_dir_x < 0:
        step_x = -1
        side_dist_x = (pos_x - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - pos_x) * delta_dist_x

    if ray_dir_y < 0:
        step_y = -1
        side_dist_y = (pos_y - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - pos_y) * delta_dist_y

    side = 0
    max_depth = max(map_w_tiles, map_h_tiles) * 2 + 5
    for _ in range(max_depth):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if map_x < 0 or map_y < 0 or map_x >= map_w_tiles or map_y >= map_h_tiles:
            d = max(map_w_tiles, map_h_tiles) * tile * 2.0
            return (d, side, max(0, map_x), max(0, map_y))

        if is_wall(map_x, map_y):
            if side == 0:
                perp = (map_x - pos_x + (1 - step_x) / 2.0) / ray_dir_x
            else:
                perp = (map_y - pos_y + (1 - step_y) / 2.0) / ray_dir_y
            perp_dist = abs(perp) * tile
            return (perp_dist, side, map_x, map_y)

    return (max(map_w_tiles, map_h_tiles) * tile * 2.0, side, map_x, map_y)
