"""Canonical runtime icon registry and size profiles.

All UI layers should resolve icon ids through this module.
"""

from __future__ import annotations

import pygame

from game.ui.system import icons as _icons
from game.ui.system.ui_scale_system import ICON_CARD_MEDIUM, ICON_CARD_SMALL, ICON_CARD_KPI, ICON_HUD_SMALL, ICON_HUD_MEDIUM, ICON_HUD_LARGE


ICON_FAMILIES = {
    "damage",
    "block",
    "heal",
    "draw",
    "retain",
    "energy",
    "ritual",
    "harmony",
    "rupture",
    "exhaust",
    "combo",
    "control",
    "canalizacion",
    "seal",
    "umbral",
    "buff",
    "debuff",
}

SIZE_PROFILES = {
    "small": ICON_HUD_SMALL,
    "medium": ICON_HUD_MEDIUM,
    "large": ICON_HUD_LARGE,
    "card_small": ICON_CARD_SMALL,
    "card_medium": ICON_CARD_MEDIUM,
    "card_kpi": ICON_CARD_KPI,
}

STROKE_BY_PROFILE = {
    "small": 1,
    "medium": 1,
    "large": 2,
    "card_small": 1,
    "card_medium": 1,
    "card_kpi": 2,
}


ALIASES = {
    "canalizacion": "energy",
    "sello": "seal",
    "umbral": "harmony",
    "buff": "support",
    "debuff": "support",
}


def resolve_icon(effect_or_name: str) -> str:
    key = _icons.resolve_icon_id(str(effect_or_name or ""))
    if key == "unknown":
        key = _icons.icon_for_effect(str(effect_or_name or ""))
    if key == "unknown":
        key = ALIASES.get(str(effect_or_name or "").strip().lower(), "unknown")
    return key


def profile_px(profile: str) -> int:
    return int(SIZE_PROFILES.get(str(profile or "").lower(), ICON_HUD_MEDIUM))


def draw_icon(surface: pygame.Surface, effect_or_name: str, x: int, y: int, color: tuple[int, int, int], font: pygame.font.Font, profile: str = "medium"):
    icon_id = resolve_icon(effect_or_name)
    px = profile_px(profile)
    size = max(1, int(round(px / 14.0)))
    _icons.render_icon(surface, icon_id, (x, y), size, color, font)


def draw_icon_value(surface: pygame.Surface, effect_or_name: str, value: int, x: int, y: int, color: tuple[int, int, int], font: pygame.font.Font, profile: str = "medium") -> int:
    icon_id = resolve_icon(effect_or_name)
    px = profile_px(profile)
    size = max(1, int(round(px / 14.0)))
    return _icons.draw_icon_with_value(surface, icon_id, int(value), color, font, x, y, size=size, min_icon_px=px)

# Compatibility wrapper for legacy callers.
def draw_icon_with_value_compat(
    surface: pygame.Surface,
    icon_name: str,
    value: int,
    color: tuple[int, int, int],
    font: pygame.font.Font,
    x: int,
    y: int,
    size: int = 1,
    min_icon_px: int = 0,
) -> int:
    profile = "medium"
    if int(min_icon_px or 0) <= ICON_HUD_SMALL:
        profile = "small"
    elif int(min_icon_px or 0) >= ICON_HUD_LARGE:
        profile = "large"
    return draw_icon_value(surface, icon_name, int(value), x, y, color, font, profile=profile)

# Backward-compatible export expected by existing screens.
draw_icon_with_value = draw_icon_with_value_compat
