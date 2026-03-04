from game.version import VERSION
import pygame

from game.ui.components.modal_confirm import ModalConfirm
from game.ui.theme import UI_THEME
from game.ui.ui_layout import centered_column
from game.ui.widgets import Button


class MenuScreen:
    def __init__(self, app):
        self.app = app
        rects = centered_column(5, width=440, height=66, gap=14, y_start=280)
        self.buttons = [
            Button(rects[0], "menu_play", self.start_run, key="menu_new"),
            Button(rects[1], "menu_continue", self.continue_run, key="menu_continue"),
            Button(rects[2], "menu_back", self.go_back, key="menu_back"),
            Button(rects[3], "menu_settings", self.open_settings, key="menu_settings"),
            Button(rects[4], "menu_exit", self.exit_game, key="menu_quit"),
        ]
        self.modal = ModalConfirm()

    def _is_button_visible(self, button, index):
        bkey = getattr(button, "key", None)
        if (bkey == "menu_continue" or (bkey is None and index == 1)) and not self.app.run_state:
            return False
        if (bkey == "menu_back" or (bkey is None and index == 2)) and self.app.menu_return_screen is None:
            return False
        return True

    def start_run(self):
        self.modal.show("Se iniciará un nuevo viaje.", on_yes=self.app.new_run)

    def continue_run(self):
        if self.app.run_state:
            self.app.goto_map()

    def go_back(self):
        if self.app.menu_return_screen is not None:
            self.app.sm.set(self.app.menu_return_screen)
            self.app.menu_return_screen = None

    def open_settings(self):
        self.app.goto_settings()

    def exit_game(self):
        self.modal.show("¿Salir del juego?", on_yes=lambda: setattr(self.app, "running", False))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.modal.open:
                self.modal.handle_event(pos)
                return
            for i, b in enumerate(self.buttons):
                if not self._is_button_visible(b, i):
                    continue
                if b.handle_click(pos):
                    self.app.sfx.play("ui_click")

    def update(self, dt):
        pass

    def render(self, surface):
        self.app.bg_gen.render_parallax(surface, "Ruinas Chakana", 2026, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        title = self.app.big_font.render(self.app.design_value("CANON_MENU_TITLE", "CHAKANA: Purple Wizard"), True, UI_THEME["gold"])
        surface.blit(title, title.get_rect(center=(960, 112)))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, b in enumerate(self.buttons):
            if not self._is_button_visible(b, i):
                continue
            b.draw(surface, self.app.font, self.app.loc, UI_THEME, b.rect.collidepoint(mouse))

        surface.blit(self.app.small_font.render("Chakana Gaming", True, UI_THEME["text"]), (846, 965))
        surface.blit(self.app.small_font.render(f"v{VERSION} • Chakana Purple Wizard", True, UI_THEME["muted"]), (760, 996))
        self.modal.render(surface, self.app.font, self.app.small_font)
