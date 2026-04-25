"""Preview robot animations before adding them to the game.
Walk (unaware) on the left, Run (chasing) on the right.
Press ESC or close window to exit."""

from __future__ import annotations
import math
import sys
import pygame

W, H = 860, 520
FPS = 60


def lerp_col(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_robot(surf: pygame.Surface, cx: int, cy: int, h: int,
               aggro: float, phase: float, running: bool) -> None:
    """Draw one animated robot centred at (cx, cy) with sprite height h."""
    # -- colours -------------------------------------------------------
    shell     = lerp_col((35, 38, 45),  (72, 28, 32),  aggro)
    body_col  = lerp_col((180, 40, 45), (240, 55, 55), aggro)
    eye_c     = lerp_col((255, 90, 55), (255, 220, 100), aggro)
    arm_dark  = (max(0, body_col[0]-35), max(0, body_col[1]-12), max(0, body_col[2]-12))
    leg_col   = (max(0, body_col[0]-20), max(0, body_col[1]-8),  max(0, body_col[2]-8))
    jfill     = (50, 52, 60)
    jring     = (24, 26, 32)

    # -- animation params ----------------------------------------------
    if running:
        freq, swing_amp, bob_amp = 3.8, 0.52, 5
    else:
        freq, swing_amp, bob_amp = 1.8, 0.22, 2

    p = phase * freq          # phase in cycles
    s = math.sin(p * math.pi * 2)
    bob = int(abs(math.sin(p * math.pi * 2)) * bob_amp)

    leg_x_amp  = int(s * swing_amp * max(3, int(h * 0.30) * 0.42))
    arm_v_amp  = int(s * swing_amp * h * 0.18)

    # -- proportions (mirror game.py) ----------------------------------
    head_w  = max(8,  int(h * 0.58))
    head_h  = max(5,  int(h * 0.19))
    body_w  = max(4,  int(h * 0.30))
    torso_h = int(h * 0.40)
    leg_h   = max(4,  int(h * 0.17))
    leg_w   = max(3,  int(body_w * 0.42))
    leg_btw = max(1,  h // 55)
    gap     = max(1,  h // 45)
    leg_gap = max(1,  h // 50)
    arm_w_  = max(3,  int(h * 0.085))
    arm_h_  = int(torso_h * 0.88)
    arm_gap = max(1,  h // 50)
    j_r     = max(3,  int(h * 0.038))
    jk_r    = max(3,  int(h * 0.036))

    stack_h = head_h + gap + torso_h + leg_gap + leg_h
    oy = cy - stack_h // 2 + bob          # top of head, with bob
    hx = cx - head_w // 2

    # -- head ----------------------------------------------------------
    hr = pygame.Rect(hx, oy, head_w, head_h)
    pygame.draw.ellipse(surf, shell,        hr.inflate(4, 4))
    pygame.draw.ellipse(surf, (40, 42, 50), hr)
    pygame.draw.ellipse(surf, (26, 28, 34), hr, 1)

    # eyes
    es   = max(2, head_h // 2)
    ey_y = oy + head_h // 2 - es // 2
    eg   = max(1, es // 2)
    x0   = hx + (head_w - (3*es + 2*eg)) // 2
    for i in range(3):
        pygame.draw.rect(surf, eye_c, (x0 + i*(es+eg), ey_y, es, es))

    # -- body origin ---------------------------------------------------
    by  = oy + head_h + gap
    bx  = cx - body_w // 2
    arm_y = by + int(torso_h * 0.06)

    # -- arms (opposite phase to same-side leg) -----------------------
    def draw_arm(ax: int, v_off: int) -> None:
        rest  = arm_h_ - j_r
        up_h  = max(2, int(rest * 0.48))
        lo_h  = max(2, rest - up_h)
        ay0   = arm_y + v_off
        ur = pygame.Rect(ax, ay0, arm_w_, up_h)
        pygame.draw.ellipse(surf, shell,    ur.inflate(2, 2))
        pygame.draw.ellipse(surf, arm_dark, ur)
        pygame.draw.ellipse(surf, jring,    ur, 1)
        ex_, ey_ = ax + arm_w_//2, ay0 + up_h + j_r//2
        pygame.draw.circle(surf, jfill, (ex_, ey_), j_r//2)
        pygame.draw.circle(surf, jring, (ex_, ey_), j_r//2, 1)
        lr = pygame.Rect(ax, ay0 + up_h + j_r, arm_w_, lo_h)
        pygame.draw.ellipse(surf, shell,    lr.inflate(2, 2))
        pygame.draw.ellipse(surf, arm_dark, lr)
        pygame.draw.ellipse(surf, jring,    lr, 1)

    draw_arm(bx - arm_w_ - arm_gap,  -arm_v_amp)   # left arm: opposite to left leg
    draw_arm(bx + body_w + arm_gap,   arm_v_amp)   # right arm

    # -- torso ---------------------------------------------------------
    br = pygame.Rect(bx, by, body_w, torso_h)
    pygame.draw.ellipse(surf, shell,           br.inflate(4, 4))
    pygame.draw.ellipse(surf, body_col,        br)
    sw_ = max(2, int(body_w * 0.38))
    sh_ = max(2, int(torso_h * 0.82))
    sr  = pygame.Rect(cx - sw_//2, by + max(1, torso_h//12), sw_, sh_)
    pygame.draw.ellipse(surf, (max(0,body_col[0]-28),max(0,body_col[1]-18),max(0,body_col[2]-18)), sr)
    band_r = pygame.Rect(bx, by + torso_h//3, body_w, max(2, torso_h//6))
    pygame.draw.ellipse(surf, (72, 22, 26), band_r)
    pygame.draw.ellipse(surf, jring, br, 1)

    # -- legs (lateral swing gives front-on stride illusion) ----------
    legs_top = by + torso_h + leg_gap
    span     = leg_w*2 + leg_btw
    lx0      = cx - span//2

    for i in range(2):
        sign   = 1 if i == 0 else -1
        thigh_x = lx0 + i*(leg_w + leg_btw) + sign*leg_x_amp
        shin_x  = lx0 + i*(leg_w + leg_btw) - sign*(leg_x_amp//2)

        rem   = leg_h - jk_r
        th_h  = max(2, int(rem * 0.52))
        sh_h  = max(2, rem - th_h)

        tr = pygame.Rect(thigh_x, legs_top, leg_w, th_h)
        pygame.draw.ellipse(surf, shell,   tr.inflate(2, 2))
        pygame.draw.ellipse(surf, leg_col, tr)
        pygame.draw.ellipse(surf, jring,   tr, 1)

        kcx_ = thigh_x + leg_w//2
        kcy_ = legs_top + th_h + jk_r//2
        pygame.draw.circle(surf, jfill, (kcx_, kcy_), jk_r//2)
        pygame.draw.circle(surf, jring, (kcx_, kcy_), jk_r//2, 1)

        sr2 = pygame.Rect(shin_x, legs_top + th_h + jk_r, leg_w, sh_h)
        pygame.draw.ellipse(surf, shell,   sr2.inflate(2, 2))
        pygame.draw.ellipse(surf, leg_col, sr2)
        pygame.draw.ellipse(surf, jring,   sr2, 1)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Robot Animation Preview  —  ESC to close")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("consolas", 22)
    small  = pygame.font.SysFont("consolas", 16)

    t = 0.0
    robot_h = 210

    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                pygame.quit(); return

        screen.fill((12, 14, 18))

        # divider
        pygame.draw.line(screen, (50, 55, 65), (W//2, 60), (W//2, H-40))

        # -- left: WALK -----------------------------------------------
        draw_robot(screen, W//4, H//2 + 20, robot_h, aggro=0.05, phase=t, running=False)
        lbl = font.render("WALK  —  Unaware", True, (200, 210, 220))
        screen.blit(lbl, (W//4 - lbl.get_width()//2, 14))
        sub = small.render("slow stride  •  dim eyes  •  passive", True, (110, 120, 130))
        screen.blit(sub, (W//4 - sub.get_width()//2, 40))

        # -- right: RUN -----------------------------------------------
        draw_robot(screen, W*3//4, H//2 + 20, robot_h, aggro=0.9, phase=t, running=True)
        lbl2 = font.render("RUN  —  Chasing", True, (240, 80, 60))
        screen.blit(lbl2, (W*3//4 - lbl2.get_width()//2, 14))
        sub2 = small.render("fast sprint  •  bright eyes  •  aggressive", True, (180, 90, 80))
        screen.blit(sub2, (W*3//4 - sub2.get_width()//2, 40))

        # hint
        hint = small.render("ESC / close window to exit preview", True, (70, 75, 85))
        screen.blit(hint, (W//2 - hint.get_width()//2, H - 28))

        pygame.display.flip()


if __name__ == "__main__":
    main()
