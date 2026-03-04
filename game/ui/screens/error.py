import pygame

from game.settings import COLORS


class ErrorScreen:
    def __init__(self, app, message_lines: list[str]):
        self.app = app
        self.lines = message_lines[-18:] if message_lines else ["Unknown error"]

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.app.running = False

    def update(self, dt):
        pass

    def render(self, surface):
        surface.fill((30, 8, 18))
        title = self.app.big_font.render(self.app.loc.t("combat_defeat"), True, COLORS["bad"])
        surface.blit(title, (40, 30))
        y = 90
        for line in self.lines:
            text = self.app.small_font.render(line[:150], True, COLORS["text"])
            surface.blit(text, (40, y))
            y += 28
