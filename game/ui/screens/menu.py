import pygame

from game.ui.ui_layout import centered_column
from game.ui.widgets import Button
from game.settings import COLORS


class MenuScreen:
    def __init__(self, app):
        self.app = app
        rects = centered_column(4)
        self.buttons = [
            Button(rects[0], "menu_play", self.start_run),
            Button(rects[1], "menu_settings", self.toggle_language),
            Button(rects[2], "menu_continue", self.continue_run),
            Button(rects[3], "menu_exit", self.exit_game),
        ]

    def on_enter(self):
        pass

    def start_run(self):
        self.app.new_run()

    def toggle_language(self):
        self.app.toggle_language()

    def continue_run(self):
        self.app.goto_map()

    def exit_game(self):
        self.app.running = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for b in self.buttons:
                if b.handle_click(pos):
                    self.app.sfx.play("ui_click")
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()

    def update(self, dt):
        pass

    def render(self, surface):
        surface.fill(COLORS["bg"])
        title = self.app.big_font.render(self.app.loc.t("game_title"), True, COLORS["text"])
        surface.blit(title, (80, 80))
        hint = self.app.font.render(self.app.loc.t("menu_language_hint"), True, COLORS["muted"])
        surface.blit(hint, (80, 130))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for b in self.buttons:
            b.draw(surface, self.app.font, self.app.loc, COLORS, b.rect.collidepoint(mouse))
