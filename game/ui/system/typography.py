"""Centralized typography roles, sizes and semantic text colors."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

import pygame

from .fonts import get_lore_font, get_pixel_font, get_title_font, get_ui_font
from .ui_scale_system import FONT_CONTEXT_SIZES, FONT_LABEL, FONT_SECTION, FONT_SMALL, FONT_TITLE

TITLE_FONT = "TITLE_FONT"
HUD_FONT = "HUD_FONT"
LORE_FONT = "LORE_FONT"
PIXEL_FONT = "PIXEL_FONT"
SMALL_FONT = "SMALL_FONT"
BUTTON_FONT = "BUTTON_FONT"

CONTEXT_FONT_SIZES: Dict[str, tuple[str, int]] = {
    "menu_title": (TITLE_FONT, FONT_CONTEXT_SIZES["menu_title"]),
    "menu_label": (HUD_FONT, FONT_CONTEXT_SIZES["menu_label"]),
    "combat_title": (TITLE_FONT, FONT_CONTEXT_SIZES["combat_title"]),
    "combat_label": (HUD_FONT, FONT_CONTEXT_SIZES["combat_label"]),
    "combat_value": (HUD_FONT, FONT_CONTEXT_SIZES["combat_value"]),
    "combat_labels": (HUD_FONT, 24),
    "hud_numbers": (HUD_FONT, 30),
    "hud_value": (HUD_FONT, FONT_CONTEXT_SIZES["hud_value"]),
    "modal_title": (TITLE_FONT, FONT_CONTEXT_SIZES["modal_title"]),
    "modal_label": (HUD_FONT, FONT_CONTEXT_SIZES["modal_label"]),
    "card_titles": (TITLE_FONT, FONT_CONTEXT_SIZES["card_title"]),
    "card_title": (TITLE_FONT, FONT_CONTEXT_SIZES["card_title"]),
    "card_type": (HUD_FONT, FONT_CONTEXT_SIZES["card_type"]),
    "card_effect": (LORE_FONT, FONT_CONTEXT_SIZES["card_effect"]),
    "card_body": (LORE_FONT, 22),
    "card_lore": (LORE_FONT, FONT_CONTEXT_SIZES["card_lore"]),
    "card_footer": (LORE_FONT, FONT_CONTEXT_SIZES["card_footer"]),
    "lore_text": (LORE_FONT, 22),
    "codex_header": (TITLE_FONT, FONT_CONTEXT_SIZES["codex_header"]),
    "codex_headers": (TITLE_FONT, FONT_CONTEXT_SIZES["codex_header"]),
    "map_title": (TITLE_FONT, FONT_CONTEXT_SIZES["map_title"]),
    "map_label": (HUD_FONT, FONT_CONTEXT_SIZES["map_label"]),
    "map_labels": (HUD_FONT, FONT_CONTEXT_SIZES["map_label"]),
    "shop_header": (TITLE_FONT, FONT_CONTEXT_SIZES["shop_header"]),
    "shop_headers": (TITLE_FONT, FONT_CONTEXT_SIZES["shop_header"]),
    "special_pixel_label": (PIXEL_FONT, FONT_CONTEXT_SIZES["special_pixel_label"]),
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
        PIXEL_FONT: FONT_LABEL,
        SMALL_FONT: FONT_LABEL,
        BUTTON_FONT: FONT_SECTION,
    }

    def __init__(self):
        self.palette = TypographyPalette()
        self._warned: set[str] = set()
        self._debug = str(os.environ.get("CHAKANA_FONT_DEBUG", "0")).strip().lower() in {"1", "true", "yes"}

    def get(self, role: str, size: int | None = None) -> pygame.font.Font:
        if not pygame.font.get_init():
            pygame.font.init()
        sz = int(size if size is not None else self.DEFAULT_SIZES.get(role, FONT_SECTION))
        try:
            if role == TITLE_FONT:
                return get_title_font(sz)
            if role == LORE_FONT:
                return get_lore_font(sz)
            if role == PIXEL_FONT:
                return get_pixel_font(sz)
            return get_ui_font(sz)
        except Exception as exc:
            key = role
            if key not in self._warned:
                self._warned.add(key)
                print(f"[typography] warning: fallback default font role={role} size={sz} err={exc}")
            return pygame.font.Font(None, sz)

    def for_context(self, app, context: str, fallback_attr: str = "small_font") -> pygame.font.Font:
        reg = getattr(app, "font_registry", {}) or {}
        font = reg.get(str(context or ""))
        if font is not None:
            return font
        return getattr(app, fallback_attr, getattr(app, "font", pygame.font.Font(None, FONT_SECTION)))

    def apply_to_app(self, app):
        """Attach role fonts to app plus legacy aliases for compatibility."""
        app.typography = self
        app.font = self.get(LORE_FONT, FONT_SECTION)
        app.small_font = self.get(LORE_FONT, FONT_LABEL + 3)
        app.tiny_font = self.get(SMALL_FONT, FONT_SMALL + 2)
        app.big_font = self.get(TITLE_FONT, 48)
        app.card_text_font = self.get(LORE_FONT, 22)
        app.card_title_font = self.get(TITLE_FONT, 28)
        app.map_font = self.get(HUD_FONT, FONT_SECTION)
        app.button_font = self.get(BUTTON_FONT, FONT_SECTION)
        app.hud_font = self.get(HUD_FONT, 30)
        app.lore_font = self.get(LORE_FONT, FONT_SECTION)
        app.title_font = self.get(TITLE_FONT, 72)
        app.special_pixel_font = self.get(PIXEL_FONT, FONT_CONTEXT_SIZES["special_pixel_label"])
        app.font_registry = {ctx: self.get(role, sz) for ctx, (role, sz) in CONTEXT_FONT_SIZES.items()}
        app.get_font_context = lambda context, fallback_attr="small_font": self.for_context(app, context, fallback_attr)
        if self._debug:
            for ctx, font in sorted(app.font_registry.items()):
                print(f"[typography] context={ctx} size={font.get_height()}")
