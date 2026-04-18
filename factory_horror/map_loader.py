"""Factory layout: # wall, . floor, P start, R robot, K key, V valve, T terminal, E evidence, X exit, d key-door, f final-door."""

from __future__ import annotations

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


RAW_MAP = """
############################
#P........#......R.........#
#.#####.d.#...#######......#
#.....#...#...#.....#..K...#
###...#...#...#.V...#......#
#.....#...#...#.....####...#
#.R...#...#...#..T.........#
#.....#...#...#.....####...#
#####.#...#...#######..#...#
#.....#...#...........E#...#
#.E...#...#############....#
#.....#................#...#
#..V..#......R........E#...#
#.....#................#...#
#.....################f#...#
#......................#..X#
############################
""".strip("\n")


def _center(cx: int, cy: int) -> Tuple[float, float]:
    return (cx * TILE + TILE / 2, cy * TILE + TILE / 2)


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
        robot_starts=robot_starts[:3],
        keys=keys,
        valves=valves,
        terminals=terminals,
        evidence=evidence,
        exit_tile=exit_tile,
        locked_doors=locked_doors,
        final_doors=final_doors,
    )
