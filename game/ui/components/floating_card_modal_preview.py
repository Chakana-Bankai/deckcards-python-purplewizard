from __future__ import annotations

import pygame

from game.ui.components.card_renderer import render_card_preview
from game.ui.theme import UI_THEME


class FloatingCardModalPreview:
    """Lightweight floating card inspect modal for hover contexts."""

    def __init__(self):
        self.rect = pygame.Rect(0, 0, 1, 1)

    def render(self, surface: pygame.Surface, app, card, title: str = "", dim_alpha: int = 96):
        if card is None:
            return
        if dim_alpha > 0:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((8, 8, 12, max(0, min(180, int(dim_alpha)))))
            surface.blit(veil, (0, 0))

        panel_w, panel_h = 620, 860
        self.rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.rect.center = (surface.get_width() // 2, surface.get_height() // 2 + 12)

        pygame.draw.rect(surface, UI_THEME["panel"], self.rect, border_radius=14)
        pygame.draw.rect(surface, UI_THEME["gold"], self.rect, 2, border_radius=14)

        if title:
            lbl = app.small_font.render(str(title), True, UI_THEME["gold"])
            surface.blit(lbl, (self.rect.x + 16, self.rect.y + 12))

        card_rect = self.rect.inflate(-36, -54)
        card_rect.y += 18
        card_rect.h -= 10
        render_card_preview(
            surface,
            card_rect,
            card,
            theme=UI_THEME,
            state={"app": app, "ctx": None, "selected": False, "hovered": True, "render_context": "archetype_preview"},
        )
