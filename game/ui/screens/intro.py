import pygame

from game.ui.theme import UI_THEME


class IntroScreen:
    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.duration = 12.0
        self.text = "Era una vez un Mago Morado llamado Chakana..."

    def on_enter(self):
        self.t = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = self.duration

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.app.goto_menu()

    def render(self, s):
        s.fill((8, 8, 14))
        s.blit(self.app.big_font.render("CRÓNICA DE CHAKANA", True, UI_THEME["gold"]), (650, 300))
        s.blit(self.app.font.render(self.text, True, UI_THEME["text"]), (420, 420))
