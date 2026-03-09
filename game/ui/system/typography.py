"""Centralized typography roles, sizes and semantic text colors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pygame

from .fonts import get_lore_font, get_title_font, get_ui_font
from .ui_scale_system import FONT_CONTEXT_SIZES, FONT_LABEL, FONT_SECTION, FONT_SMALL, FONT_TITLE

TITLE_FONT = "TITLE_FONT"
HUD_FONT = "HUD_FONT"
LORE_FONT = "LORE_FONT"
SMALL_FONT = "SMALL_FONT"
BUTTON_FONT = "BUTTON_FONT"

CONTEXT_FONT_SIZES: Dict[str, tuple[str, int]] = {
    "combat_title": (TITLE_FONT, FONT_CONTEXT_SIZES["combat_title"]),
    "combat_label": (HUD_FONT, FONT_CONTEXT_SIZES["combat_label"]),
    "combat_value": (HUD_FONT, FONT_CONTEXT_SIZES["combat_value"]),
    "combat_labels": (HUD_FONT, 22),
    "hud_numbers": (HUD_FONT, 28),
    "card_titles": (TITLE_FONT, FONT_CONTEXT_SIZES["card_title"]),
    "card_title": (TITLE_FONT, FONT_CONTEXT_SIZES["card_title"]),
    "card_type": (HUD_FONT, FONT_CONTEXT_SIZES["card_type"]),
    "card_effect": (LORE_FONT, FONT_CONTEXT_SIZES["card_effect"]),
    "card_body": (LORE_FONT, 20),
    "card_lore": (LORE_FONT, FONT_CONTEXT_SIZES["card_lore"]),
    "card_footer": (LORE_FONT, FONT_CONTEXT_SIZES["card_footer"]),
    "lore_text": (LORE_FONT, 22),
    "codex_header": (TITLE_FONT, FONT_CONTEXT_SIZES["codex_header"]),
    "codex_headers": (TITLE_FONT, FONT_CONTEXT_SIZES["codex_header"]),
    "map_label": (HUD_FONT, FONT_CONTEXT_SIZES["map_label"]),
    "map_labels": (HUD_FONT, FONT_CONTEXT_SIZES["map_label"]),
    "shop_header": (TITLE_FONT, FONT_CONTEXT_SIZES["shop_header"]),
    "shop_headers": (TITLE_FONT, FONT_CONTEXT_SIZES["shop_header"]),
}


@dataclass(frozen=True)
class TypographyPalette:
    title_primary: tuple[int, int, int] = (214, 182, 255)
    title_glow: tuple[int, int, int] = (122, 210, 255)
    hud_default: tuple[int, int, int] = (236, 240, 255)
    hud_energy: tuple[int, int, int] = (130, 218, 255)
    hud_damage: tuple[int, int, int] = (255, 104, 122)
    hud_block: tuple[int, int, int] = (132, 174, 255)
    hud_harmony: tuple[int, int, int] = (189, 152, 255)
    hud_gold: tuple[int, int, int] = (236, 212, 148)
    lore: tuple[int, int, int] = (206, 200, 230)
    muted: tuple[int, int, int] = (166, 160, 196)


class ChakanaTypography:
    """Single source of truth for UI typography roles."""

    DEFAULT_SIZES: Dict[str, int] = {
        TITLE_FONT: FONT_TITLE,
        HUD_FONT: 30,
        LORE_FONT: FONT_SECTION,
        SMALL_FONT: FONT_LABEL,
        BUTTON_FONT: FONT_SECTION,
    }

    def __init__(self):
        self.palette = TypographyPalette()
        self._warned: set[str] = set()

    def get(self, role: str, size: int | None = None) -> pygame.font.Font:
        if not pygame.font.get_init():
            pygame.font.init()
        sz = int(size if size is not None else self.DEFAULT_SIZES.get(role, FONT_SECTION))
        try:
            if role == TITLE_FONT:
                return get_title_font(sz)
            if role == LORE_FONT:
                return get_lore_font(sz)
            return get_ui_font(sz)
        except Exception as exc:
            key = role
            if key not in self._warned:
                self._warned.add(key)
                print(f"[typography] warning: fallback default font role={role} size={sz} err={exc}")
            return pygame.font.Font(None, sz)

    def apply_to_app(self, app):
        """Attach role fonts to app plus legacy aliases for compatibility."""
        app.typography = self
        app.font = self.get(LORE_FONT, FONT_SECTION)
        app.small_font = self.get(LORE_FONT, FONT_LABEL)
        app.tiny_font = self.get(SMALL_FONT, FONT_SMALL)
        app.big_font = self.get(TITLE_FONT, 40)
        app.card_text_font = self.get(LORE_FONT, 20)
        app.card_title_font = self.get(TITLE_FONT, 28)
        app.map_font = self.get(HUD_FONT, FONT_SECTION)
        app.button_font = self.get(BUTTON_FONT, FONT_SECTION)
        app.hud_font = self.get(HUD_FONT, 30)
        app.lore_font = self.get(LORE_FONT, FONT_SECTION)
        app.title_font = self.get(TITLE_FONT, 72)
        app.font_registry = {ctx: self.get(role, sz) for ctx, (role, sz) in CONTEXT_FONT_SIZES.items()}
