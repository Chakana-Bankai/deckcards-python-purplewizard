"""DEPRECATED: legacy generic Button wrapper.

Use `game.ui.system.components.UIButton` for new UI code.
"""

import pygame


class Button:
    def __init__(self, rect, text_key, callback, key=None, id=None):
        self.rect = pygame.Rect(rect)
        self.text_key = text_key
        self.callback = callback
        self.key = key
        self.id = id

    def draw(self, surf, font, loc, colors, hovered=False):
        color = colors["violet"] if hovered else colors["panel"]
        if hovered:
            color = tuple(min(255, c + 18) for c in color)
        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        pygame.draw.rect(surf, colors["deep_purple"], self.rect, 2, border_radius=10)
        label = font.render(loc.t(self.text_key), True, colors["text"])
        surf.blit(label, label.get_rect(center=self.rect.center))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()
            return True
        return False
