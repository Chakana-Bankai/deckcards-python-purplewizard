from __future__ import annotations

import pygame

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

    def _payload(self, card):
        if card is None:
            return None, None
        if hasattr(card, "definition"):
            payload = {
                "id": getattr(card.definition, "id", "carta"),
                "name_key": getattr(card.definition, "name_key", "carta"),
                "text_key": getattr(card.definition, "text_key", ""),
                "rarity": getattr(card.definition, "rarity", "common"),
                "cost": getattr(card, "cost", getattr(card.definition, "cost", 0)),
                "tags": list(getattr(card.definition, "tags", []) or []),
                "effects": list(getattr(card.definition, "effects", []) or []),
            }
            return payload, card
        if isinstance(card, dict):
            return card, None
        return None, None

    def _icon_row(self, summary: dict):
        stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
        icon_data = []
        if stats.get("damage", 0) > 0:
            icon_data.append(("sword", stats.get("damage", 0)))
        if stats.get("block", 0) > 0:
            icon_data.append(("shield", stats.get("block", 0)))
        if stats.get("rupture", 0) > 0:
            icon_data.append(("crack", stats.get("rupture", 0)))
        if stats.get("harmony_delta", 0) > 0 or stats.get("harmony", 0) > 0:
            icon_data.append(("star", stats.get("harmony_delta", stats.get("harmony", 0))))
        if stats.get("scry", 0) > 0:
            icon_data.append(("eye", stats.get("scry", 0)))
        if stats.get("draw", 0) > 0:
            icon_data.append(("scroll", stats.get("draw", 0)))
        return icon_data[:3]

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

            # Preserve aspect ratio strictly to avoid stretched/distorted preview cards.
            card_area = panel.inflate(-28, -52)
            card_area.y += 18
            card_area.h = max(120, card_area.h - 18)
            target_ratio = 0.72  # width / height
            if card_area.h <= 0 or card_area.w <= 0:
                return

            fitted_w = min(card_area.w, int(card_area.h * target_ratio))
            fitted_h = int(fitted_w / target_ratio)
            if fitted_h > card_area.h:
                fitted_h = card_area.h
                fitted_w = int(fitted_h * target_ratio)

            card_rect = pygame.Rect(0, 0, max(90, fitted_w), max(120, fitted_h))
            card_rect.center = card_area.center

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
