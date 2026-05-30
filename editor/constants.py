"""Layout, palette, and colour constants for the pixel art editor."""

# --- Sprite grid ------------------------------------------------------------
GRID_W = 32
GRID_H = 32
CELL = 16  # on-screen size (px) of one sprite pixel inside the canvas

# --- Canvas placement -------------------------------------------------------
CANVAS_X = 184
CANVAS_Y = 56
CANVAS_W = GRID_W * CELL  # 512
CANVAS_H = GRID_H * CELL  # 512

# --- Panels -----------------------------------------------------------------
LEFT_X = 12
LEFT_W = 158
RIGHT_X = CANVAS_X + CANVAS_W + 18  # right info/controls column
TIMELINE_Y = CANVAS_Y + CANVAS_H + 18
TIMELINE_X = CANVAS_X
THUMB = 56  # frame thumbnail size in the timeline

WINDOW_W = 1140
WINDOW_H = 760
FPS = 60

# Transparent sentinel for an empty pixel.
TRANSPARENT = (0, 0, 0, 0)

# --- UI colours -------------------------------------------------------------
C_BG = (28, 28, 36)
C_PANEL = (44, 44, 56)
C_PANEL_HI = (58, 58, 72)
C_ACCENT = (92, 148, 226)
C_TEXT = (224, 224, 232)
C_TEXT_DIM = (150, 150, 162)
C_GRID = (60, 60, 72)
C_CHECKER_A = (70, 70, 82)
C_CHECKER_B = (52, 52, 64)
C_BORDER = (20, 20, 26)

# --- Default 32-colour palette (DawnBringer-flavoured) ----------------------
PALETTE = [
    (0, 0, 0, 255), (34, 32, 52, 255), (69, 40, 60, 255), (102, 57, 49, 255),
    (143, 86, 59, 255), (223, 113, 38, 255), (217, 160, 102, 255), (238, 195, 154, 255),
    (251, 242, 54, 255), (153, 229, 80, 255), (106, 190, 48, 255), (55, 148, 110, 255),
    (75, 105, 47, 255), (82, 75, 36, 255), (50, 60, 57, 255), (63, 63, 116, 255),
    (48, 96, 130, 255), (91, 110, 225, 255), (99, 155, 255, 255), (95, 205, 228, 255),
    (203, 219, 252, 255), (255, 255, 255, 255), (155, 173, 183, 255), (132, 126, 135, 255),
    (105, 106, 106, 255), (89, 86, 82, 255), (118, 66, 138, 255), (172, 50, 50, 255),
    (217, 87, 99, 255), (215, 123, 186, 255), (143, 151, 74, 255), (138, 111, 48, 255),
]
