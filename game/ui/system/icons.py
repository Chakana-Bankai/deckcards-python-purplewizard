"""Centralized semantic icon API for Chakana UI.

This module intentionally avoids font-only glyph icons for KPI rows,
so missing glyph support never renders broken square placeholders.
"""

from __future__ import annotations

import pygame
from game.visual import get_visual_engine


ICON_ALIASES = {
    "sword": "damage",
    "shield": "block",
    "bolt": "energy",
    "star": "harmony",
    "crack": "rupture",
    "eye": "scry",
    "scroll": "draw",
}

FALLBACK_TEXT = {
    "damage": "*",
    "block": "#",
    "energy": "!",
    "harmony": "<>",
    "rupture": "//",
    "scry": "o",
    "draw": "+",
    "ritual": "^",
    "gold": "$",
    "xp": "xp",
    "level": "lvl",
    "deck": "M",
    "hand": "H",
    "discard": "E",
    "fatigue": "D",
    "boss": "B",
    "shop": "$",
    "guide": "G",
    "relic": "R",
    "unknown": "?",
}

_ICON_CACHE: dict[tuple[str, tuple[int, int, int], int], pygame.Surface] = {}
_VISUAL_ENGINE = None


def normalize_icon_name(icon_name: str) -> str:
    key = str(icon_name or "unknown").strip().lower()
    semantic = {
        "damage",
        "block",
        "energy",
        "harmony",
        "rupture",
        "scry",
        "draw",
        "ritual",
        "gold",
        "xp",
        "level",
        "deck",
        "hand",
        "discard",
        "fatigue",
        "boss",
        "shop",
        "guide",
        "relic",
        "unknown",
    }
    if key in semantic:
        return key
    return ICON_ALIASES.get(key, "unknown")


def _make_surface(px: int) -> pygame.Surface:
    return pygame.Surface((px, px), pygame.SRCALPHA)


def _stroke(surf: pygame.Surface, color: tuple[int, int, int], pts: list[tuple[int, int]], w: int = 2):
    if len(pts) >= 2:
        pygame.draw.lines(surf, color, False, pts, max(1, int(w)))


def _render_icon_surface(icon_name: str, color: tuple[int, int, int], size: int) -> pygame.Surface:
    key = normalize_icon_name(icon_name)
    scale = max(1, int(size or 1))
    px = 14 * scale
    cache_key = (key, tuple(int(c) for c in color), scale)
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached

    surf = _make_surface(px)
    c = tuple(int(v) for v in color[:3])
    lw = max(1, scale)
    mid = px // 2

    # Prefer centralized visual engine icon if available.
    global _VISUAL_ENGINE
    try:
        if _VISUAL_ENGINE is None:
            _VISUAL_ENGINE = get_visual_engine()
        vis = _VISUAL_ENGINE.generate("icons", key, (px, px), context="", force=False)
        if vis is not None:
            vis_col = vis.copy()
            vis_col.fill((c[0], c[1], c[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
            _ICON_CACHE[cache_key] = vis_col
            return vis_col
    except Exception:
        pass

    if key == "damage":
        _stroke(surf, c, [(3 * scale, 11 * scale), (11 * scale, 3 * scale)], lw + 1)
        _stroke(surf, c, [(6 * scale, 3 * scale), (11 * scale, 3 * scale), (11 * scale, 8 * scale)], lw)
    elif key == "block":
        poly = [(mid, 2 * scale), (11 * scale, 4 * scale), (10 * scale, 10 * scale), (mid, 12 * scale), (4 * scale, 10 * scale), (3 * scale, 4 * scale)]
        pygame.draw.polygon(surf, c, poly, lw + 1)
    elif key == "energy":
        poly = [(8 * scale, 2 * scale), (5 * scale, 7 * scale), (8 * scale, 7 * scale), (6 * scale, 12 * scale), (10 * scale, 6 * scale), (7 * scale, 6 * scale)]
        pygame.draw.polygon(surf, c, poly)
    elif key == "harmony":
        poly = [(mid, 2 * scale), (11 * scale, mid), (mid, 12 * scale), (3 * scale, mid)]
        pygame.draw.polygon(surf, c, poly, lw + 1)
        pygame.draw.circle(surf, c, (mid, mid), max(1, scale), 0)
    elif key == "rupture":
        _stroke(surf, c, [(3 * scale, 3 * scale), (7 * scale, 6 * scale), (4 * scale, 8 * scale), (10 * scale, 12 * scale)], lw + 1)
    elif key == "scry":
        eye_rect = pygame.Rect(2 * scale, 4 * scale, 10 * scale, 6 * scale)
        pygame.draw.ellipse(surf, c, eye_rect, lw + 1)
        pygame.draw.circle(surf, c, (mid, 7 * scale), max(1, scale + 1))
    elif key == "draw":
        rect = pygame.Rect(3 * scale, 3 * scale, 8 * scale, 8 * scale)
        pygame.draw.rect(surf, c, rect, lw + 1, border_radius=max(1, scale))
        _stroke(surf, c, [(6 * scale, 12 * scale), (11 * scale, 12 * scale)], lw + 1)
        _stroke(surf, c, [(10 * scale, 10 * scale), (12 * scale, 12 * scale), (10 * scale, 14 * scale)], lw)
    elif key == "ritual":
        tri = [(mid, 2 * scale), (11 * scale, 11 * scale), (3 * scale, 11 * scale)]
        pygame.draw.polygon(surf, c, tri, lw + 1)
        pygame.draw.circle(surf, c, (mid, 8 * scale), max(1, scale), 0)
    elif key == "gold":
        pygame.draw.circle(surf, c, (mid, mid), 5 * scale, lw + 1)
        pygame.draw.circle(surf, c, (mid, mid), max(1, scale), 0)
    elif key == "xp":
        _stroke(surf, c, [(mid, 2 * scale), (mid, 12 * scale)], lw)
        _stroke(surf, c, [(2 * scale, mid), (12 * scale, mid)], lw)
        _stroke(surf, c, [(4 * scale, 4 * scale), (10 * scale, 10 * scale)], lw)
        _stroke(surf, c, [(10 * scale, 4 * scale), (4 * scale, 10 * scale)], lw)
    else:
        # Safe fallback: compact marker, never tofu squares.
        pygame.draw.circle(surf, c, (mid, mid), 4 * scale, lw)
        pygame.draw.circle(surf, c, (mid, mid), max(1, scale), 0)

    _ICON_CACHE[cache_key] = surf
    return surf


def render_icon(
    surface: pygame.Surface,
    icon_name: str,
    pos: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    font: pygame.font.Font,
):
    """Render one semantic icon through a single API."""
    icon = _render_icon_surface(icon_name, color, size)
    if icon is None or icon.get_width() <= 0:
        label = FALLBACK_TEXT.get(normalize_icon_name(icon_name), "?")
        surface.blit(font.render(label, True, color), pos)
        return
    surface.blit(icon, pos)


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
    icon = _render_icon_surface(icon_name, color, size)
    if icon is None or icon.get_width() <= 0:
        label = FALLBACK_TEXT.get(normalize_icon_name(icon_name), "?")
        icon = font.render(label, True, color)

    surface.blit(icon, (x, y))
    txt = font.render(str(int(value or 0)), True, color)
    vy = y + max(0, (icon.get_height() - txt.get_height()) // 2)
    surface.blit(txt, (x + icon.get_width() + 4, vy))
    return x + icon.get_width() + txt.get_width() + 12


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
        "level": "level",
    }
    return mapping.get(key, "unknown")
