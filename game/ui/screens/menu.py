import json
from pathlib import Path

import pygame

from game.ui.components.modal_confirm import ModalConfirm
from game.ui.system.brand import ChakanaBrand
from game.ui.system.colors import UColors
from game.ui.system.components import UIButton
from game.ui.system.typography import BUTTON_FONT, SMALL_FONT, TITLE_FONT
from game.ui.ui_layout import centered_column


DEFAULT_VERSION_LINE = "v0.0.0-dev"


class MenuScreen:
    def __init__(self, app):
        self.app = app
        rects = centered_column(6, width=440, height=62, gap=12, y_start=252)
        self.buttons = [
            {"rect": pygame.Rect(rects[0]), "text_key": "menu_play", "cb": self.start_run, "key": "menu_new"},
            {"rect": pygame.Rect(rects[1]), "text_key": "menu_continue", "cb": self.continue_run, "key": "menu_continue"},
            {"rect": pygame.Rect(rects[2]), "text_key": "menu_back", "cb": self.go_back, "key": "menu_back"},
            {"rect": pygame.Rect(rects[3]), "text_key": "menu_settings", "cb": self.open_settings, "key": "menu_settings"},
            {"rect": pygame.Rect(rects[4]), "text_key": "menu_codex", "cb": self.open_codex, "key": "menu_codex"},
            {"rect": pygame.Rect(rects[5]), "text_key": "menu_exit", "cb": self.exit_game, "key": "menu_quit"},
        ]
        self.modal = ModalConfirm()
        self.version_line = self._load_version_line()
        self.title_font = self.app.typography.get(TITLE_FONT, max(74, ChakanaBrand.TITLE_FONT_SIZE + 8))
        self.button_font = self.app.typography.get(BUTTON_FONT, 24)
        self.meta_font = self.app.typography.get(SMALL_FONT, 18)

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

    def on_enter(self):
        # Prevent stale modal state from previous menu interactions.
        self.modal.modal.hide()
        self.modal.modal.title = ""
        self.modal.modal.message = ""

    def _confirm_start_run(self):
        self.modal.modal.hide()
        self.app.new_run()

    def start_run(self):
        self.modal.show("Se iniciara un nuevo viaje.", on_yes=self._confirm_start_run)

    def continue_run(self):
        if self.app.run_state:
            self.app.goto_map()

    def go_back(self):
        if self.app.menu_return_screen is not None:
            self.app.sm.set(self.app.menu_return_screen)
            self.app.menu_return_screen = None

    def open_settings(self):
        self.app.goto_settings()

    def open_codex(self):
        self.app.goto_codex()

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

    def _draw_title(self, surface: pygame.Surface, rect: pygame.Rect):
        title_text = "CHAKANA : PURPLE WIZARD"
        palette = self.app.typography.palette

        # Subtle cyan-violet glow layers below title glyphs.
        for dx, dy, col, alpha in [(-3, 2, palette.title_glow, 90), (3, -2, palette.title_glow, 70), (0, 0, palette.hud_harmony, 60)]:
            glow = self.title_font.render(title_text, True, col)
            glow_surf = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
            glow_surf.blit(glow, (0, 0))
            glow_surf.set_alpha(alpha)
            surface.blit(glow_surf, glow_surf.get_rect(center=(rect.centerx + dx, rect.centery + dy + 2)))

        title = self.title_font.render(title_text, True, palette.title_primary)
        surface.blit(title, title.get_rect(center=(rect.centerx, rect.centery + 2)))

    def render(self, surface):
        self.app.bg_gen.render_parallax(surface, "Ruinas Chakana", 2026, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        title_rect = pygame.Rect(160, 20, 1600, 166)

        # Premium header strip: subtle ritual atmosphere, no heavy opaque box.
        strip = pygame.Surface((title_rect.w, title_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(strip, (26, 16, 48, 168), strip.get_rect(), border_radius=18)
        pygame.draw.rect(strip, (184, 140, 255, 84), strip.get_rect(), 1, border_radius=18)
        surface.blit(strip, title_rect.topleft)
        self._draw_title(surface, title_rect)

        portrait = self.app.assets.sprite("avatar", "menu", (132, 132), fallback=(86, 56, 132))
        surface.blit(portrait, (title_rect.x + 20, title_rect.y + 18))
        emblem = self.app.assets.sprite("emblems", "oracle_of_fate", (72, 72), fallback=(96, 74, 136))
        surface.blit(emblem, (title_rect.right - 96, title_rect.y + 28))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, item in enumerate(self.buttons):
            if not self._is_button_visible(item, i):
                continue
            label = self.app.loc.t(item["text_key"])
            btn = UIButton(item["rect"], label, role="menu", premium=True)
            btn.draw(surface, self.button_font, hovered=item["rect"].collidepoint(mouse))

        surface.blit(self.meta_font.render(self.version_line, True, self.app.typography.palette.muted), (24, 1048))
        self.modal.render(surface, self.button_font, self.app.small_font)

