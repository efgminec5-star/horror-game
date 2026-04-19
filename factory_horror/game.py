from __future__ import annotations

import array
import math
from enum import Enum, auto
from typing import List, Optional, Set, Tuple

import pygame

from .config import (
    ACCENT,
    BG_DARK,
    DOOR_LOCKED,
    DOOR_OPEN,
    FIRST_DOOR_FILES_NEEDED,
    TOTAL_EVIDENCE_FILES,
    FLASHLIGHT_EDGE_ALPHA,
    FLASHLIGHT_FALLOFF,
    FLASHLIGHT_RADIUS,
    FOV_RAD,
    FPS,
    RAY_STRIDE,
    ROBOT_CATCH_DIST,
    ROBOT_LEAD_MAX_SEC,
    ROBOT_SPEED,
    ROBOT_SPEED_MULT_MAX,
    ROBOT_SUBSTEP_AGGRO_THRESHOLD,
    SCREEN_H,
    SCREEN_W,
    TILE,
    TITLE,
    WALL,
)
from .entities import Player, Robot
from .map_loader import LoadedMap, load_map
from .raycast import cast_ray


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
        self.player = Player(m.player_start[0], m.player_start[1], angle=0.0)
        self.robots = [Robot(rx, ry) for rx, ry in m.robot_starts]
        while len(self.robots) < 5:
            self.robots.append(
                Robot(m.player_start[0] + 140, m.player_start[1] + 100)
            )
        self.evidence_count = 0
        self.valve_a = False
        self.valve_b = False
        self.valve_c = False
        self.terminal_on = False
        self.valves = list(m.valves)
        self.terminals = list(m.terminals)
        self.evidence_tiles = list(m.evidence)
        self.state = State.INTRO
        self._caught_at_ms: Optional[int] = None

    def _blocking_tiles(self) -> Set[Tuple[int, int]]:
        return self.walls | self.locked_doors | self.final_doors

    def _is_wall_tile(self, tx: int, ty: int) -> bool:
        return (tx, ty) in self._blocking_tiles()

    def _can_open_first_door(self) -> bool:
        return self.terminal_on and self.evidence_count >= FIRST_DOOR_FILES_NEEDED

    def _can_rescue(self) -> bool:
        return self.terminal_on and self.evidence_count >= TOTAL_EVIDENCE_FILES

    def _robot_aggro(self) -> float:
        ev = self.evidence_count / float(max(TOTAL_EVIDENCE_FILES, 1))
        valves = (
            int(self.valve_a) + int(self.valve_b) + int(self.valve_c)
        ) / 3.0
        return min(1.0, 0.5 * ev + 0.5 * valves)

    def _forward_dot(self, wx: float, wy: float) -> float:
        fx = math.cos(self.player.angle)
        fy = math.sin(self.player.angle)
        dx, dy = wx - self.player.x, wy - self.player.y
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return -1.0
        return (dx / d) * fx + (dy / d) * fy

    def _try_interact(self):
        px, py = self.player.x, self.player.y
        reach = TILE * 2.2
        min_dot = 0.28

        def nearest_tile(positions: Set[Tuple[int, int]]) -> Tuple[int, int] | None:
            best: Tuple[int, int] | None = None
            best_d = 1e9
            for tx, ty in positions:
                cx, cy = tx * TILE + TILE / 2, ty * TILE + TILE / 2
                d = math.hypot(px - cx, py - cy)
                if d < reach and d < best_d and self._forward_dot(cx, cy) >= min_dot:
                    best_d = d
                    best = (tx, ty)
            return best

        if self._can_open_first_door():
            dpos = nearest_tile(self.locked_doors)
            if dpos is not None:
                self.locked_doors.discard(dpos)
                return

        if self._can_rescue():
            dpos = nearest_tile(self.final_doors)
            if dpos is not None:
                self.final_doors.discard(dpos)
                return

        candidates = []

        for j, (vx, vy) in enumerate(self.valves):
            cx, cy = vx * TILE + TILE / 2, vy * TILE + TILE / 2
            d = math.hypot(px - cx, py - cy)
            if d < reach and self._forward_dot(cx, cy) >= min_dot:
                candidates.append((d, "valve", j))

        for i, (ex, ey) in enumerate(self.evidence_tiles):
            cx, cy = ex * TILE + TILE / 2, ey * TILE + TILE / 2
            d = math.hypot(px - cx, py - cy)
            if d < reach and self._forward_dot(cx, cy) >= min_dot:
                candidates.append((d, "evidence", i))

        if not candidates:
            return
        candidates.sort(key=lambda t: t[0])
        _, kind, payload = candidates[0]

        if kind == "valve":
            if payload == 0:
                self.valve_a = not self.valve_a
            elif payload == 1:
                self.valve_b = not self.valve_b
            else:
                self.valve_c = not self.valve_c
            self.terminal_on = self.valve_a and self.valve_b and self.valve_c
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

    def _play_jumpscare_sting(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 1, 512)
        except pygame.error:
            return
        rate = 44100
        ms = 260
        n = int(rate * ms / 1000)
        buf = array.array("h")
        for i in range(n):
            t = i / rate
            u = i / max(n - 1, 1)
            f = 680.0 * (1.0 - u) + 70.0 * u
            env = math.sin(math.pi * u) ** 0.4
            s = math.sin(2 * math.pi * f * t) * env
            s += 0.2 * math.sin(2 * math.pi * (2000.0 - 1500.0 * u) * t) * env
            v = int(24000 * s)
            buf.append(max(-32767, min(32767, v)))
        try:
            snd = pygame.mixer.Sound(buffer=buf.tobytes())
            snd.set_volume(0.72)
            snd.play()
        except (ValueError, pygame.error):
            pass

    def _draw_jumpscare_face(self, phase_ms: int) -> None:
        """Close-up robot head; phase_ms is time since this segment began."""
        t = min(1.0, phase_ms / 380.0)
        decay = 1.0 - t
        shake = int(22 * decay * math.sin(phase_ms * 0.11))
        shake_y = int(16 * decay * math.cos(phase_ms * 0.09))
        ox = SCREEN_W // 2 + shake
        oy = SCREEN_H // 2 + shake_y

        self.screen.fill((14, 10, 12))
        split = max(3, int(10 * (0.35 + decay)))

        hw = int(SCREEN_W * 0.74)
        hh = int(SCREEN_H * 0.52)
        hx = ox - hw // 2
        hy = oy - hh // 2 - int(SCREEN_H * 0.06)
        base = pygame.Rect(hx, hy, hw, hh)

        pygame.draw.ellipse(self.screen, (160, 35, 38), base.move(-split, 0), max(2, split // 2))
        pygame.draw.ellipse(self.screen, (32, 42, 170), base.move(split, 0), max(2, split // 2))
        pygame.draw.ellipse(self.screen, (36, 38, 46), base)
        pygame.draw.ellipse(self.screen, (26, 28, 34), base.inflate(-14, -10))
        pygame.draw.ellipse(self.screen, (18, 20, 26), base.inflate(-14, -10), 2)

        eye_glow = (255, 210, 120) if t < 0.55 else (255, 85, 45)
        ew = max(28, SCREEN_W // 13)
        eh = max(22, SCREEN_H // 26)
        eg = max(8, ew // 2)
        band_w = 3 * ew + 2 * eg
        ex0 = ox - band_w // 2
        eye_y = hy + hh // 2 - eh // 2
        for i in range(3):
            er = pygame.Rect(ex0 + i * (ew + eg), eye_y, ew, eh)
            pygame.draw.rect(self.screen, (eye_glow[0] // 5, eye_glow[1] // 5, eye_glow[2] // 5), er.inflate(14, 10))
            pygame.draw.rect(self.screen, eye_glow, er)
            pygame.draw.rect(self.screen, (40, 20, 18), er, 2)

        scan = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for row in range(0, SCREEN_H, 3):
            a = min(55, int(18 + abs(row - SCREEN_H // 2) * 0.12))
            pygame.draw.line(scan, (0, 0, 0, a), (0, row), (SCREEN_W, row))
        self.screen.blit(scan, (0, 0))
        ve = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        bar_x = SCREEN_W // 5
        bar_y = SCREEN_H // 7
        pygame.draw.rect(ve, (0, 0, 0, 125), (0, 0, bar_x, SCREEN_H))
        pygame.draw.rect(ve, (0, 0, 0, 125), (SCREEN_W - bar_x, 0, bar_x, SCREEN_H))
        pygame.draw.rect(ve, (0, 0, 0, 95), (0, 0, SCREEN_W, bar_y))
        pygame.draw.rect(ve, (0, 0, 0, 95), (0, SCREEN_H - bar_y, SCREEN_W, bar_y))
        self.screen.blit(ve, (0, 0))

    def _wall_rgb(self, tx: int, ty: int, side: int, dist: float) -> Tuple[int, int, int]:
        if (tx, ty) in self.locked_doors:
            base = DOOR_OPEN if self._can_open_first_door() else DOOR_LOCKED
        elif (tx, ty) in self.final_doors:
            base = DOOR_OPEN if self._can_rescue() else DOOR_LOCKED
        else:
            base = WALL
        shade = max(0.36, 1.0 - dist / (TILE * 34.0))
        if side == 1:
            shade *= 0.84
        return (
            int(base[0] * shade),
            int(base[1] * shade),
            int(base[2] * shade),
        )

    def _draw_sprites(self, proj: float, aggro: float) -> None:
        px, py = self.player.x, self.player.y
        ca = math.cos(self.player.angle)
        sa = math.sin(self.player.angle)

        def _lerp(c1: Tuple[int, int, int], c2: Tuple[int, int, int], u: float) -> Tuple[int, int, int]:
            return (
                int(c1[0] + (c2[0] - c1[0]) * u),
                int(c1[1] + (c2[1] - c1[1]) * u),
                int(c1[2] + (c2[2] - c1[2]) * u),
            )

        sprites: List[Tuple[float, float, float, Tuple[int, int, int], int]] = []
        for i, (vx, vy) in enumerate(self.valves):
            sx = vx * TILE + TILE / 2
            sy = vy * TILE + TILE / 2
            on = (self.valve_a, self.valve_b, self.valve_c)[i] if i < 3 else False
            col = (80, 140, 200) if on else (60, 70, 90)
            sprites.append((sx, sy, TILE * 0.55, col, 0))

        for tx, ty in self.terminals:
            sx = tx * TILE + TILE / 2
            sy = ty * TILE + TILE / 2
            col = (100, 220, 120) if self.terminal_on else (70, 75, 80)
            sprites.append((sx, sy, TILE * 0.5, col, 0))

        for tx, ty in self.evidence_tiles:
            sx = tx * TILE + TILE / 2
            sy = ty * TILE + TILE / 2
            sprites.append((sx, sy, TILE * 0.5, (160, 140, 200), 0))

        ex, ey = self.map_data.exit_tile
        sprites.append(
            (ex * TILE + TILE / 2, ey * TILE + TILE / 2, TILE * 0.65, (50, 90, 70), 0)
        )

        shell = _lerp((35, 38, 45), (72, 28, 32), aggro)
        body = _lerp(ACCENT, (240, 55, 55), aggro)
        for r in self.robots:
            sprites.append((r.x, r.y, TILE * 0.64, body, 1))

        def depth_key(s):
            wx, wy, _, _, tag = s
            dx, dy = wx - px, wy - py
            return -(dx * ca + dy * sa)

        sprites.sort(key=depth_key)

        for wx, wy, spr_h, col, is_robot in sprites:
            dx = wx - px
            dy = wy - py
            depth = dx * ca + dy * sa
            if depth < TILE * 0.35:
                continue
            lat = -dx * sa + dy * ca
            screen_x = int(SCREEN_W / 2 + lat / depth * proj)
            h = int(spr_h / depth * proj)
            if h < 2 or screen_x < -h or screen_x > SCREEN_W + h:
                continue
            top = SCREEN_H // 2 - h // 2
            if is_robot:
                # Box head + thin torso + arms + legs (billboard)
                head_w = max(8, int(h * 0.58))
                head_h = max(5, int(h * 0.19))
                body_w = max(4, int(h * 0.30))
                torso_h = int(h * 0.40)
                leg_h = max(4, int(h * 0.17))
                leg_w = max(3, int(body_w * 0.42))
                leg_between = max(1, h // 55)
                gap = max(1, h // 45)
                leg_gap = max(1, h // 50)
                stack_h = head_h + gap + torso_h + leg_gap + leg_h
                oy = SCREEN_H // 2 - stack_h // 2
                hx = screen_x - head_w // 2

                head_rect = pygame.Rect(hx, oy, head_w, head_h)
                pygame.draw.ellipse(self.screen, shell, head_rect.inflate(4, 4))
                pygame.draw.ellipse(self.screen, (40, 42, 50), head_rect)
                pygame.draw.ellipse(self.screen, (26, 28, 34), head_rect, 1)

                eye_c = _lerp((255, 90, 55), (255, 220, 100), aggro)
                es = max(2, head_h // 2)
                ey = oy + head_h // 2 - es // 2
                eg = max(1, es // 2)
                eyes_w = 3 * es + 2 * eg
                x0 = hx + (head_w - eyes_w) // 2
                for i in range(3):
                    pygame.draw.rect(self.screen, eye_c, (x0 + i * (es + eg), ey, es, es))

                by = oy + head_h + gap
                bx = screen_x - body_w // 2
                arm_w = max(3, int(h * 0.085))
                arm_h = int(torso_h * 0.88)
                arm_y = by + int(torso_h * 0.06)
                arm_gap = max(1, h // 50)
                arm_dark = (max(0, col[0] - 35), max(0, col[1] - 12), max(0, col[2] - 12))
                j_r = max(3, int(h * 0.038))
                joint_fill = (50, 52, 60)
                joint_ring = (24, 26, 32)

                def _draw_arm_column(ax: int, ay: int) -> None:
                    rest = arm_h - j_r
                    up_h = max(2, int(rest * 0.48))
                    lo_h = max(2, rest - up_h)
                    up_rect = pygame.Rect(ax, ay, arm_w, up_h)
                    pygame.draw.ellipse(self.screen, shell, up_rect.inflate(2, 2))
                    pygame.draw.ellipse(self.screen, arm_dark, up_rect)
                    pygame.draw.ellipse(self.screen, joint_ring, up_rect, 1)
                    ecx, ecy = ax + arm_w // 2, ay + up_h + j_r // 2
                    pygame.draw.circle(self.screen, joint_fill, (ecx, ecy), j_r // 2)
                    pygame.draw.circle(self.screen, joint_ring, (ecx, ecy), j_r // 2, 1)
                    ly = ay + up_h + j_r
                    lo_rect = pygame.Rect(ax, ly, arm_w, lo_h)
                    pygame.draw.ellipse(self.screen, shell, lo_rect.inflate(2, 2))
                    pygame.draw.ellipse(self.screen, arm_dark, lo_rect)
                    pygame.draw.ellipse(self.screen, joint_ring, lo_rect, 1)

                _draw_arm_column(bx - arm_w - arm_gap, arm_y)
                _draw_arm_column(bx + body_w + arm_gap, arm_y)

                body_rect = pygame.Rect(bx, by, body_w, torso_h)
                pygame.draw.ellipse(self.screen, shell, body_rect.inflate(4, 4))
                pygame.draw.ellipse(self.screen, col, body_rect)
                spine_w = max(2, int(body_w * 0.38))
                spine_h = max(2, int(torso_h * 0.82))
                spine_rect = pygame.Rect(
                    screen_x - spine_w // 2,
                    by + max(1, torso_h // 12),
                    spine_w,
                    spine_h,
                )
                spine_shade = (
                    max(0, col[0] - 28),
                    max(0, col[1] - 18),
                    max(0, col[2] - 18),
                )
                pygame.draw.ellipse(self.screen, spine_shade, spine_rect)
                band = max(2, torso_h // 6)
                band_rect = pygame.Rect(bx, by + torso_h // 3, body_w, band)
                pygame.draw.ellipse(self.screen, (72, 22, 26), band_rect)
                pygame.draw.ellipse(self.screen, joint_ring, body_rect, 1)

                legs_top = by + torso_h + leg_gap
                span = leg_w * 2 + leg_between
                leg_x0 = screen_x - span // 2
                leg_col = (max(0, col[0] - 20), max(0, col[1] - 8), max(0, col[2] - 8))
                jk_r = max(3, int(h * 0.036))
                for i in range(2):
                    lx = leg_x0 + i * (leg_w + leg_between)
                    rem = leg_h - jk_r
                    th_h = max(2, int(rem * 0.52))
                    sh_h = max(2, rem - th_h)
                    th_rect = pygame.Rect(lx, legs_top, leg_w, th_h)
                    pygame.draw.ellipse(self.screen, shell, th_rect.inflate(2, 2))
                    pygame.draw.ellipse(self.screen, leg_col, th_rect)
                    pygame.draw.ellipse(self.screen, joint_ring, th_rect, 1)
                    kcx = lx + leg_w // 2
                    kcy = legs_top + th_h + jk_r // 2
                    pygame.draw.circle(self.screen, joint_fill, (kcx, kcy), jk_r // 2)
                    pygame.draw.circle(self.screen, joint_ring, (kcx, kcy), jk_r // 2, 1)
                    sy = legs_top + th_h + jk_r
                    sh_rect = pygame.Rect(lx, sy, leg_w, sh_h)
                    pygame.draw.ellipse(self.screen, shell, sh_rect.inflate(2, 2))
                    pygame.draw.ellipse(self.screen, leg_col, sh_rect)
                    pygame.draw.ellipse(self.screen, joint_ring, sh_rect, 1)
            else:
                pygame.draw.rect(self.screen, col, (screen_x - h // 2, top, h, h))

    def _draw_fps_world(self) -> None:
        m = self.map_data
        mw, mh = m.width, m.height
        px, py = self.player.x, self.player.y
        angle = self.player.angle

        half = SCREEN_H // 2
        pygame.draw.rect(self.screen, (10, 12, 18), (0, 0, SCREEN_W, half))
        pygame.draw.rect(self.screen, (18, 16, 14), (0, half, SCREEN_W, SCREEN_H - half))

        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        plane_x = -math.sin(angle) * math.tan(FOV_RAD / 2)
        plane_y = math.cos(angle) * math.tan(FOV_RAD / 2)
        proj = (SCREEN_W / 2) / math.tan(FOV_RAD / 2)

        for col in range(0, SCREEN_W, RAY_STRIDE):
            camera_x = 2 * col / float(SCREEN_W) - 1.0
            ray_dx = dir_x + plane_x * camera_x
            ray_dy = dir_y + plane_y * camera_x
            ray_angle = math.atan2(ray_dy, ray_dx)

            dist, side, mtx, mty = cast_ray(
                px,
                py,
                ray_angle,
                TILE,
                self._is_wall_tile,
                mw,
                mh,
            )
            rel = ray_angle - angle
            perp = dist * math.cos(rel)
            perp = max(perp, 0.001)
            line_h = int((TILE * proj) / perp)
            line_h = min(line_h, SCREEN_H * 2)
            top = SCREEN_H // 2 - line_h // 2
            rgb = self._wall_rgb(mtx, mty, side, dist)
            pygame.draw.rect(self.screen, rgb, (col, top, RAY_STRIDE, line_h))

        self._draw_sprites(proj, self._robot_aggro())

        dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dark.fill((0, 0, 0, FLASHLIGHT_EDGE_ALPHA))
        punch = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        for rad in range(int(FLASHLIGHT_RADIUS * 1.1), 0, -5):
            t = rad / max(FLASHLIGHT_RADIUS * 1.1, 1)
            a = min(
                255,
                FLASHLIGHT_EDGE_ALPHA + 40 + int(200 * (1.0 - t) ** FLASHLIGHT_FALLOFF),
            )
            pygame.draw.circle(punch, (255, 255, 255, a), (cx, cy), rad)
        dark.blit(punch, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        self.screen.blit(dark, (0, 0))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                        return
                    if event.key == pygame.K_e and self.state == State.PLAYING:
                        self._try_interact()
                    if event.key == pygame.K_r and self.state in (State.CAUGHT, State.WON):
                        self._reset_world()
                        self.state = State.INTRO
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    if event.key == pygame.K_RETURN and self.state == State.INTRO:
                        self.state = State.PLAYING
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                        pygame.mouse.get_rel()

            keys = pygame.key.get_pressed()

            if self.state == State.INTRO:
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)

            if self.state == State.PLAYING:
                mdx, _ = pygame.mouse.get_rel()
                block = self._blocking_tiles()
                self.player.update_fps(dt, block, keys, float(mdx), True)
                aggro = self._robot_aggro()
                speed = ROBOT_SPEED * (1.0 + aggro * (ROBOT_SPEED_MULT_MAX - 1.0))
                lead = aggro * ROBOT_LEAD_MAX_SEC
                tx = self.player.x + self.player.vel_x * lead
                ty = self.player.y + self.player.vel_y * lead
                substeps = 2 if aggro >= ROBOT_SUBSTEP_AGGRO_THRESHOLD else 1
                sub_dt = dt / substeps
                for _ in range(substeps):
                    for r in self.robots:
                        r.step_toward(tx, ty, sub_dt, block, speed)
                if self._check_caught():
                    self._play_jumpscare_sting()
                    self.state = State.CAUGHT
                    self._caught_at_ms = pygame.time.get_ticks()
                    pygame.event.set_grab(False)
                    pygame.mouse.set_visible(True)
                elif self._check_exit() and self._can_rescue():
                    self.state = State.WON
                    pygame.event.set_grab(False)
                    pygame.mouse.set_visible(True)

            self._draw()
            pygame.display.flip()

    def _draw(self):
        if self.state == State.CAUGHT and self._caught_at_ms is not None:
            elapsed = pygame.time.get_ticks() - self._caught_at_ms
            if elapsed < 100:
                self.screen.fill((255, 255, 255) if (elapsed // 50) % 2 == 0 else (235, 25, 45))
                return
            if elapsed < 480:
                self._draw_jumpscare_face(elapsed - 100)
                return

        self.screen.fill(BG_DARK)
        if self.state == State.INTRO:
            lines = [
                "THE EMPTY SHIFT — FIRST PERSON",
                "",
                "You are searching an abandoned packaging plant for Elias Crane,",
                "missing six months. The night shift left recordings of 'statues' in the aisles.",
                "",
                "MOVE: W forward, S back, A/D strafe   LOOK: mouse   INTERACT: E   ESC: quit",
                "ROBOTS crawl toward you — faster and meaner as you collect FILES and bring",
                "VALVES online.",
                "",
                "FIRST RED DOOR: all 3 VALVES on, first 2 FILES, then E while facing the door.",
                "SAVE ELIAS: keep all valves on, ALL 5 FILES, E on FINAL door, then reach green EXIT.",
                "",
                "Press ENTER to begin (mouse will be captured for look).",
            ]
            y = 56
            for ln in lines:
                surf = self.font.render(ln, True, (220, 220, 225))
                self.screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, y))
                y += 26
        elif self.state == State.PLAYING:
            self._draw_fps_world()
            if self.locked_doors:
                door_hud = (
                    "Red door: READY (E)"
                    if self._can_open_first_door()
                    else f"Red door: power + {FIRST_DOOR_FILES_NEEDED} files ({self.evidence_count}/{FIRST_DOOR_FILES_NEEDED}, valves: {'OK' if self.terminal_on else 'no'})"
                )
            else:
                door_hud = "Red door: open"
            if self.final_doors:
                final_hud = (
                    "Final door: READY (E)"
                    if self._can_rescue()
                    else f"Final door: power + {TOTAL_EVIDENCE_FILES} files ({self.evidence_count}/{TOTAL_EVIDENCE_FILES}, valves: {'OK' if self.terminal_on else 'no'})"
                )
            else:
                final_hud = (
                    "Exit: RESCUE ready"
                    if self._can_rescue()
                    else f"Exit: need power + {TOTAL_EVIDENCE_FILES} files ({self.evidence_count}/{TOTAL_EVIDENCE_FILES})"
                )
            ag = self._robot_aggro()
            hud = [
                f"Files: {self.evidence_count}/{TOTAL_EVIDENCE_FILES}   Power: {'OK' if self.terminal_on else 'toggle valves'}",
                f"Threat: {int(ag * 100)}%",
                door_hud,
                final_hud,
            ]
            yy = 8
            for h in hud:
                self.screen.blit(self.font_small.render(h, True, (220, 220, 225)), (12, yy))
                yy += 22

        if self.state == State.CAUGHT:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((80, 0, 0, 200))
            self.screen.blit(ov, (0, 0))
            t = self.font.render("They caught you in the aisles.", True, (255, 255, 255))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 - 20))
            t2 = self.font_small.render("R — try again   ESC — quit", True, (230, 230, 230))
            self.screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, SCREEN_H // 2 + 20))

        if self.state == State.WON:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 40, 30, 210))
            self.screen.blit(ov, (0, 0))
            t = self.font.render("All valves held. Every file accounted for. You get Elias out alive.", True, (200, 255, 220))
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2 - 20))
            t2 = self.font_small.render("R — play again   ESC — quit", True, (220, 240, 230))
            self.screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, SCREEN_H // 2 + 20))


def main():
    Game().run()
    pygame.quit()
