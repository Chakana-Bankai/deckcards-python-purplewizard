import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event
        self.writer = TypewriterBanner()
        lore_hint = (self.app.lore_data.get("world_text", "")[:220] + "...") if self.app.lore_data.get("world_text") else self.app.loc.t("lore_tagline")
        fr = self.app.content.dialogues_events.get("default", ["La Trama te observa."]) if hasattr(self.app, "content") else ["La Trama te observa."]
        self.lines = [self.app.loc.t(event.get("body_key", "lore_tagline")), lore_hint, fr[0]]
        self.idx = 0
        self.timer = 0
        self.msg = ""
        self.guide_type = self._pick_guide_type(event.get("id", "default"))

    def on_enter(self):
        self.writer.set(self.lines[0], 3.0)

    def _pick_guide_type(self, event_id: str) -> str:
        eid = (event_id or "").lower()
        if any(k in eid for k in ["oracle", "angel", "luz"]): return "angel"
        if any(k in eid for k in ["tribu", "apacheta", "ritual", "shaman"]): return "shaman"
        if any(k in eid for k in ["demon", "sangre", "abyss", "void"]): return "demon"
        if any(k in eid for k in ["hack", "data", "runa", "circuit"]): return "arcane_hacker"
        return ["angel", "shaman", "demon", "arcane_hacker"][abs(hash(eid)) % 4]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            for i, ch in enumerate(self.event["choices"][:3]):
                if pygame.Rect(500, 700 + i * 90, 1340, 70).collidepoint(pos):
                    self.app.apply_event_effects(ch["effects"])
                    self.msg = f"{self.app.loc.t(ch['text_key'])}"
                    self.app._complete_current_node(); self.app.goto_map()

    def update(self, dt):
        self.timer += dt
        if self.timer > 2.6:
            self.timer = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.writer.set(self.lines[self.idx], 2.4)

    def _metaforma(self, s, rect):
        pygame.draw.rect(s, (66, 48, 88), rect, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], rect, 2, border_radius=18)
        inner = rect.inflate(-20, -20)
        pygame.draw.rect(s, (24, 18, 36), inner, border_radius=14)
        for i in range(6):
            pygame.draw.rect(s, (120, 100, 170), (inner.x + 16 + i * 70, inner.y + 12, 38, 6), border_radius=3)

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 2048, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        title = self.app.loc.t(self.event["title_key"])
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (100, 56))

        panel = pygame.Rect(80, 130, 1760, 840)
        self._metaforma(s, panel)

        avatar_frame = pygame.Rect(130, 210, 300, 300)
        pygame.draw.rect(s, (58, 40, 82), avatar_frame, border_radius=14)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_frame, 2, border_radius=14)
        av = self.app.assets.sprite("guides", self.guide_type, (256, 256), fallback=(34, 24, 52))
        s.blit(av, (152, 232))

        text_box = pygame.Rect(470, 210, 1320, 420)
        pygame.draw.rect(s, UI_THEME["panel_2"], text_box, border_radius=12)
        s.blit(self.app.small_font.render(self.app.design_value("CANON_GUIDE_NAME", "Guía espiritual"), True, UI_THEME["muted"]), (500, 240))
        lines = self.writer.current.split("\n")
        y = 286
        for ln in lines[:8]:
            s.blit(self.app.font.render(ln, True, UI_THEME["text"]), (500, y)); y += 36

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, ch in enumerate(self.event["choices"][:3]):
            r = pygame.Rect(500, 700 + i * 90, 1340, 70)
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t(ch["text_key"]), True, UI_THEME["text"]), (530, r.y + 20))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (520, 660))
