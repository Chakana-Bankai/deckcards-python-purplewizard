import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event
        self.writer = TypewriterBanner()
        lore_hint = (self.app.lore_data.get("world_text", "")[:180] + "...") if self.app.lore_data.get("world_text") else self.app.loc.t("lore_tagline")
        fr = self.app.content.dialogues_events.get("default", ["La Trama te observa."]) if hasattr(self.app, "content") else ["La Trama te observa."]
        self.lines = [self.app.loc.t(event.get("body_key", "lore_tagline")), lore_hint, fr[0]]
        self.idx = 0
        self.timer = 0
        self.msg = ""

    def on_enter(self):
        self.writer.set(self.lines[0], 3.0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            for i, ch in enumerate(self.event["choices"][:3]):
                if pygame.Rect(520, 470 + i * 96, 1180, 76).collidepoint(pos):
                    self.app.apply_event_effects(ch["effects"])
                    self.msg = f"{self.app.loc.t(ch['text_key'])}"
                    self.app._complete_current_node(); self.app.goto_map()

    def update(self, dt):
        self.timer += dt
        if self.timer > 2.6:
            self.timer = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.writer.set(self.lines[self.idx], 2.4)

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 2048, pygame.time.get_ticks()*0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        title = self.app.loc.t(self.event["title_key"])
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (140, 70))

        panel = pygame.Rect(120, 150, 1680, 760)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=16)
        pygame.draw.rect(s, UI_THEME["accent_violet"], panel, 2, border_radius=16)

        # guide image top-left
        avatar_frame = pygame.Rect(170, 220, 300, 300)
        pygame.draw.rect(s, (58, 40, 82), avatar_frame, border_radius=14)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_frame, 2, border_radius=14)
        av = pygame.Surface((260, 260)); av.fill((34, 24, 52))
        pygame.draw.circle(av, (188, 150, 230), (130, 80), 56)
        pygame.draw.rect(av, (110, 80, 160), (84, 140, 92, 102), border_radius=18)
        s.blit(av, (190, 240))

        # text right of image
        text_box = pygame.Rect(520, 220, 1180, 200)
        pygame.draw.rect(s, UI_THEME["panel_2"], text_box, border_radius=12)
        s.blit(self.app.small_font.render(self.app.design_value("CANON_GUIDE_NAME", "Guía espiritual"), True, UI_THEME["muted"]), (550, 248))
        s.blit(self.app.font.render(self.writer.current, True, UI_THEME["text"]), (550, 300))

        # buttons below text vertically
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, ch in enumerate(self.event["choices"][:3]):
            r = pygame.Rect(520, 470 + i * 96, 1180, 76)
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t(ch["text_key"]), True, UI_THEME["text"]), (550, r.y + 24))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (540, 820))
