from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Set, Tuple

from .config import PLAYER_RADIUS, ROBOT_RADIUS, ROBOT_SPEED, PLAYER_SPEED, TILE


Vec2 = Tuple[float, float]


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
    vx: float = 0.0
    vy: float = 0.0

    def update(self, dt: float, walls: Set[Tuple[int, int]], keys) -> bool:
        import pygame

        moving = False
        self.vx = 0.0
        self.vy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.vy = -PLAYER_SPEED
            moving = True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.vy = PLAYER_SPEED
            moving = True
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -PLAYER_SPEED
            moving = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = PLAYER_SPEED
            moving = True
        if self.vx and self.vy:
            self.vx *= 0.70710678
            self.vy *= 0.70710678
        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt
        nx, self.y = circle_wall_collision(nx, self.y, PLAYER_RADIUS, walls)
        self.x, ny = circle_wall_collision(self.x, ny, PLAYER_RADIUS, walls)
        self.x = nx
        self.y = ny
        return moving


@dataclass
class Robot:
    x: float
    y: float

    def step_toward(self, tx: float, ty: float, dt: float, walls: Set[Tuple[int, int]]):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        dx /= dist
        dy /= dist
        step = ROBOT_SPEED * dt
        if step > dist:
            step = dist
        nx = self.x + dx * step
        ny = self.y + dy * step
        nx, self.y = circle_wall_collision(nx, self.y, ROBOT_RADIUS, walls)
        self.x, ny = circle_wall_collision(self.x, ny, ROBOT_RADIUS, walls)
        self.x = nx
        self.y = ny
