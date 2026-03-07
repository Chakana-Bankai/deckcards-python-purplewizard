import json
from pathlib import Path

import pygame

from game.ui.components.modal_confirm import ModalConfirm
from game.ui.system.brand import ChakanaBrand
from game.ui.system.colors import UColors
from game.ui.system.components import UIButton, UIPanel
from game.ui.system.fonts import get_title_font, get_ui_font
from game.ui.ui_layout import centered_column


DEFAULT_VERSION_LINE = "v0.0.0-dev"


class MenuScreen:
    def __init__(self, app):
        self.app = app
        rects = centered_column(5, width=440, height=66, gap=14, y_start=280)
        self.buttons = [
            {"rect": pygame.Rect(rects[0]), "text_key": "menu_play", "cb": self.start_run, "key": "menu_new"},
            {"rect": pygame.Rect(rects[1]), "text_key": "menu_continue", "cb": self.continue_run, "key": "menu_continue"},
            {"rect": pygame.Rect(rects[2]), "text_key": "menu_back", "cb": self.go_back, "key": "menu_back"},
            {"rect": pygame.Rect(rects[3]), "text_key": "menu_settings", "cb": self.open_settings, "key": "menu_settings"},
            {"rect": pygame.Rect(rects[4]), "text_key": "menu_exit", "cb": self.exit_game, "key": "menu_quit"},
        ]
        self.modal = ModalConfirm()
        self.version_line = self._load_version_line()
        self.title_font = get_title_font(max(48, ChakanaBrand.TITLE_FONT_SIZE))
        self.button_font = get_ui_font(24)
        self.meta_font = get_ui_font(18)

    def _load_version_line(self):
        path = Path(__file__).resolve().parents[2] / "data" / "version.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return DEFAULT_VERSION_LINE
            version = str(payload.get("version") or "").strip()
            build = str(payload.get("build") or "").strip()
            date = str(payload.get("date") or "").strip()
            if not version:
                return DEFAULT_VERSION_LINE
            line = f"v{version}"
            if build:
                line += f" | {build}"
            if date:
                line += f" | {date}"
            return line
        except Exception:
            return DEFAULT_VERSION_LINE

    def _is_button_visible(self, item, index):
        bkey = item.get("key")
        if (bkey == "menu_continue" or (bkey is None and index == 1)) and not self.app.run_state:
            return False
        if (bkey == "menu_back" or (bkey is None and index == 2)) and self.app.menu_return_screen is None:
            return False
        return True

    def start_run(self):
        self.modal.show("Se iniciara un nuevo viaje.", on_yes=self.app.new_run)

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
        self.modal.show("Salir del juego?", on_yes=lambda: setattr(self.app, "running", False))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.modal.open:
                self.modal.handle_event(pos)
                return
            for i, item in enumerate(self.buttons):
                if not self._is_button_visible(item, i):
                    continue
                if item["rect"].collidepoint(pos):
                    item["cb"]()
                    self.app.sfx.play("ui_click")
                    return

    def update(self, dt):
        pass

    def render(self, surface):
        self.app.bg_gen.render_parallax(surface, "Ruinas Chakana", 2026, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        title_rect = pygame.Rect(220, 36, 1480, 132)
        UIPanel(title_rect, variant="alt").draw(surface)
        title = self.title_font.render(self.app.design_value("CANON_MENU_TITLE", "CHAKANA: Purple Wizard"), True, UColors.HARMONY)
        surface.blit(title, title.get_rect(center=(960, 102)))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, item in enumerate(self.buttons):
            if not self._is_button_visible(item, i):
                continue
            label = self.app.loc.t(item["text_key"])
            btn = UIButton(item["rect"], label, role="end_turn", premium=True)
            btn.draw(surface, self.button_font, hovered=item["rect"].collidepoint(mouse))

        surface.blit(self.meta_font.render(self.version_line, True, UColors.MUTED), (24, 1048))
        self.modal.render(surface, self.button_font, self.app.small_font)
