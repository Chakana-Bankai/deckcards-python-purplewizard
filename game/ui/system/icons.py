"""Centralized icon rendering API for Chakana UI."""

from __future__ import annotations

import pygame


ICON_GLYPHS = {
    "damage": "✦",
    "block": "▣",
    "harmony": "◈",
    "rupture": "⬟",
    "scry": "◉",
    "draw": "+",
    "energy": "●",
    "deck": "M",
    "hand": "H",
    "discard": "E",
    "fatigue": "D",
    "ritual": "△",
    "boss": "⚚",
    "shop": "¤",
    "guide": "☉",
    "relic": "◆",
}


def render_icon(surface: pygame.Surface, icon_name: str, pos: tuple[int, int], size: int, color: tuple[int, int, int], font: pygame.font.Font):
    """Render an icon glyph through a single API."""
    glyph = ICON_GLYPHS.get(str(icon_name), "?")
    txt = font.render(glyph, True, color)
    if size > 1:
        txt = pygame.transform.smoothscale(txt, (int(txt.get_width() * size), int(txt.get_height() * size)))
    surface.blit(txt, pos)
