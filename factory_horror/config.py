# Display
SCREEN_W, SCREEN_H = 1280, 720
TITLE = "The Empty Shift — Factory Horror"
FPS = 60

# World (pixels)
TILE = 48
PLAYER_RADIUS = 14
ROBOT_RADIUS = 16
ROBOT_SPEED = 95  # only applied while player moves
PLAYER_SPEED = 220
# Lit area around player (larger = easier to see; horror is edge vignette only)
FLASHLIGHT_RADIUS = 420
FLASHLIGHT_EDGE_ALPHA = 95  # darkness at screen edges (lower = clearer gameplay)
ROBOT_CATCH_DIST = PLAYER_RADIUS + ROBOT_RADIUS + 4

# Colors (muted industrial horror)
BG_DARK = (12, 14, 18)
FLOOR = (38, 42, 48)
FLOOR_ALT = (32, 36, 42)
WALL = (22, 24, 28)
WALL_EDGE = (55, 58, 65)
DOOR_LOCKED = (90, 35, 40)
DOOR_OPEN = (45, 70, 50)
ACCENT = (180, 40, 45)
