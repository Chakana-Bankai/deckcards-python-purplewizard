import pygame


class Button:
    def __init__(self, rect, text_key, callback):
        self.rect = pygame.Rect(rect)
        self.text_key = text_key
        self.callback = callback

    def draw(self, surf, font, loc, colors, hovered=False):
        pygame.draw.rect(surf, colors["violet"] if hovered else colors["panel"], self.rect, border_radius=8)
        label = font.render(loc.t(self.text_key), True, colors["text"])
        surf.blit(label, label.get_rect(center=self.rect.center))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()
            return True
        return False
