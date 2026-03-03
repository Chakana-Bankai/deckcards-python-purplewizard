"""Global settings for CHAKANA MVP."""

from game.core.paths import assets_dir, data_dir, game_dir

BASE_DIR = game_dir()
DATA_DIR = data_dir()
ASSETS_DIR = assets_dir()

INTERNAL_WIDTH = 1280
INTERNAL_HEIGHT = 720
FPS = 60
DEFAULT_LANG = "es"

COLORS = {
    "bg": (12, 14, 28),
    "panel": (26, 30, 54),
    "violet": (145, 98, 255),
    "violet_dark": (89, 56, 166),
    "text": (245, 245, 250),
    "muted": (170, 170, 195),
    "good": (112, 220, 148),
    "bad": (232, 92, 106),
    "gold": (244, 194, 78),
}
