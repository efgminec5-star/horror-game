import math

# Display
SCREEN_W, SCREEN_H = 1280, 720
TITLE = "The Empty Shift — Factory Horror"
FPS = 60
# First-person raycast
FOV_RAD = math.pi * 0.52
MOUSE_SENS = 0.0022
RAY_STRIDE = 2  # draw every Nth column (2 = half rays, faster)

# World (pixels)
TILE = 48
PLAYER_RADIUS = 14
ROBOT_RADIUS = 16
ROBOT_SPEED = 95  # base; scales up with aggro (files + valves)
PLAYER_SPEED = 220
# Aggro 0..1 from files + valves: speed multiplier approaches this at full aggro
ROBOT_SPEED_MULT_MAX = 1.95
# Lead target along player velocity (seconds * aggro); higher = smarter cutting-off
ROBOT_LEAD_MAX_SEC = 0.42
# Use 2 movement substeps when aggro exceeds this (better corner pursuit)
ROBOT_SUBSTEP_AGGRO_THRESHOLD = 0.42
# Flashlight: small bright core, very dark everywhere else
FLASHLIGHT_RADIUS = 200
FLASHLIGHT_EDGE_ALPHA = 242  # unlit areas (higher = darker)
FLASHLIGHT_FALLOFF = 2.6  # >1 = tighter beam edge
ROBOT_CATCH_DIST = PLAYER_RADIUS + ROBOT_RADIUS + 4

# First (red) door: all valves + this many files
FIRST_DOOR_FILES_NEEDED = 2
# Rescue / final door / exit: need this many files and all valves (terminal_on)
TOTAL_EVIDENCE_FILES = 5

# Colors (muted industrial horror)
BG_DARK = (12, 14, 18)
FLOOR = (38, 42, 48)
FLOOR_ALT = (32, 36, 42)
WALL = (22, 24, 28)
WALL_EDGE = (55, 58, 65)
DOOR_LOCKED = (90, 35, 40)
DOOR_OPEN = (45, 70, 50)
ACCENT = (180, 40, 45)
