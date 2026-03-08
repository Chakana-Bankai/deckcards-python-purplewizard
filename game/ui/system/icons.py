"""Centralized semantic icon API for Chakana UI."""

from __future__ import annotations

import pygame


ICON_GLYPHS = {
    "damage": "✦",
    "block": "▣",
    "energy": "●",
    "harmony": "◈",
    "rupture": "⬟",
    "scry": "◉",
    "draw": "+",
    "ritual": "△",
    "gold": "¤",
    "xp": "✶",
    "deck": "M",
    "hand": "H",
    "discard": "E",
    "fatigue": "D",
    "boss": "⚚",
    "shop": "¤",
    "guide": "☉",
    "relic": "◆",
    "unknown": "?",
}

# Backward aliases used by legacy card/icon paths.
ICON_ALIASES = {
    "sword": "damage",
    "shield": "block",
    "bolt": "energy",
    "star": "harmony",
    "crack": "rupture",
    "eye": "scry",
    "scroll": "draw",
}


def normalize_icon_name(icon_name: str) -> str:
    key = str(icon_name or "unknown").strip().lower()
    if key in ICON_GLYPHS:
        return key
    return ICON_ALIASES.get(key, "unknown")


def render_icon(
    surface: pygame.Surface,
    icon_name: str,
    pos: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    font: pygame.font.Font,
):
    """Render one semantic icon through a single API."""
    key = normalize_icon_name(icon_name)
    glyph = ICON_GLYPHS.get(key, ICON_GLYPHS["unknown"])
    txt = font.render(glyph, True, color)
    scale = max(1, int(size or 1))
    if scale > 1:
        txt = pygame.transform.smoothscale(txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
    surface.blit(txt, pos)


def draw_icon_with_value(
    surface: pygame.Surface,
    icon_name: str,
    value: int,
    color: tuple[int, int, int],
    font: pygame.font.Font,
    x: int,
    y: int,
    size: int = 1,
) -> int:
    """Draw icon + numeric value and return the next x cursor position."""
    key = normalize_icon_name(icon_name)
    glyph = ICON_GLYPHS.get(key, ICON_GLYPHS["unknown"])
    icon = font.render(glyph, True, color)
    scale = max(1, int(size or 1))
    if scale > 1:
        icon = pygame.transform.smoothscale(icon, (int(icon.get_width() * scale), int(icon.get_height() * scale)))
    surface.blit(icon, (x, y))

    txt = font.render(str(int(value or 0)), True, color)
    vy = y + max(0, (icon.get_height() - txt.get_height()) // 2)
    surface.blit(txt, (x + icon.get_width() + 4, vy))
    return x + icon.get_width() + txt.get_width() + 14


def icon_for_effect(effect_type: str) -> str:
    """Map effect identifiers to semantic icons with safe fallback."""
    key = str(effect_type or "").strip().lower()
    mapping = {
        "damage": "damage",
        "block": "block",
        "gain_block": "block",
        "energy": "energy",
        "gain_mana": "energy",
        "gain_mana_next_turn": "energy",
        "harmony": "harmony",
        "harmony_delta": "harmony",
        "consume_harmony": "harmony",
        "rupture": "rupture",
        "apply_break": "rupture",
        "break": "rupture",
        "scry": "scry",
        "draw": "draw",
        "ritual": "ritual",
        "ritual_trama": "ritual",
        "gain_gold": "gold",
        "gold": "gold",
        "gain_xp": "xp",
        "xp": "xp",
    }
    return mapping.get(key, "unknown")
