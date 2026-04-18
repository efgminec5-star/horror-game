"""Factory layout: # wall, . floor, P start, R robot, V valve, T terminal, E evidence, X exit, d first-door, f final-door."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .config import TILE

# Core layout (28 wide); expanded at load time for a larger play area
_BASE_RAW = """
############################
#P..E..E..#......R.........#
#.#####.d.#...#######......#
#.....#...#...#.....#......#
###...#...#...#.V...#......#
#.....#...#...#.....####...#
#.R...#...#...#..T.........#
#.....#...#...#.....####...#
#####.#...#...#######..#...#
#.....#...#............#...#
#.....#...#############....#
#.....#................#...#
#..V..#......R........E#...#
#.....#................#...#
#.....################f#...#
#.........................X#
############################
""".strip("\n")

# Total map width after padding (must be >= len(base inner) + 2)
MAP_WIDTH = 66
# Insert this many extra horizontal slices (duplicate one open row) for more vertical space
EXTRA_FLOOR_SLICES = 14
# 0-based index of base row to duplicate (spacious hall; no extra pickups)
_EXTRA_ROW_TEMPLATE_INDEX = 10


def _expand_base_map() -> str:
    base = [ln for ln in _BASE_RAW.splitlines() if ln.strip()]
    wide: List[str] = []
    for row in base:
        if len(row) < 2 or row[0] != "#" or row[-1] != "#":
            raise ValueError(f"Bad map row: {row!r}")
        inner = row[1:-1]
        pad = MAP_WIDTH - 2 - len(inner)
        if pad < 0:
            raise ValueError(f"MAP_WIDTH {MAP_WIDTH} too small for inner len {len(inner)}")
        wide.append("#" + inner + "." * pad + "#")

    tpl = wide[_EXTRA_ROW_TEMPLATE_INDEX]
    head = wide[: _EXTRA_ROW_TEMPLATE_INDEX + 1]
    tail = wide[_EXTRA_ROW_TEMPLATE_INDEX + 1 :]
    out = head + [tpl] * EXTRA_FLOOR_SLICES + tail
    if not all(len(r) == MAP_WIDTH for r in out):
        raise AssertionError("width mismatch")
    return "\n".join(out)


RAW_MAP = _expand_base_map()


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
