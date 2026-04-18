"""Procedural maze + markers: P R E V T d f X. Walls # corridors ."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

from .config import TILE


@dataclass
class LoadedMap:
    width: int
    height: int
    walls: List[Tuple[int, int]]
    floor: List[Tuple[int, int]]
    player_start: Tuple[float, float]
    robot_starts: List[Tuple[float, float]]
    keys: List[Tuple[int, int]]
    valves: List[Tuple[int, int]]
    terminals: List[Tuple[int, int]]
    evidence: List[Tuple[int, int]]
    exit_tile: Tuple[int, int]
    locked_doors: List[Tuple[int, int]]
    final_doors: List[Tuple[int, int]]


def _center(cx: int, cy: int) -> Tuple[float, float]:
    return (cx * TILE + TILE / 2, cy * TILE + TILE / 2)


def _generate_maze_grid(cells_x: int, cells_y: int, seed: int = 7) -> List[List[str]]:
    """DFS maze: cells are (cx,cy) 0..cells_x-1; output grid (2*cx+1, 2*cy+1) is floor."""
    rng = random.Random(seed)
    w = cells_x * 2 + 1
    h = cells_y * 2 + 1
    grid = [["#"] * w for _ in range(h)]
    vis = [[False] * cells_x for _ in range(cells_y)]

    def carve(cx: int, cy: int) -> None:
        vis[cy][cx] = True
        grid[cy * 2 + 1][cx * 2 + 1] = "."
        opts = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        rng.shuffle(opts)
        for dx, dy in opts:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cells_x and 0 <= ny < cells_y and not vis[ny][nx]:
                grid[cy * 2 + 1 + dy][cx * 2 + 1 + dx] = "."
                carve(nx, ny)

    carve(0, 0)
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = "#"
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = "#"
    return grid


def _place_spread(order: List[Tuple[int, int]], count: int, skip: set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Pick floor cells spread along BFS wave (skip taken)."""
    picks: List[Tuple[int, int]] = []
    n = len(order)
    if n < 4:
        return picks
    step = max(3, n // (count + 2))
    i = step
    while len(picks) < count and i < n:
        c = order[i]
        if c not in skip:
            picks.append(c)
            skip.add(c)
        i += step
    # fill if short
    j = n - 2
    while len(picks) < count and j > 0:
        c = order[j]
        if c not in skip:
            picks.append(c)
            skip.add(c)
        j -= 2
    return picks


def _open_cell(grid: List[List[str]], x: int, y: int, block: set[Tuple[int, int]]) -> bool:
    if (x, y) in block:
        return False
    c = grid[y][x]
    return c == "." or c == "P"


def _floor_neighbors(
    grid: List[List[str]], x: int, y: int, block: set[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    h, w = len(grid), len(grid[0])
    out: List[Tuple[int, int]] = []
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and _open_cell(grid, nx, ny, block):
            out.append((nx, ny))
    return out


def _maze_leaves(grid: List[List[str]], block: set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    h, w = len(grid), len(grid[0])
    leaves: List[Tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not _open_cell(grid, x, y, block):
                continue
            if len(_floor_neighbors(grid, x, y, block)) == 1:
                leaves.append((x, y))
    return leaves


def _bfs_order_blocked(
    grid: List[List[str]], sx: int, sy: int, block: set[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    h, w = len(grid), len(grid[0])
    if not _open_cell(grid, sx, sy, block):
        return []
    q = deque([(sx, sy)])
    seen = {(sx, sy)}
    out: List[Tuple[int, int]] = [(sx, sy)]
    while q:
        x, y = q.popleft()
        for nx, ny in _floor_neighbors(grid, x, y, block):
            if (nx, ny) not in seen:
                seen.add((nx, ny))
                out.append((nx, ny))
                q.append((nx, ny))
    return out


def _bfs_dist_from(
    grid: List[List[str]], sx: int, sy: int, block: set[Tuple[int, int]]
) -> dict[Tuple[int, int], int]:
    order = _bfs_order_blocked(grid, sx, sy, block)
    return {pos: i for i, pos in enumerate(order)}


def _build_raw_map() -> str:
    """DFS maze; d and f/X sit on dead-end tips so valves/files stay reachable."""
    cx, cy = 28, 14
    g = _generate_maze_grid(cx, cy, seed=11)
    if g[1][1] != ".":
        g[1][1] = "."
    g[1][1] = "P"

    leaves = _maze_leaves(g, set())
    dist = _bfs_dist_from(g, 1, 1, set())
    if not leaves:
        raise RuntimeError("no maze leaves")

    # Exit branch: farthest leaf; X at tip, f on its only corridor neighbor
    x_tile = max(leaves, key=lambda p: dist.get(p, 0))
    x_neighbors = _floor_neighbors(g, x_tile[0], x_tile[1], set())
    if len(x_neighbors) != 1:
        raise RuntimeError("exit leaf expected degree 1")
    f_tile = x_neighbors[0]

    # Red door: another leaf, moderate distance, not on exit branch
    exit_branch = {x_tile, f_tile}
    d_candidates = [
        p
        for p in leaves
        if p not in exit_branch and 8 <= dist.get(p, 0) <= 42
    ]
    if not d_candidates:
        d_candidates = [p for p in leaves if p not in exit_branch]
    d_tile = min(d_candidates, key=lambda p: abs(dist.get(p, 0) - 22))

    doors_block = {d_tile, f_tile, x_tile}
    order = _bfs_order_blocked(g, 1, 1, doors_block)
    if len(order) < 40:
        raise RuntimeError("playable region too small after door placement")

    used: set[Tuple[int, int]] = {(1, 1), d_tile, f_tile, x_tile}

    g[d_tile[1]][d_tile[0]] = "d"
    g[f_tile[1]][f_tile[0]] = "f"
    g[x_tile[1]][x_tile[0]] = "X"

    def grab(count: int) -> List[Tuple[int, int]]:
        picks = _place_spread(order, count, set(used))
        for p in picks:
            used.add(p)
        return picks

    for vx, vy in grab(3):
        g[vy][vx] = "V"
    for ex, ey in grab(5):
        g[ey][ex] = "E"
    for rx, ry in grab(5):
        g[ry][rx] = "R"

    placed_t = False
    ti = min(len(order) * 52 // 100, len(order) - 2)
    for j in range(ti, len(order)):
        tx, ty = order[j]
        if (tx, ty) not in used:
            g[ty][tx] = "T"
            used.add((tx, ty))
            placed_t = True
            break
    if not placed_t:
        raise RuntimeError("cannot place terminal")

    return "\n".join("".join(row) for row in g)


RAW_MAP = _build_raw_map()


def load_map() -> LoadedMap:
    lines = [ln for ln in RAW_MAP.splitlines() if ln.strip()]
    height = len(lines)
    width = max(len(row) for row in lines)
    walls: List[Tuple[int, int]] = []
    floor: List[Tuple[int, int]] = []
    player_start = (TILE * 2.5, TILE * 2.5)
    robot_starts: List[Tuple[float, float]] = []
    keys: List[Tuple[int, int]] = []
    valves: List[Tuple[int, int]] = []
    terminals: List[Tuple[int, int]] = []
    evidence: List[Tuple[int, int]] = []
    exit_tile = (width - 2, height - 2)
    locked_doors: List[Tuple[int, int]] = []
    final_doors: List[Tuple[int, int]] = []

    for y, row in enumerate(lines):
        for x in range(width):
            ch = row[x] if x < len(row) else "#"
            if ch == "#":
                walls.append((x, y))
            elif ch == "d":
                floor.append((x, y))
                locked_doors.append((x, y))
            elif ch == "f":
                floor.append((x, y))
                final_doors.append((x, y))
            else:
                floor.append((x, y))
                if ch == "P":
                    player_start = _center(x, y)
                elif ch == "R":
                    robot_starts.append(_center(x, y))
                elif ch == "K":
                    keys.append((x, y))
                elif ch == "V":
                    valves.append((x, y))
                elif ch == "T":
                    terminals.append((x, y))
                elif ch == "E":
                    evidence.append((x, y))
                elif ch == "X":
                    exit_tile = (x, y)

    return LoadedMap(
        width=width,
        height=height,
        walls=walls,
        floor=floor,
        player_start=player_start,
        robot_starts=robot_starts[:5],
        keys=keys,
        valves=valves,
        terminals=terminals,
        evidence=evidence,
        exit_tile=exit_tile,
        locked_doors=locked_doors,
        final_doors=final_doors,
    )
