import pygame

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.theme import UI_THEME


class RewardScreen:
    def __init__(self, app, picks, gold, xp_gained=0):
        self.app = app
        self.picks = picks
        self.gold = gold
        self.xp_gained = xp_gained
        self.msg = ""
        self.selected_index = None
        self.confirm_rect = pygame.Rect(760, 904, 380, 60)
        self.option_rects = [pygame.Rect(84 + i * 420, 250, 390, 470) for i in range(3)]
        self.preview = CardPreviewPanel(app)
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

    def claim(self, index: int) -> bool:
        if not (0 <= index < len(self.picks)):
            return False
        card = self.picks[index]
        self.app.run_state["sideboard"].append(card.definition.id)
        self.app.run_state["gold"] += self.gold
        self.msg = self.app.loc.t("reward_claimed", gold=self.gold)
        self.app.goto_map()
        return True

    def _wrap(self, font, text: str, width: int, max_lines: int = 2):
        words = str(text or "").split()
        out = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if font.size(cand)[0] <= width:
                cur = cand
            else:
                if cur:
                    out.append(cur)
                cur = w
                if len(out) >= max_lines:
                    break
        if cur and len(out) < max_lines:
            out.append(cur)
        return out

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(self.option_rects[: len(self.picks)]):
                if r.collidepoint(pos):
                    self.selected_index = i
                    return
            if self.confirm_rect.collidepoint(pos) and self.selected_index is not None:
                self.claim(self.selected_index)

    def update(self, dt):
        _ = dt

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 1111, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))

        panel = pygame.Rect(42, 42, 1836, 996)
        pygame.draw.rect(s, (24, 18, 36), panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=18)

        s.blit(self.app.big_font.render("Recompensa de Combate", True, UI_THEME["gold"]), (72, 68))
        hint_txt = str((self.hint or {}).get("text", "")).strip()
        if hint_txt:
            for i, ln in enumerate(self._wrap(self.app.small_font, hint_txt, 850, 2)):
                s.blit(self.app.small_font.render(ln, True, UI_THEME["text"]), (74, 118 + i * 24))
        s.blit(self.app.small_font.render(f"+{self.gold} oro • +{self.xp_gained} XP", True, UI_THEME["good"]), (74, 174))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        hovered = None
        for i, card in enumerate(self.picks):
            r = self.option_rects[i]
            is_hover = r.collidepoint(mouse)
            is_sel = self.selected_index == i
            if is_hover:
                hovered = card
            pygame.draw.rect(s, UI_THEME["panel_2"] if is_hover else UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if (is_hover or is_sel) else UI_THEME["accent_violet"], r, 3 if (is_hover or is_sel) else 2, border_radius=12)

            art = self.app.assets.sprite("cards", card.definition.id, (r.w - 24, 260), fallback=(82, 52, 112))
            s.blit(art, (r.x + 12, r.y + 54))
            name = self.app.loc.t(str(card.definition.name_key))
            s.blit(self.app.small_font.render(name[:28], True, UI_THEME["text"]), (r.x + 12, r.y + 14))
            s.blit(self.app.tiny_font.render(f"Coste {card.cost}", True, UI_THEME["energy"]), (r.right - 90, r.y + 18))
            s.blit(self.app.tiny_font.render("Click para seleccionar", True, UI_THEME["muted"]), (r.x + 12, r.bottom - 56))
            s.blit(self.app.tiny_font.render("Recompensa: carta + oro", True, UI_THEME["good"]), (r.x + 12, r.bottom - 32))

        preview_rect = pygame.Rect(1320, 250, 530, 640)
        selected_card = self.picks[self.selected_index] if self.selected_index is not None and self.selected_index < len(self.picks) else hovered
        self.preview.render(s, preview_rect, selected_card)

        confirm_enabled = self.selected_index is not None
        pygame.draw.rect(s, UI_THEME["violet"] if confirm_enabled else (84, 76, 106), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        s.blit(self.app.font.render("Confirmar recompensa", True, UI_THEME["text"]), (self.confirm_rect.x + 56, self.confirm_rect.y + 18))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (74, 980))
