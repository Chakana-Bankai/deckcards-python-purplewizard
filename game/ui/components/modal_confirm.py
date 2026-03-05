from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class ModalConfirm:
    def __init__(self):
        self.open = False
        self.message = ""
        self.on_yes = None
        self.on_no = None
        self.panel = pygame.Rect(620, 420, 680, 240)
        self.yes = pygame.Rect(760, 560, 180, 60)
        self.no = pygame.Rect(980, 560, 180, 60)

    def show(self, message: str, on_yes=None, on_no=None):
        self.open = True
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no

    def handle_event(self, pos):
        if not self.open:
            return False
        if self.yes.collidepoint(pos):
            cb = self.on_yes
            self.open = False
            if callable(cb):
                cb()
            return True
        if self.no.collidepoint(pos):
            cb = self.on_no
            self.open = False
            if callable(cb):
                cb()
            return True
        return True

    def render(self, surface, font, small_font):
        if not self.open:
            return
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        surface.blit(ov, (0, 0))
        pygame.draw.rect(surface, UI_THEME["deep_purple"], self.panel, border_radius=14)
        pygame.draw.rect(surface, UI_THEME["gold"], self.panel, 2, border_radius=14)
        surface.blit(font.render("¿Confirmar acción?", True, UI_THEME["text"]), (self.panel.x + 170, self.panel.y + 44))
        surface.blit(small_font.render(self.message, True, UI_THEME["muted"]), (self.panel.x + 36, self.panel.y + 92))
        pygame.draw.rect(surface, UI_THEME["violet"], self.yes, border_radius=10)
        pygame.draw.rect(surface, UI_THEME["panel_2"], self.no, border_radius=10)
        surface.blit(small_font.render("Confirmar", True, UI_THEME["text"]), (self.yes.x + 30, self.yes.y + 20))
        surface.blit(small_font.render("Cancelar", True, UI_THEME["text"]), (self.no.x + 36, self.no.y + 20))
