from __future__ import annotations

import math
from enum import Enum, auto
from typing import Set, Tuple

import pygame

from .config import (
    ACCENT,
    BG_DARK,
    DOOR_LOCKED,
    DOOR_OPEN,
    FLASHLIGHT_EDGE_ALPHA,
    FLASHLIGHT_RADIUS,
    FPS,
    ROBOT_CATCH_DIST,
    SCREEN_H,
    SCREEN_W,
    TILE,
    TITLE,
    FLOOR,
    FLOOR_ALT,
    WALL,
    WALL_EDGE,
    PLAYER_RADIUS,
    ROBOT_RADIUS,
)
from .entities import Player, Robot
from .map_loader import LoadedMap, load_map


class State(Enum):
    PLAYING = auto()
    CAUGHT = auto()
    WON = auto()
    INTRO = auto()


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.map_data: LoadedMap = load_map()
        self._reset_world()

    def _reset_world(self):
        m = self.map_data
        self.walls: Set[Tuple[int, int]] = set(m.walls)
        self.locked_doors: Set[Tuple[int, int]] = set(m.locked_doors)
        self.final_doors: Set[Tuple[int, int]] = set(m.final_doors)
        self.player = Player(m.player_start[0], m.player_start[1])
        self.robots = [Robot(rx, ry) for rx, ry in m.robot_starts]
        while len(self.robots) < 3:
            self.robots.append(
                Robot(m.player_start[0] + 140, m.player_start[1] + 100)
            )
        self.has_key = False
        self.evidence_count = 0
        self.valve_a = False
        self.valve_b = False
        self.terminal_on = False
        self.keys_world = list(m.keys)
        self.valves = list(m.valves)
        self.terminals = list(m.terminals)
        self.evidence_tiles = list(m.evidence)
        self.state = State.INTRO

    def _blocking_tiles(self) -> Set[Tuple[int, int]]:
        return self.walls | self.locked_doors | self.final_doors

    def _try_interact(self):
        px, py = self.player.x, self.player.y
        reach = TILE * 1.15
        candidates = []

        for i, (tx, ty) in enumerate(self.keys_world):
            cx, cy = tx * TILE + TILE / 2, ty * TILE + TILE / 2
            d = math.hypot(px - cx, py - cy)
            if d < reach:
                candidates.append((d, "key", i))

        for j, (vx, vy) in enumerate(self.valves):
            cx, cy = vx * TILE + TILE / 2, vy * TILE + TILE / 2
            d = math.hypot(px - cx, py - cy)
            if d < reach:
                candidates.append((d, "valve", j))

        for dpos in self.locked_doors:
            cx, cy = dpos[0] * TILE + TILE / 2, dpos[1] * TILE + TILE / 2
            dist = math.hypot(px - cx, py - cy)
            if dist < reach and self.has_key:
                candidates.append((dist, "lock", dpos))

        for dpos in self.final_doors:
            cx, cy = dpos[0] * TILE + TILE / 2, dpos[1] * TILE + TILE / 2
            dist = math.hypot(px - cx, py - cy)
            if dist < reach and self.evidence_count >= 3:
                candidates.append((dist, "final", dpos))

        for i, (ex, ey) in enumerate(self.evidence_tiles):
            cx, cy = ex * TILE + TILE / 2, ey * TILE + TILE / 2
            d = math.hypot(px - cx, py - cy)
            if d < reach:
                candidates.append((d, "evidence", i))

        if not candidates:
            return
        candidates.sort(key=lambda t: t[0])
        _, kind, payload = candidates[0]

        if kind == "key":
            self.has_key = True
            self.keys_world.pop(payload)
        elif kind == "valve":
            if payload == 0:
                self.valve_a = not self.valve_a
            else:
                self.valve_b = not self.valve_b
            self.terminal_on = self.valve_a and self.valve_b
        elif kind == "lock":
            self.locked_doors.discard(payload)
            self.has_key = False
        elif kind == "final":
            self.final_doors.discard(payload)
        elif kind == "evidence":
            self.evidence_tiles.pop(payload)
            self.evidence_count += 1

    def _check_exit(self) -> bool:
        ex, ey = self.map_data.exit_tile
        cx, cy = ex * TILE + TILE / 2, ey * TILE + TILE / 2
        return math.hypot(self.player.x - cx, self.player.y - cy) < TILE * 0.45

    def _check_caught(self) -> bool:
        for r in self.robots:
            if math.hypot(self.player.x - r.x, self.player.y - r.y) < ROBOT_CATCH_DIST:
                return True
        return False

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_e and self.state == State.PLAYING:
                        self._try_interact()
                    if event.key == pygame.K_r and self.state in (State.CAUGHT, State.WON):
                        self._reset_world()
                        self.state = State.INTRO
                    if event.key == pygame.K_RETURN and self.state == State.INTRO:
                        self.state = State.PLAYING

            keys = pygame.key.get_pressed()

            if self.state == State.PLAYING:
                block = self._blocking_tiles()
                player_moved = self.player.update(dt, block, keys)
                if player_moved:
                    for r in self.robots:
                        r.step_toward(self.player.x, self.player.y, dt, block)
                if self._check_caught():
                    self.state = State.CAUGHT
                elif self._check_exit() and self.evidence_count >= 3:
                    self.state = State.WON

            self._draw()
            pygame.display.flip()

    def _draw(self):
        self.screen.fill(BG_DARK)
        m = self.map_data
        cam_x = self.player.x - SCREEN_W / 2
        cam_y = self.player.y - SCREEN_H / 2
        world_w = m.width * TILE
        world_h = m.height * TILE
        cam_x = max(0, min(cam_x, world_w - SCREEN_W))
        cam_y = max(0, min(cam_y, world_h - SCREEN_H))

        def w2s(wx: float, wy: float) -> Tuple[float, float]:
            return wx - cam_x, wy - cam_y

        # tiles
        for (tx, ty) in m.floor:
            sx, sy = w2s(tx * TILE, ty * TILE)
            if sx < -TILE or sy < -TILE or sx > SCREEN_W or sy > SCREEN_H:
                continue
            col = FLOOR if (tx + ty) % 2 == 0 else FLOOR_ALT
            pygame.draw.rect(self.screen, col, (sx, sy, TILE + 1, TILE + 1))
            pygame.draw.rect(self.screen, (28, 30, 34), (sx, sy, TILE + 1, TILE + 1), 1)

        for (tx, ty) in self.walls:
            sx, sy = w2s(tx * TILE, ty * TILE)
            pygame.draw.rect(self.screen, WALL, (sx, sy, TILE + 1, TILE + 1))
            pygame.draw.rect(self.screen, WALL_EDGE, (sx + 2, sy + 2, TILE - 3, TILE - 3), 1)

        for (tx, ty) in self.locked_doors:
            sx, sy = w2s(tx * TILE, ty * TILE)
            pygame.draw.rect(self.screen, DOOR_LOCKED, (sx, sy, TILE + 1, TILE + 1))

        for (tx, ty) in self.final_doors:
            sx, sy = w2s(tx * TILE, ty * TILE)
            c = DOOR_LOCKED if self.evidence_count < 3 else DOOR_OPEN
            pygame.draw.rect(self.screen, c, (sx, sy, TILE + 1, TILE + 1))

        # pickups / puzzle objects
        for tx, ty in self.keys_world:
            sx, sy = w2s(tx * TILE + TILE / 2, ty * TILE + TILE / 2)
            pygame.draw.circle(self.screen, (200, 180, 60), (int(sx), int(sy)), 8)

        for i, (vx, vy) in enumerate(self.valves):
            sx, sy = w2s(vx * TILE + TILE / 2, vy * TILE + TILE / 2)
            on = self.valve_a if i == 0 else self.valve_b
            pygame.draw.circle(self.screen, (80, 140, 200) if on else (60, 70, 90), (int(sx), int(sy)), 10)

        for tx, ty in self.terminals:
            sx, sy = w2s(tx * TILE + TILE / 2, ty * TILE + TILE / 2)
            col = (100, 220, 120) if self.terminal_on else (70, 75, 80)
            pygame.draw.rect(self.screen, col, (sx - 14, sy - 10, 28, 20))

        for tx, ty in self.evidence_tiles:
            sx, sy = w2s(tx * TILE + TILE / 2, ty * TILE + TILE / 2)
            pygame.draw.rect(self.screen, (160, 140, 200), (sx - 10, sy - 8, 20, 16))

        ex, ey = m.exit_tile
        esx, esy = w2s(ex * TILE + TILE / 2, ey * TILE + TILE / 2)
        pygame.draw.rect(self.screen, (50, 90, 70), (esx - 12, esy - 18, 24, 36))

        # robots
        for r in self.robots:
            sx, sy = w2s(r.x, r.y)
            pygame.draw.circle(self.screen, (35, 38, 45), (int(sx), int(sy)), ROBOT_RADIUS + 2)
            pygame.draw.circle(self.screen, ACCENT, (int(sx), int(sy)), ROBOT_RADIUS)
            pygame.draw.circle(self.screen, (255, 80, 60), (int(sx - 5), int(sy - 3)), 4)
            pygame.draw.circle(self.screen, (255, 80, 60), (int(sx + 5), int(sy - 3)), 4)

        # player
        psx, psy = w2s(self.player.x, self.player.y)
        pygame.draw.circle(self.screen, (200, 205, 215), (int(psx), int(psy)), PLAYER_RADIUS)

        # Subtle vignette + bright center so the map stays readable (flash aims slightly with mouse)
        mx, my = int(psx), int(psy)
        mpos = pygame.mouse.get_pos()
        aim_dx = mpos[0] - psx
        aim_dy = mpos[1] - psy
        aim_len = math.hypot(aim_dx, aim_dy) or 1.0
        pull = min(48.0, FLASHLIGHT_RADIUS * 0.11)
        fx = int(mx + (aim_dx / aim_len) * pull)
        fy = int(my + (aim_dy / aim_len) * pull)

        dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dark.fill((0, 0, 0, FLASHLIGHT_EDGE_ALPHA))
        punch = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for rad in range(int(FLASHLIGHT_RADIUS), 0, -6):
            t = rad / FLASHLIGHT_RADIUS
            # Stronger subtract near center = clearer middle of screen
            a = min(255, FLASHLIGHT_EDGE_ALPHA + 50 + int(160 * (1.0 - t) ** 1.2))
            pygame.draw.circle(punch, (255, 255, 255, a), (fx, fy), rad)
        dark.blit(punch, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        self.screen.blit(dark, (0, 0))

        # UI
        if self.state == State.INTRO:
            lines = [
                "THE EMPTY SHIFT",
                "",
                "You are searching an abandoned packaging plant for Elias Crane,",
                "missing six months. The night shift left recordings of 'statues' in the aisles.",
                "",
                "MOVE: WASD   LOOK: mouse (flashlight)   INTERACT: E   ESC: quit",
                "ROBOTS only crawl toward you while YOU are moving. Stand still to think.",
                "",
                "PUZZLES: find the maintenance KEY (gold), open the RED door (E at door).",
                "Power the CONTROL ROOM: toggle BOTH blue VALVES, then the terminal lights green.",
                "Collect 3 FILES (violet) on Elias, open the FINAL door, reach the EXIT (green).",
                "",
                "Press ENTER to begin.",
            ]
            y = 80
            for ln in lines:
                surf = self.font.render(ln, True, (220, 220, 225))
                self.screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))
                y += 28
        else:
            hud = [
                f"Evidence files: {self.evidence_count}/3",
                f"Key: {'yes' if self.has_key else 'no'}",
                f"Power: {'both valves OK' if self.valve_a and self.valve_b else 'align valves'}",
            ]
            yy = 8
            for h in hud:
                self.screen.blit(self.font_small.render(h, True, (200, 200, 205)), (12, yy))
                yy += 22

        if self.state == State.CAUGHT:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((80, 0, 0, 200))
            self.screen.blit(ov, (0, 0))
            t = self.font.render("They only move when you do. You moved once too often.", True, (255, 255, 255))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 - 20))
            t2 = self.font_small.render("R — try again   ESC — quit", True, (230, 230, 230))
            self.screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, SCREEN_H // 2 + 20))

        if self.state == State.WON:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 40, 30, 210))
            self.screen.blit(ov, (0, 0))
            t = self.font.render("You reached the loading dock with the files. Elias was here.", True, (200, 255, 220))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 - 20))
            t2 = self.font_small.render("R — play again   ESC — quit", True, (220, 240, 230))
            self.screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, SCREEN_H // 2 + 20))

def main():
    Game().run()
    pygame.quit()
