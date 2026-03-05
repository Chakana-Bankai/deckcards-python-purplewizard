import pygame

from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.theme import UI_THEME
from game.ui.components.pixel_icons import draw_icon_with_value


class RewardScreen:
    def __init__(self, app, reward_data, gold, xp_gained=0):
        self.app = app
        self.reward_data = reward_data if isinstance(reward_data, dict) else {"type": "choose1of3", "cards": list(reward_data or [])}
        self.mode = str(self.reward_data.get("type", "choose1of3"))
        self.cards = list(self.reward_data.get("cards", []))
        self.picks = self.cards
        self.relic = self.reward_data.get("relic")
        self.options = list(self.reward_data.get("options", []))
        self.gold = int(gold or 0)
        self.xp_gained = int(xp_gained or 0)
        self.msg = ""
        self.selected_idx = None
        self.hover_card = None
        self.preview = CardPreviewPanel(app=app)
        self.left_rect = pygame.Rect(52, 70, 1220, 920)
        self.right_rect = pygame.Rect(1290, 70, 578, 920)
        self.confirm_rect = pygame.Rect(780, 1004, 360, 56)
        self.back_rect = pygame.Rect(400, 1004, 320, 56)
        self.pulse = 0.0

    def on_enter(self):
        pass

    def claim(self, index: int) -> bool:
        if self.mode != "choose1of3":
            return False
        if not (0 <= index < len(self.cards)):
            return False
        self.selected_idx = index
        self.confirm()
        return True

    def _card_rects(self):
        if self.mode == "boss_pack":
            return [pygame.Rect(78 + i * 232, 240, 216, 330) for i in range(min(5, len(self.cards)))]
        return [pygame.Rect(78 + i * 380, 240, 350, 520) for i in range(min(3, len(self.cards)))]

    def _choice_rects(self):
        return [pygame.Rect(86, 300 + i * 188, 1160, 164) for i in range(min(3, len(self.options)))]

    def _wrap(self, font, text: str, width: int, max_lines: int = 3):
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

    def _confirm_enabled(self):
        if self.mode in {"choose1of3", "guide_choice"}:
            return self.selected_idx is not None
        if self.mode == "boss_pack":
            return True
        return False

    def _apply_guide_option(self, idx: int):
        option = self.options[idx]
        effects = list(option.get("effects", []))
        player = self.app.run_state.get("player", {})
        for effect in effects:
            typ = effect.get("type")
            if typ == "gain_harmony_perm":
                cur = int(player.get("harmony_max", 10))
                player["harmony_max"] = cur + int(effect.get("amount", 1))
            elif typ == "gain_cards":
                for cid in effect.get("cards", []):
                    self.app.run_state["sideboard"].append(cid)
            elif typ == "heal_percent":
                amount = float(effect.get("amount", 0.25))
                heal = int(player.get("max_hp", 60) * amount)
                player["hp"] = min(player.get("max_hp", 60), player.get("hp", 1) + max(1, heal))
            elif typ == "lose_random_deck_card":
                deck = self.app.run_state.get("deck", [])
                if deck:
                    deck.pop(self.app.rng.randint(0, len(deck) - 1))
        self.app.goto_map()

    def confirm(self):
        if not self._confirm_enabled():
            self.app.sfx.play("ui_click")
            return
        if self.mode == "choose1of3":
            card = self.cards[self.selected_idx]
            self.app.run_state["sideboard"].append(card.definition.id)
            self.app.run_state["gold"] += self.gold
            self.app.goto_map()
            return
        if self.mode == "boss_pack":
            for c in self.cards:
                self.app.run_state["sideboard"].append(c.definition.id)
            if isinstance(self.relic, dict) and self.relic.get("id"):
                self.app.run_state.setdefault("relics", []).append(self.relic["id"])
            self.app.run_state["gold"] += self.gold
            self.app.goto_map()
            return
        if self.mode == "guide_choice":
            self._apply_guide_option(self.selected_idx)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_map()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_rect.collidepoint(pos):
                self.app.goto_map(); return
            if self.confirm_rect.collidepoint(pos):
                self.confirm(); return

            if self.mode in {"choose1of3", "boss_pack"}:
                for i, r in enumerate(self._card_rects()):
                    if r.collidepoint(pos):
                        self.selected_idx = i
                        return
            elif self.mode == "guide_choice":
                for i, r in enumerate(self._choice_rects()):
                    if r.collidepoint(pos):
                        self.selected_idx = i
                        return

    def update(self, dt):
        self.pulse += dt * 5.0

    def _draw_header(self, s):
        pygame.draw.rect(s, (24, 18, 36), pygame.Rect(24, 24, 1872, 1032), border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], pygame.Rect(24, 24, 1872, 1032), 2, border_radius=16)
        title = {
            "choose1of3": "Elige 1 de 3 cartas",
            "boss_pack": "Victoria de Jefe: Botín Mayor",
            "guide_choice": "Elección del Guía",
        }.get(self.mode, "Recompensa")
        subtitle = {
            "choose1of3": "La Trama ofrece tres senderos.",
            "boss_pack": "Toma el pack completo y un relicario.",
            "guide_choice": "Sabiduría, Poder o Sacrificio: elige tu destino.",
        }.get(self.mode, "")
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (58, 42))
        s.blit(self.app.small_font.render(subtitle, True, UI_THEME["text"]), (60, 92))
        if self.mode != "guide_choice":
            s.blit(self.app.small_font.render(f"+{self.gold} oro • +{self.xp_gained} XP", True, UI_THEME["good"]), (60, 126))

    def _draw_cards_mode(self, s):
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, card in enumerate(self.cards):
            r = self._card_rects()[i]
            hover = r.collidepoint(mouse)
            if hover:
                self.hover_card = card
            sel = self.selected_idx == i
            pulse_add = int(2 * (1 + pygame.math.Vector2(1, 0).rotate(self.pulse * 60).x)) if sel else 0
            pygame.draw.rect(s, UI_THEME["panel_2"] if hover else UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if (hover or sel) else UI_THEME["accent_violet"], r, 2 + pulse_add, border_radius=12)
            art_h = 220 if self.mode == "boss_pack" else 300
            art = self.app.assets.sprite("cards", card.definition.id, (r.w - 20, art_h), fallback=(82, 52, 112))
            s.blit(art, (r.x + 10, r.y + 8))
            summary = summarize_card_effect(card.definition, card_instance=card, ctx=None)
            icon_data = self.preview._icon_row(summary)
            s.blit(self.app.tiny_font.render(self.app.loc.t(card.definition.name_key)[:24], True, UI_THEME["text"]), (r.x + 8, r.y + art_h + 22))
            s.blit(self.app.tiny_font.render(f"Coste {card.cost}", True, UI_THEME["energy"]), (r.x + 8, r.y + art_h + 44))
            x_icon = r.x + 88
            for icon_name, val in icon_data:
                x_icon = draw_icon_with_value(s, icon_name, val, UI_THEME["gold"], self.app.tiny_font, x_icon, r.y + art_h + 42, size=1)

        if self.mode == "boss_pack":
            relic_rect = pygame.Rect(86, 612, 1160, 130)
            pygame.draw.rect(s, UI_THEME["panel"], relic_rect, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"], relic_rect, 2, border_radius=12)
            rid = self.relic.get("id", "relic") if isinstance(self.relic, dict) else "relic"
            rname = self.app.loc.t(self.relic.get("name_key", rid)) if isinstance(self.relic, dict) else "Reliquia"
            rdesc = self.app.loc.t(self.relic.get("text_key", "")) if isinstance(self.relic, dict) else ""
            s.blit(self.app.small_font.render(f"Reliquia: {rname}", True, UI_THEME["gold"]), (relic_rect.x + 18, relic_rect.y + 18))
            for i, ln in enumerate(self._wrap(self.app.tiny_font, rdesc, relic_rect.w - 30, 2)):
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (relic_rect.x + 18, relic_rect.y + 56 + i * 18))

    def _draw_guide_mode(self, s):
        avatar_rect = pygame.Rect(80, 250, 360, 360)
        pygame.draw.rect(s, UI_THEME["panel"], avatar_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_rect, 2, border_radius=12)
        av = self.app.assets.sprite("guides", "angel", (320, 320), fallback=(40, 28, 62))
        s.blit(av, (avatar_rect.x + 20, avatar_rect.y + 20))

        lore_rect = pygame.Rect(456, 250, 790, 140)
        pygame.draw.rect(s, UI_THEME["panel_2"], lore_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], lore_rect, 2, border_radius=10)
        lore = "El guía susurra: cada senda moldea tu armonía y tu precio."
        for i, ln in enumerate(self._wrap(self.app.small_font, lore, lore_rect.w - 24, 3)):
            s.blit(self.app.small_font.render(ln, True, UI_THEME["text"]), (lore_rect.x + 12, lore_rect.y + 14 + i * 28))

        for i, opt in enumerate(self.options[:3]):
            r = self._choice_rects()[i]
            sel = self.selected_idx == i
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if sel else UI_THEME["accent_violet"], r, 3 if sel else 2, border_radius=12)
            s.blit(self.app.small_font.render(opt.get("title", f"Opción {i+1}"), True, UI_THEME["gold"]), (r.x + 14, r.y + 14))
            s.blit(self.app.tiny_font.render(opt.get("effect_label", ""), True, UI_THEME["good"]), (r.x + 16, r.y + 48))
            for j, ln in enumerate(self._wrap(self.app.tiny_font, opt.get("lore", ""), r.w - 28, 2)):
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (r.x + 16, r.y + 76 + j * 18))

    def render(self, s):
        self._draw_header(s)
        if self.mode in {"choose1of3", "boss_pack"}:
            self._draw_cards_mode(s)
        elif self.mode == "guide_choice":
            self._draw_guide_mode(s)

        preview_card = self.hover_card
        if self.selected_idx is not None and self.mode in {"choose1of3", "boss_pack"} and self.selected_idx < len(self.cards):
            preview_card = self.cards[self.selected_idx]
        self.preview.render(s, self.right_rect, preview_card, app=self.app)

        confirm_enabled = self._confirm_enabled()
        pygame.draw.rect(s, UI_THEME["violet"] if confirm_enabled else (84, 76, 106), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        label = "Confirmar" if self.mode != "boss_pack" else "Tomar recompensas"
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.confirm_rect.x + 108, self.confirm_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.back_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.back_rect, 2, border_radius=10)
        s.blit(self.app.font.render("Volver", True, UI_THEME["text"]), (self.back_rect.x + 126, self.back_rect.y + 16))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (70, 1002))
