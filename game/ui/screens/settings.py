import pygame

from game.ui.theme import UI_THEME


class SettingsScreen:
    def __init__(self, app):
        self.app = app
        self.back_rect = pygame.Rect(520, 850, 220, 50)
        self.lang_rect = pygame.Rect(360, 170, 600, 60)
        self.full_rect = pygame.Rect(360, 242, 600, 60)
        self.sfx_slider = pygame.Rect(360, 330, 600, 14)
        self.music_slider = pygame.Rect(360, 400, 600, 14)
        self.mute_rect = pygame.Rect(360, 450, 600, 50)
        self.timer_rect = pygame.Rect(360, 510, 600, 50)
        self.art_regen_rect = pygame.Rect(1020, 220, 540, 64)
        self.art_wipe_regen_rect = pygame.Rect(1020, 300, 540, 64)
        self.music_regen_rect = pygame.Rect(1020, 380, 540, 64)
        self.dev_reset_rect = pygame.Rect(1020, 460, 540, 64)
        self.modal = None
        self.progress = ""

    def on_enter(self):
        pass

    def _set_slider(self, x, slider, setter):
        t = (x - slider.x) / slider.w
        setter(max(0.0, min(1.0, t)))

    def _run_action(self, action):
        self.progress = "Procesando..."
        if action == "art":
            self.app.regenerate_card_art()
        elif action == "art_wipe":
            self.app.regenerate_card_art_with_cleanup()
        elif action == "music":
            self.app.regenerate_music()
        self.progress = "Listo"
        self.modal = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.modal:
                self.modal = None
                return
            self.app.save_user_settings()
            self.app.goto_menu()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.modal:
                yes = pygame.Rect(760, 560, 180, 60)
                no = pygame.Rect(980, 560, 180, 60)
                if yes.collidepoint(pos):
                    self._run_action(self.modal)
                elif no.collidepoint(pos):
                    self.modal = None
                return
            if self.back_rect.collidepoint(pos):
                self.app.save_user_settings()
                self.app.goto_menu()
            elif self.lang_rect.collidepoint(pos):
                self.app.toggle_language()
                self.app.user_settings["language"] = self.app.loc.current_lang
            elif self.full_rect.collidepoint(pos):
                self.app.renderer.toggle_fullscreen()
                self.app.user_settings["fullscreen"] = self.app.renderer.fullscreen
            elif self.sfx_slider.inflate(0, 16).collidepoint(pos):
                self._set_slider(pos[0], self.sfx_slider, self.app.sfx.set_volume)
                self.app.user_settings["sfx_volume"] = self.app.sfx.master_volume
            elif self.music_slider.inflate(0, 16).collidepoint(pos):
                self._set_slider(pos[0], self.music_slider, self.app.music.set_volume)
                self.app.user_settings["music_volume"] = self.app.music.volume
            elif self.mute_rect.collidepoint(pos):
                v = not self.app.user_settings.get("music_muted", False)
                self.app.music.set_muted(v)
                self.app.user_settings["music_muted"] = v
                self.app.user_settings["music_mute"] = v
                if self.app.run_state:
                    self.app.run_state["settings"]["music_muted"] = v
            elif self.timer_rect.collidepoint(pos):
                cur = self.app.user_settings.get("turn_timer_enabled", False)
                self.app.user_settings["turn_timer_enabled"] = not cur
                if self.app.run_state:
                    self.app.run_state["settings"]["turn_timer_enabled"] = not cur
            elif self.art_regen_rect.collidepoint(pos):
                self.modal = "art"
            elif self.art_wipe_regen_rect.collidepoint(pos):
                self.modal = "art_wipe"
            elif self.music_regen_rect.collidepoint(pos):
                self.modal = "music"
            elif self.dev_reset_rect.collidepoint(pos):
                v = not self.app.user_settings.get("dev_reset_autogen_on_boot", False)
                self.app.user_settings["dev_reset_autogen_on_boot"] = v
                self.progress = "Dev reset ON para próximo arranque" if v else "Dev reset OFF"

    def update(self, dt):
        pass

    def _draw_slider(self, surface, yrect, value):
        pygame.draw.rect(surface, UI_THEME["panel_2"], yrect, border_radius=7)
        kx = yrect.x + int(yrect.w * value)
        pygame.draw.circle(surface, UI_THEME["rupture"], (kx, yrect.y + yrect.h // 2), 10)

    def _draw_btn(self, s, rect, label):
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=10)
        s.blit(self.app.small_font.render(label, True, UI_THEME["text"]), (rect.x + 16, rect.y + 20))

    def render(self, surface):
        surface.fill(UI_THEME["bg"])
        surface.blit(self.app.big_font.render(self.app.loc.t("settings_title"), True, UI_THEME["text"]), (500, 90))
        pygame.draw.rect(surface, UI_THEME["panel"], self.lang_rect, border_radius=10)
        lang_name = self.app.loc.t("lang_es") if self.app.loc.current_lang == "es" else self.app.loc.t("lang_en")
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_language')}: {lang_name}", True, UI_THEME["text"]), (380, 188))
        pygame.draw.rect(surface, UI_THEME["panel"], self.full_rect, border_radius=10)
        fs = self.app.user_settings.get("fullscreen", False)
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_fullscreen')}: {self.app.loc.t('settings_on') if fs else self.app.loc.t('settings_off')}", True, UI_THEME["text"]), (380, 260))
        surface.blit(self.app.font.render(self.app.loc.t("settings_sfx"), True, UI_THEME["text"]), (360, 306))
        self._draw_slider(surface, self.sfx_slider, self.app.sfx.master_volume)
        surface.blit(self.app.font.render(self.app.loc.t("settings_music"), True, UI_THEME["text"]), (360, 376))
        self._draw_slider(surface, self.music_slider, self.app.music.volume)
        pygame.draw.rect(surface, UI_THEME["panel"], self.mute_rect, border_radius=10)
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_music_mute')}: {self.app.loc.t('settings_on') if self.app.music.muted else self.app.loc.t('settings_off')}", True, UI_THEME["text"]), (380, 464))
        pygame.draw.rect(surface, UI_THEME["panel"], self.timer_rect, border_radius=10)
        timer_on = self.app.user_settings.get("turn_timer_enabled", False)
        surface.blit(self.app.font.render(f"{self.app.loc.t('settings_timer')}: {self.app.loc.t('settings_on') if timer_on else self.app.loc.t('settings_off')}", True, UI_THEME["text"]), (380, 524))
        self._draw_btn(surface, self.art_regen_rect, "Regenerar Arte de Cartas (prompts nuevos)")
        self._draw_btn(surface, self.art_wipe_regen_rect, "Borrar arte actual de cartas y regenerar")
        self._draw_btn(surface, self.music_regen_rect, "Regenerar Banda Sonora")
        st = "ON" if self.app.user_settings.get("dev_reset_autogen_on_boot", False) else "OFF"
        self._draw_btn(surface, self.dev_reset_rect, f"Dev reset auto-assets al boot: {st}")
        if self.progress:
            surface.blit(self.app.small_font.render(self.progress, True, UI_THEME["gold"]), (1040, 470))
        pygame.draw.rect(surface, UI_THEME["panel"], self.back_rect, border_radius=10)
        surface.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (600, 864))

        if self.modal:
            overlay = pygame.Surface((1920, 1080), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            surface.blit(overlay, (0, 0))
            m = pygame.Rect(660, 430, 600, 240)
            pygame.draw.rect(surface, UI_THEME["deep_purple"], m, border_radius=14)
            pygame.draw.rect(surface, UI_THEME["gold"], m, 2, border_radius=14)
            surface.blit(self.app.font.render("¿Confirmar acción?", True, UI_THEME["text"]), (820, 480))
            yes = pygame.Rect(760, 560, 180, 60)
            no = pygame.Rect(980, 560, 180, 60)
            pygame.draw.rect(surface, UI_THEME["violet"], yes, border_radius=10)
            pygame.draw.rect(surface, UI_THEME["panel_2"], no, border_radius=10)
            surface.blit(self.app.small_font.render("Confirmar", True, UI_THEME["text"]), (790, 580))
            surface.blit(self.app.small_font.render("Cancelar", True, UI_THEME["text"]), (1020, 580))
