import pygame

from game.ui.theme import UI_THEME


class SettingsScreen:
    def __init__(self, app):
        self.app = app
        self.back_rect = pygame.Rect(520, 640, 220, 50)
        self.lang_rect = pygame.Rect(380, 190, 520, 60)
        self.full_rect = pygame.Rect(380, 265, 520, 60)
        self.sfx_slider = pygame.Rect(380, 350, 520, 14)
        self.music_slider = pygame.Rect(380, 420, 520, 14)
        self.mute_rect = pygame.Rect(380, 470, 520, 50)
        self.timer_rect = pygame.Rect(380, 530, 520, 50)

    def on_enter(self):
        pass

    def _set_slider(self, x, slider, setter):
        t = (x - slider.x) / slider.w
        setter(max(0.0, min(1.0, t)))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_menu()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_rect.collidepoint(pos):
                self.app.goto_menu()
            elif self.lang_rect.collidepoint(pos):
                self.app.toggle_language()
            elif self.full_rect.collidepoint(pos):
                self.app.renderer.toggle_fullscreen()
            elif self.sfx_slider.inflate(0, 16).collidepoint(pos):
                self._set_slider(pos[0], self.sfx_slider, self.app.sfx.set_volume)
            elif self.music_slider.inflate(0, 16).collidepoint(pos):
                self._set_slider(pos[0], self.music_slider, self.app.music.set_volume)
            elif self.mute_rect.collidepoint(pos):
                v = not self.app.run_state.get("settings", {}).get("music_muted", False) if self.app.run_state else not self.app.music.muted
                self.app.music.set_muted(v)
                if self.app.run_state:
                    self.app.run_state["settings"]["music_muted"] = v
            elif self.timer_rect.collidepoint(pos) and self.app.run_state:
                cur = self.app.run_state["settings"].get("timer_on", False)
                self.app.run_state["settings"]["timer_on"] = not cur

    def update(self, dt):
        pass

    def _draw_slider(self, surface, yrect, value):
        pygame.draw.rect(surface, UI_THEME["panel_2"], yrect, border_radius=7)
        kx = yrect.x + int(yrect.w * value)
        pygame.draw.circle(surface, UI_THEME["rupture"], (kx, yrect.y + yrect.h // 2), 10)

    def render(self, surface):
        surface.fill(UI_THEME["bg"])
        surface.blit(self.app.big_font.render(self.app.loc.t("settings_title"), True, UI_THEME["text"]), (500, 110))
        pygame.draw.rect(surface, UI_THEME["panel"], self.lang_rect, border_radius=10)
        lang_name = self.app.loc.t("lang_es") if self.app.loc.current_lang == "es" else self.app.loc.t("lang_en")
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_language')}: {lang_name}", True, UI_THEME["text"]), (400, 208))
        pygame.draw.rect(surface, UI_THEME["panel"], self.full_rect, border_radius=10)
        fs = "ON" if self.app.renderer.fullscreen else "OFF"
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_fullscreen')}: {fs}", True, UI_THEME["text"]), (400, 282))
        surface.blit(self.app.font.render(self.app.loc.t("settings_sfx"), True, UI_THEME["text"]), (380, 326))
        self._draw_slider(surface, self.sfx_slider, self.app.sfx.master_volume)
        surface.blit(self.app.font.render(self.app.loc.t("settings_music"), True, UI_THEME["text"]), (380, 396))
        self._draw_slider(surface, self.music_slider, self.app.music.volume)
        pygame.draw.rect(surface, UI_THEME["panel"], self.mute_rect, border_radius=10)
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_music_mute')}: {self.app.loc.t('settings_on') if self.app.music.muted else self.app.loc.t('settings_off')}", True, UI_THEME["text"]), (400, 484))
        pygame.draw.rect(surface, UI_THEME["panel"], self.timer_rect, border_radius=10)
        timer_on = self.app.run_state.get("settings", {}).get("timer_on", False) if self.app.run_state else False
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_timer')}: {self.app.loc.t('settings_on') if timer_on else self.app.loc.t('settings_off')}", True, UI_THEME["text"]), (400, 544))
        pygame.draw.rect(surface, UI_THEME["panel"], self.back_rect, border_radius=10)
        surface.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (600, 654))
