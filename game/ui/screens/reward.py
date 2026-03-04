import pygame

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.ui.theme import UI_THEME


class RewardScreen:
    def __init__(self, app, picks, gold, xp_gained=0):
        self.app = app
        self.picks = picks
        self.gold = gold
        self.xp_gained = xp_gained
        self.msg = ""
        self.hints = load_json(data_dir() / "hints_es.json", default=[])
        if not isinstance(self.hints, list):
            self.hints = []
        self.hint = self._pick_hint()

    def _pick_hint(self):
        if not self.hints:
            return {"id": "fallback", "text": "Observa energía, intención enemiga y armonía antes de ejecutar."}
        last = str((self.app.run_state or {}).get("last_hint_id", ""))
        pool = [h for h in self.hints if isinstance(h, dict) and str(h.get("id", "")) != last]
        if not pool:
            pool = [h for h in self.hints if isinstance(h, dict)]
        picked = self.app.rng.choice(pool) if pool else {"id": "fallback", "text": "Escucha la Trama antes de decidir."}
        if self.app.run_state is not None and isinstance(picked, dict):
            self.app.run_state["last_hint_id"] = picked.get("id", "fallback")
        return picked

    def on_enter(self):
        pass

    def _metaforma(self, s, rect):
        pygame.draw.rect(s, (66, 48, 88), rect, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], rect, 2, border_radius=18)
        inner = rect.inflate(-20, -20)
        pygame.draw.rect(s, (24, 18, 36), inner, border_radius=14)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, card in enumerate(self.picks):
                r = pygame.Rect(430 + i * 350, 370, 300, 420)
                if r.collidepoint(pos):
                    self.app.run_state["sideboard"].append(card.definition.id)
                    self.app.run_state["gold"] += self.gold
                    self.msg = self.app.loc.t("reward_claimed", gold=self.gold)
                    self.app.goto_map()
                    return

    def update(self, dt):
        pass

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 1111, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        panel = pygame.Rect(120, 120, 1680, 840)
        self._metaforma(s, panel)
        header = pygame.Rect(140, 140, 1640, 120)
        pygame.draw.rect(s, UI_THEME["deep_purple"], header, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], header, 2, border_radius=12)
        s.blit(self.app.big_font.render("Recompensa", True, UI_THEME["gold"]), (160, 164))
        s.blit(self.app.small_font.render(f"Oro +{self.gold}   XP +{self.xp_gained}", True, UI_THEME["good"]), (162, 206))

        teach = pygame.Rect(140, 804, 1640, 126)
        pygame.draw.rect(s, UI_THEME["panel"], teach, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], teach, 2, border_radius=12)
        s.blit(self.app.small_font.render("Enseñanza", True, UI_THEME["gold"]), (160, 820))
        hint = str((self.hint or {}).get("text", "Escucha la Trama."))
        s.blit(self.app.small_font.render(hint[:128], True, UI_THEME["text"]), (160, 856))
        print(f"[ui] reward_hint={hint}")

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, card in enumerate(self.picks):
            r = pygame.Rect(430 + i * 350, 370, 300, 420)
            hover = r.collidepoint(mouse)
            rr = r.inflate(12, 12) if hover else r
            pygame.draw.rect(s, UI_THEME["card_bg"], rr, border_radius=14)
            pygame.draw.rect(s, UI_THEME["gold"], rr, 2, border_radius=14)
            art = self.app.assets.sprite("cards", card.definition.id, (rr.w - 20, 220), fallback=(82, 52, 112))
            s.blit(art, (rr.x + 10, rr.y + 50))
            s.blit(self.app.small_font.render(self.app.loc.t(str(card.definition.name_key)), True, UI_THEME["text"]), (rr.x + 14, rr.y + 16))
            s.blit(self.app.tiny_font.render(self.app.loc.t(str(card.definition.text_key))[:44], True, UI_THEME["muted"]), (rr.x + 14, rr.y + 292))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (140, 920))
