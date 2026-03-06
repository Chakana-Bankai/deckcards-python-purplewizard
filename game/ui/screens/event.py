import pygame

from game.systems.reward_system import build_reward_guide
from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event
        self.writer = TypewriterBanner()
        self.t = 0.0
        self.alpha = 0.0
        self.guide_type = self._pick_guide_type(event.get("id", "default"))
        lore = getattr(self.app, "lore_data", {}) or {}
        defaults = lore.get("event_fragments", ["Toda ruta trae aprendizaje.", "Escucha al guía."])
        self.parabola = defaults[:3] if defaults else ["La Trama te observa."]
        self.moraleja = defaults[0] if defaults else "Moraleja: cada decisión pesa."
        self.msg = ""
        self.guide_names = {"angel": "Oraculo Solar", "shaman": "Amauta de Ceniza", "demon": "Custodio del Vacio", "arcane_hacker": "Arquitecto del Umbral"}
        self._resolved_guide_reward = None

    def on_enter(self):
        self.writer.set("\n".join(self.parabola[:3]), 1.8)

    def _pick_guide_type(self, event_id: str) -> str:
        eid = (event_id or "").lower()
        if any(k in eid for k in ["oracle", "angel", "luz"]):
            return "angel"
        if any(k in eid for k in ["tribu", "apacheta", "ritual", "shaman"]):
            return "shaman"
        if any(k in eid for k in ["demon", "sangre", "abyss", "void"]):
            return "demon"
        return "arcane_hacker"

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            for i, ch in enumerate(self.event.get("choices", [])[:3]):
                if pygame.Rect(530, 720 + i * 92, 1260, 74).collidepoint(pos):
                    effects = ch.get("effects", [])
                    if str(self.event.get("id", "")) in {"chakana_crossroads", "condor_vision"}:
                        if self._resolved_guide_reward is None:
                            self._resolved_guide_reward = build_reward_guide(str(self.event.get("id", "guide")), self.app.rng, self.app.cards_data, self.app.run_state or {})
                        self.app.goto_reward(mode="guide_choice", guide_reward=self._resolved_guide_reward)
                        return
                    self.app.apply_event_effects(effects)
                    self.msg = self.app.loc.t(ch.get("text_key", "event_continue"))
                    self.app._complete_current_node()
                    self.app.goto_map()

    def update(self, dt):
        self.t += dt
        self.alpha = min(1.0, self.alpha + dt * 1.5)

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 2048, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        panel = pygame.Rect(80, 120, 1760, 850)
        pygame.draw.rect(s, (34, 24, 52), panel, border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=16)

        title = self.app.loc.t(self.event.get("title_key", "event_title"))
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (120, 148))

        avatar_frame = pygame.Rect(120, 230, 360, 420)
        pygame.draw.rect(s, (58, 40, 82), avatar_frame, border_radius=14)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_frame, 2, border_radius=14)
        av = self.app.assets.sprite("guides", self.guide_type, (320, 320), fallback=(34, 24, 52))
        s.blit(av, (140, 250))

        text_box = pygame.Rect(520, 230, 1280, 420)
        pygame.draw.rect(s, UI_THEME["panel_2"], text_box, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], text_box, 2, border_radius=12)
        guide_name = self.guide_names.get(self.guide_type, "Guia")
        s.blit(self.app.small_font.render(guide_name, True, UI_THEME["gold"]), (548, 246))
        s.blit(self.app.tiny_font.render("Lore breve", True, UI_THEME["muted"]), (548, 274))

        lines = self.writer.current.split("\n")
        y = 292
        for ln in lines[:6]:
            s.blit(self.app.font.render(ln, True, UI_THEME["text"]), (548, y))
            y += 38

        s.blit(self.app.small_font.render("Tres caminos", True, UI_THEME["gold"]), (548, 510))
        s.blit(self.app.font.render(self.moraleja, True, UI_THEME["muted"]), (690, 512))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, ch in enumerate(self.event.get("choices", [])[:3]):
            r = pygame.Rect(530, 720 + i * 92, 1260, 74)
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t(ch.get("text_key", "event_continue")), True, UI_THEME["text"]), (560, r.y + 22))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (540, 688))

        if self.alpha < 1.0:
            ov = pygame.Surface((1920, 1080), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(180 * (1.0 - self.alpha))))
            s.blit(ov, (0, 0))
