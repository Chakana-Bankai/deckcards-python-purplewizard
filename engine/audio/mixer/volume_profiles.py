"""Default volume profile presets."""

from __future__ import annotations

VOLUME_PROFILES = {
    "default": {
        "master": 1.0,
        "music": 0.75,
        "sfx": 0.85,
        "stingers": 0.90,
        "ambient": 0.60,
        "ui": 0.80,
        "dialogue": 0.85,
    },
    "accessibility_high_dialogue": {
        "master": 1.0,
        "music": 0.60,
        "sfx": 0.80,
        "stingers": 0.85,
        "ambient": 0.50,
        "ui": 0.85,
        "dialogue": 1.00,
    },
}
