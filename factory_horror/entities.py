from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Set, Tuple

from .config import MOUSE_SENS, PLAYER_RADIUS, ROBOT_RADIUS, ROBOT_SPEED, PLAYER_SPEED, TILE


def circle_wall_collision(
    x: float,
    y: float,
    radius: float,
    walls: Set[Tuple[int, int]],
) -> Tuple[float, float]:
    """Resolve AABB tiles vs circle; return corrected position."""
    gx = int(x // TILE)
    gy = int(y // TILE)
    for ty in range(gy - 1, gy + 2):
        for tx in range(gx - 1, gx + 2):
            if (tx, ty) not in walls:
                continue
            cx = tx * TILE + TILE / 2
            cy = ty * TILE + TILE / 2
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            min_dist = TILE / 2 + radius - 0.01
            if dist < min_dist and dist > 1e-6:
                push = (min_dist - dist) / dist
                x += dx * push
                y += dy * push
            elif dist <= 1e-6:
                x += min_dist
    return x, y


@dataclass
class Player:
    x: float
    y: float
    angle: float = 0.0  # radians; 0 = +X east, pi/2 = +Y south (screen down)
    vel_x: float = 0.0
    vel_y: float = 0.0

    def update_fps(
        self,
        dt: float,
        walls: Set[Tuple[int, int]],
        keys,
        mouse_dx: float,
        mouse_active: bool,
    ) -> bool:
        import pygame

        if mouse_active:
            self.angle += mouse_dx * MOUSE_SENS

        fx = math.cos(self.angle)
        fy = math.sin(self.angle)
        rdx = -math.sin(self.angle)
        rdy = math.cos(self.angle)

        mx = 0.0
        my = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            mx += fx
            my += fy
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            mx -= fx
            my -= fy
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= rdx
            my -= rdy
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += rdx
            my += rdy

        moving = mx != 0.0 or my != 0.0
        if moving:
            ln = math.hypot(mx, my)
            mx /= ln
            my /= ln

        old_x, old_y = self.x, self.y
        nx = self.x + mx * PLAYER_SPEED * dt
        ny = self.y + my * PLAYER_SPEED * dt
        for _ in range(4):
            nx, ny = circle_wall_collision(nx, ny, PLAYER_RADIUS, walls)
        self.x = nx
        self.y = ny

        dt = max(dt, 1e-6)
        self.vel_x = (self.x - old_x) / dt
        self.vel_y = (self.y - old_y) / dt
        return moving


@dataclass
class Robot:
    x: float
    y: float

    def step_toward(
        self,
        tx: float,
        ty: float,
        dt: float,
        walls: Set[Tuple[int, int]],
        speed: float | None = None,
    ):
        sp = ROBOT_SPEED if speed is None else speed
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        dx /= dist
        dy /= dist
        step = sp * dt
        if step > dist:
            step = dist
        nx = self.x + dx * step
        ny = self.y + dy * step
        for _ in range(3):
            nx, ny = circle_wall_collision(nx, ny, ROBOT_RADIUS, walls)
        self.x = nx
        self.y = ny
