"""Centralized typography roles, sizes and semantic text colors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pygame

from .fonts import get_lore_font, get_title_font, get_ui_font

TITLE_FONT = "TITLE_FONT"
HUD_FONT = "HUD_FONT"
LORE_FONT = "LORE_FONT"
SMALL_FONT = "SMALL_FONT"
BUTTON_FONT = "BUTTON_FONT"


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
        TITLE_FONT: 72,
        HUD_FONT: 30,
        LORE_FONT: 24,
        SMALL_FONT: 18,
        BUTTON_FONT: 24,
    }

    def __init__(self):
        self.palette = TypographyPalette()
        self._warned: set[tuple[str, int]] = set()

    def get(self, role: str, size: int | None = None) -> pygame.font.Font:
        if not pygame.font.get_init():
            pygame.font.init()
        sz = int(size if size is not None else self.DEFAULT_SIZES.get(role, 24))
        try:
            if role == TITLE_FONT:
                return get_title_font(sz)
            if role == LORE_FONT:
                return get_lore_font(sz)
            return get_ui_font(sz)
        except Exception as exc:
            key = (role, sz)
            if key not in self._warned:
                self._warned.add(key)
                print(f"[typography] warning: fallback default font role={role} size={sz} err={exc}")
            return pygame.font.Font(None, sz)

    def apply_to_app(self, app):
        """Attach role fonts to app plus legacy aliases for compatibility."""
        app.typography = self
        app.font = self.get(LORE_FONT, 24)
        app.small_font = self.get(LORE_FONT, 22)
        app.tiny_font = self.get(SMALL_FONT, 18)
        app.big_font = self.get(TITLE_FONT, 40)
        app.card_text_font = self.get(LORE_FONT, 20)
        app.card_title_font = self.get(TITLE_FONT, 28)
        app.map_font = self.get(HUD_FONT, 24)
        app.button_font = self.get(BUTTON_FONT, 24)
        app.hud_font = self.get(HUD_FONT, 30)
        app.lore_font = self.get(LORE_FONT, 24)
        app.title_font = self.get(TITLE_FONT, 72)

