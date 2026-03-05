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

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
    def claim(self, index: int) -> bool:
        if not (0 <= index < len(self.picks)):
            return False
        card = self.picks[index]
        self.app.run_state["sideboard"].append(card.definition.id)
        self.app.run_state["gold"] += self.gold
        self.msg = self.app.loc.t("reward_claimed", gold=self.gold)
        self.app.goto_map()
        return True

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
    def _clamp_text(self, font, text: str, max_px: int) -> str:
        out = str(text or "")
        while font.size(out)[0] > max_px and len(out) > 3:
            out = out[:-2]
        if out != text:
            out = out.rstrip() + "…"
        return out

    def _metaforma(self, s, rect):
        pygame.draw.rect(s, (66, 48, 88), rect, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], rect, 2, border_radius=18)
        inner = rect.inflate(-20, -20)
        pygame.draw.rect(s, (24, 18, 36), inner, border_radius=14)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            for i, card in enumerate(self.picks):
                r = pygame.Rect(300 + i * 440, 314, 400, 448)
                if r.collidepoint(pos):
                    self.app.run_state["sideboard"].append(card.definition.id)
                    self.app.run_state["gold"] += self.gold
                    self.msg = self.app.loc.t("reward_claimed", gold=self.gold)
                    self.app.goto_map()
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
            for i, _card in enumerate(self.picks):
                r = pygame.Rect(300 + i * 440, 314, 400, 448)
                if r.collidepoint(pos):
                    self.claim(i)
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
                    return

    def update(self, dt):
        pass

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 1111, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        panel = pygame.Rect(84, 84, 1752, 912)
        self._metaforma(s, panel)
        header = pygame.Rect(110, 110, 1700, 118)
        pygame.draw.rect(s, UI_THEME["deep_purple"], header, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], header, 2, border_radius=12)
        s.blit(self.app.big_font.render("Elige tu Recompensa", True, UI_THEME["gold"]), (132, 136))
        s.blit(self.app.small_font.render(f"+{self.gold} oro  •  +{self.xp_gained} XP", True, UI_THEME["good"]), (134, 180))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, card in enumerate(self.picks):
            r = pygame.Rect(300 + i * 440, 314, 400, 448)
            hover = r.collidepoint(mouse)
            rr = r.inflate(14, 14) if hover else r
            pygame.draw.rect(s, UI_THEME["card_bg"], rr, border_radius=14)
            pygame.draw.rect(s, UI_THEME["gold" if hover else "accent_violet"], rr, 3 if hover else 2, border_radius=14)

            name = self.app.loc.t(str(card.definition.name_key))
            desc = self.app.loc.t(str(card.definition.text_key))
            art = self.app.assets.sprite("cards", card.definition.id, (rr.w - 24, 262), fallback=(82, 52, 112))
            s.blit(art, (rr.x + 12, rr.y + 52))

            name_line = self._clamp_text(self.app.small_font, name, rr.w - 64)
            s.blit(self.app.small_font.render(name_line, True, UI_THEME["text"]), (rr.x + 14, rr.y + 14))
            pygame.draw.circle(s, UI_THEME["energy"], (rr.right - 22, rr.y + 24), 13)
            s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rr.right - 26, rr.y + 17))
            desc_line = self._clamp_text(self.app.tiny_font, desc, rr.w - 28)
            s.blit(self.app.tiny_font.render(desc_line, True, UI_THEME["muted"]), (rr.x + 14, rr.y + 328))
            s.blit(self.app.tiny_font.render("Click para reclamar", True, UI_THEME["good"] if hover else UI_THEME["muted"]), (rr.x + 14, rr.bottom - 26))

        teach = pygame.Rect(110, 804, 1700, 152)
        pygame.draw.rect(s, UI_THEME["panel"], teach, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], teach, 2, border_radius=12)
        hint = str((self.hint or {}).get("text", "")).strip()
        if hint:
            s.blit(self.app.small_font.render("Enseñanza de la Trama", True, UI_THEME["gold"]), (130, 822))
            hline = self._clamp_text(self.app.small_font, hint, teach.w - 40)
            s.blit(self.app.small_font.render(hline, True, UI_THEME["text"]), (130, 862))
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        print(f"[ui] reward_hint={hint}")
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (124, 964))
