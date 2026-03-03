import pygame

from game.ui.theme import UI_THEME


class SettingsScreen:
    def __init__(self, app):
        self.app = app
        self.back_rect = pygame.Rect(520, 600, 220, 58)
        self.lang_rect = pygame.Rect(420, 230, 440, 70)
        self.full_rect = pygame.Rect(420, 330, 440, 70)
        self.slider = pygame.Rect(420, 440, 440, 18)
        self.knob_w = 18

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
            if event.key == pygame.K_F1:
                self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_rect.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.goto_menu()
            elif self.lang_rect.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.toggle_language()
            elif self.full_rect.collidepoint(pos):
                self.app.sfx.play("ui_click")
                self.app.renderer.toggle_fullscreen()
            elif self.slider.inflate(0, 18).collidepoint(pos):
                self._set_slider(pos[0])
        if event.type == pygame.MOUSEMOTION and event.buttons[0]:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.slider.inflate(0, 18).collidepoint(pos):
                self._set_slider(pos[0])

    def _set_slider(self, x):
        t = (x - self.slider.x) / self.slider.w
        self.app.sfx.set_volume(t)

    def update(self, dt):
        pass

    def render(self, surface):
        surface.fill(UI_THEME["bg"])
        title = self.app.big_font.render(self.app.loc.t("settings_title"), True, UI_THEME["text"])
        surface.blit(title, (500, 120))
        pygame.draw.rect(surface, UI_THEME["panel"], self.lang_rect, border_radius=10)
        lang_name = self.app.loc.t("lang_es") if self.app.loc.current_lang == "es" else self.app.loc.t("lang_en")
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_language')}: {lang_name}", True, UI_THEME["text"]), (440, 255))
        pygame.draw.rect(surface, UI_THEME["panel"], self.full_rect, border_radius=10)
        fs = "ON" if self.app.renderer.fullscreen else "OFF"
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_fullscreen')}: {fs}", True, UI_THEME["text"]), (440, 355))
        surface.blit(self.app.font.render(self.app.loc.t("settings_sfx"), True, UI_THEME["text"]), (420, 405))
        pygame.draw.rect(surface, UI_THEME["panel_2"], self.slider, border_radius=8)
        kx = self.slider.x + int(self.slider.w * self.app.sfx.master_volume) - self.knob_w // 2
        pygame.draw.rect(surface, UI_THEME["rupture"], (kx, self.slider.y - 6, self.knob_w, 30), border_radius=4)
        pygame.draw.rect(surface, UI_THEME["panel"], self.back_rect, border_radius=10)
        surface.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (600, 617))
