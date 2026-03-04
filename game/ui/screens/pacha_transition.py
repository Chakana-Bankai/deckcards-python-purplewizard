import pygame

from game.ui.theme import UI_THEME


class PachaTransitionScreen:
    def __init__(self, app, biome_name, next_fn):
        self.app = app
        self.biome_name = biome_name
        self.next_fn = next_fn
        self.t = 0.0

    def on_enter(self):
        self.t = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = 2.1

    def update(self, dt):
        self.t += dt
        if self.t >= 2.0:
            self.next_fn()

    def render(self, s):
        s.fill((10, 8, 18))
        s.blit(self.app.big_font.render("Transición de Pacha", True, UI_THEME["gold"]), (700, 430))
        s.blit(self.app.font.render(self.biome_name, True, UI_THEME["text"]), (860, 500))
