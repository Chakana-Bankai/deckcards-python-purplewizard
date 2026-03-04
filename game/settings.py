"""Global settings for CHAKANA MVP."""

from game.core.paths import assets_dir, data_dir, game_dir

BASE_DIR = game_dir()
DATA_DIR = data_dir()
ASSETS_DIR = assets_dir()

INTERNAL_WIDTH = 1920
INTERNAL_HEIGHT = 1080
FPS = 60
DEFAULT_LANG = "es"

COLORS = {
    "primary_purple": (75, 30, 120),
    "deep_purple": (44, 15, 69),
    "accent_violet": (143, 77, 255),
    "gold": (212, 175, 55),
    "off_white": (241, 232, 255),
    "text_dark": (26, 16, 37),
    "muted_lavender": (188, 169, 230),
    "bg": (12, 14, 28),
    "panel": (44, 15, 69),
    "violet": (143, 77, 255),
    "violet_dark": (89, 56, 166),
    "text": (241, 232, 255),
    "muted": (188, 169, 230),
    "good": (112, 220, 148),
    "bad": (232, 92, 106),
}
