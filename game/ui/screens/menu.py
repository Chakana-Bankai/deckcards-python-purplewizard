import pygame

from game.ui.theme import UI_THEME
from game.ui.ui_layout import centered_column
from game.ui.widgets import Button


class MenuScreen:
    def __init__(self, app):
        self.app = app
        rects = centered_column(5, width=420, height=70, gap=18, y_start=230)
        self.buttons = [
            Button(rects[0], "menu_play", self.start_run),
            Button(rects[1], "menu_continue", self.continue_run),
            Button(rects[2], "menu_qa", self.open_qa),
            Button(rects[3], "menu_settings", self.open_settings),
            Button(rects[4], "menu_exit", self.exit_game),
        ]

    def on_enter(self):
        pass

    def start_run(self):
        self.app.set_debug(last_ui_event="menu:start")
        self.app.new_run()

    def continue_run(self):
        if self.app.run_state:
            self.app.goto_map()
        else:
            self.app.new_run()

    def open_qa(self):
        self.app.run_qa_mode()

    def open_settings(self):
        self.app.set_debug(last_ui_event="menu:settings")
        self.app.goto_settings()

    def exit_game(self):
        self.app.running = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for b in self.buttons:
                if b.handle_click(pos):
                    self.app.sfx.play("ui_click")

    def update(self, dt):
        pass

    def render(self, surface):
        surface.fill(UI_THEME["bg"])
        title = self.app.big_font.render(self.app.loc.t("game_title"), True, UI_THEME["text"])
        surface.blit(title, title.get_rect(center=(960, 110)))
        hint = self.app.font.render(self.app.loc.t("menu_language_hint"), True, UI_THEME["muted"])
        surface.blit(hint, hint.get_rect(center=(960, 170)))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for b in self.buttons:
            b.draw(surface, self.app.font, self.app.loc, UI_THEME, b.rect.collidepoint(mouse))
