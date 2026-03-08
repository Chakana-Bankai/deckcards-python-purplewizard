from __future__ import annotations

import pygame

from game.ui.components.card_framework import CARD_SIZE_MODAL, CARD_SIZE_PREVIEW, fit_card_rect
from game.ui.components.card_renderer import render_card_preview
from game.ui.theme import UI_THEME


class CardPreviewPanel:
    def __init__(self, rect=None, fonts=None, theme=None, app=None):
        self.rect = rect
        self.fonts = fonts or {}
        self.theme = theme or UI_THEME
        self.app = app
        self._card = None
        self._summary = None
        self._art = None

    def set_card(self, card_instance_or_def, summary_dict=None, art_surface=None):
        self._card = card_instance_or_def
        self._summary = summary_dict
        self._art = art_surface

    def clear(self):
        self._card = None
        self._summary = None
        self._art = None

    def set_card_safe(self, card, app=None, ctx=None):
        _ = ctx
        if app is not None:
            self.app = app
        if card is None:
            self.clear()
            return
        self._card = card

    def render(self, surface: pygame.Surface, rect: pygame.Rect | None = None, card=None, app=None):
        try:
            if app is not None:
                self.app = app
            if rect is None:
                rect = self.rect
            if rect is None:
                return
            if card is not None:
                self.set_card_safe(card, app=self.app)

            panel = pygame.Rect(rect)
            pygame.draw.rect(surface, self.theme["panel"], panel, border_radius=12)
            pygame.draw.rect(surface, self.theme["accent_violet"], panel, 2, border_radius=12)

            if self.app is not None:
                surface.blit(self.app.small_font.render("Previsualizacion", True, self.theme["gold"]), (panel.x + 14, panel.y + 12))

            if self._card is None:
                if self.app is not None:
                    surface.blit(self.app.tiny_font.render("Pasa el cursor sobre una carta.", True, self.theme["muted"]), (panel.x + 14, panel.y + 40))
                return

            # Framework lock: preview/modal sizes with strict contained fit (no stretch).
            card_area = panel.inflate(-28, -52)
            card_area.y += 18
            card_area.h = max(120, card_area.h - 18)
            if card_area.h <= 0 or card_area.w <= 0:
                return

            target_size = CARD_SIZE_MODAL if card_area.h >= 760 else CARD_SIZE_PREVIEW
            card_rect = fit_card_rect(card_area, target_size)

            render_card_preview(
                surface,
                card_rect,
                self._card,
                theme=self.theme,
                state={"app": self.app, "ctx": None, "selected": False, "hovered": False},
            )
        except Exception:
            if rect is None:
                return
            pygame.draw.rect(surface, self.theme.get("panel", (30, 24, 44)), rect, border_radius=12)
            pygame.draw.rect(surface, self.theme.get("accent_violet", (120, 80, 170)), rect, 2, border_radius=12)
            if self.app is not None:
                surface.blit(self.app.small_font.render("Preview no disponible", True, self.theme.get("muted", (180, 170, 200))), (rect.x + 14, rect.y + 14))
