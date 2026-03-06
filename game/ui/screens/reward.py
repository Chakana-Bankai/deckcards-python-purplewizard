import pygame

from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.theme import UI_THEME, UI_SAFE_BOTTOM, UI_SAFE_SIDE
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
        self.confirm_rect = pygame.Rect(0, 0, 360, 56)
        self.back_rect = pygame.Rect(0, 0, 320, 56)
        self.content_rect = pygame.Rect(52, 170, 1220, 770)
        self.pulse = 0.0
        self.reveal_t = 0.0

    def _layout(self, surface: pygame.Surface):
        w, h = surface.get_size()
        frame = pygame.Rect(UI_SAFE_SIDE, UI_SAFE_SIDE, w - UI_SAFE_SIDE * 2, h - UI_SAFE_SIDE * 2)
        buttons_y = h - UI_SAFE_BOTTOM
        self.back_rect.size = (280, 56)
        self.confirm_rect.size = (320, 56)
        gap = 24
        group_w = self.back_rect.w + self.confirm_rect.w + gap
        start_x = w // 2 - group_w // 2
        self.back_rect.topleft = (start_x, buttons_y - self.back_rect.h // 2)
        self.confirm_rect.topleft = (self.back_rect.right + gap, buttons_y - self.confirm_rect.h // 2)

        header_h = 132
        content_top = frame.y + header_h
        content_bottom = buttons_y - 18
        content_h = max(240, content_bottom - content_top)

        if self.mode == "guide_choice":
            self.left_rect = pygame.Rect(frame.x + 28, content_top, int(frame.w * 0.68), content_h)
            self.right_rect = pygame.Rect(self.left_rect.right + 16, content_top, frame.right - self.left_rect.right - 44, content_h)
        else:
            self.left_rect = pygame.Rect(frame.x + 28, content_top, int(frame.w * 0.66), content_h)
            self.right_rect = pygame.Rect(self.left_rect.right + 16, content_top, frame.right - self.left_rect.right - 44, content_h)
        self.content_rect = self.left_rect.copy()
        return frame

    def on_enter(self):
        self.reveal_t = 0.0

    def claim(self, index: int) -> bool:
        if self.mode != "choose1of3":
            return False
        if not (0 <= index < len(self.cards)):
            return False
        self.selected_idx = index
        self.confirm()
        return True

    def _card_rects(self):
        top = self.content_rect.y + 14
        if self.mode == "boss_pack":
            count = min(5, len(self.cards))
            gap = 14
            card_w = max(180, min(220, (self.content_rect.w - 12 - (count - 1) * gap) // max(1, count)))
            h = min(330, self.content_rect.h - 190)
            return [pygame.Rect(self.content_rect.x + 6 + i * (card_w + gap), top, card_w, h) for i in range(count)]
        count = min(3, len(self.cards))
        gap = 18
        card_w = max(280, min(350, (self.content_rect.w - 12 - (count - 1) * gap) // max(1, count)))
        h = min(520, self.content_rect.h - 20)
        return [pygame.Rect(self.content_rect.x + 6 + i * (card_w + gap), top, card_w, h) for i in range(count)]

    def _choice_rects(self):
        count = min(3, len(self.options))
        gap = 14
        usable_h = self.content_rect.h - 190
        row_h = max(122, min(164, (usable_h - (count - 1) * gap) // max(1, count)))
        top = self.content_rect.y + 176
        return [pygame.Rect(self.content_rect.x + self.content_rect.w // 2, top + i * (row_h + gap), self.content_rect.w // 2 - 10, row_h) for i in range(count)]

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
            self.app.goto_end(victory=True)
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
        self.reveal_t = min(1.0, self.reveal_t + dt * 2.2)

    def _draw_header(self, s, frame):
        pygame.draw.rect(s, (24, 18, 36), frame, border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], frame, 2, border_radius=16)
        title = {
            "choose1of3": "Recompensa",
            "boss_pack": "Botín del Jefe",
            "guide_choice": "Elección del Guía",
        }.get(self.mode, "Recompensa")
        subtitle = {
            "choose1of3": "Selecciona 1 carta para añadirla a tu sideboard.",
            "boss_pack": "Has vencido al jefe. Recibirás todo el lote.",
            "guide_choice": "Sabiduría, Poder o Sacrificio: elige tu destino.",
        }.get(self.mode, "")
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (frame.x + 34, frame.y + 18))
        s.blit(self.app.small_font.render(subtitle, True, UI_THEME["text"]), (frame.x + 36, frame.y + 68))
        if self.mode != "guide_choice":
            s.blit(self.app.small_font.render(f"+{self.gold} oro • +{self.xp_gained} XP", True, UI_THEME["good"]), (frame.x + 36, frame.y + 102))

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
            art_h = min(300 if self.mode != "boss_pack" else 220, r.h - 88)
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
            relic_top = min(self.content_rect.bottom - 136, max((rr.bottom for rr in self._card_rects()), default=self.content_rect.y) + 14)
            relic_rect = pygame.Rect(self.content_rect.x + 10, relic_top, self.content_rect.w - 20, 126)
            pygame.draw.rect(s, UI_THEME["panel"], relic_rect, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"], relic_rect, 2, border_radius=12)
            rid = self.relic.get("id", "relic") if isinstance(self.relic, dict) else "relic"
            rname = self.app.loc.t(self.relic.get("name_key", rid)) if isinstance(self.relic, dict) else "Reliquia"
            rdesc = self.app.loc.t(self.relic.get("text_key", "")) if isinstance(self.relic, dict) else ""
            s.blit(self.app.small_font.render(f"Reliquia: {rname}", True, UI_THEME["gold"]), (relic_rect.x + 18, relic_rect.y + 16))
            for i, ln in enumerate(self._wrap(self.app.tiny_font, rdesc, relic_rect.w - 30, 2)):
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (relic_rect.x + 18, relic_rect.y + 52 + i * 18))

    def _draw_guide_mode(self, s):
        left_col = pygame.Rect(self.content_rect.x + 8, self.content_rect.y + 12, self.content_rect.w // 2 - 16, self.content_rect.h - 24)
        right_col = pygame.Rect(self.content_rect.x + self.content_rect.w // 2 + 8, self.content_rect.y + 12, self.content_rect.w // 2 - 16, self.content_rect.h - 24)

        avatar_rect = pygame.Rect(left_col.x + 10, left_col.y + 18, left_col.w - 20, min(320, left_col.h - 180))
        pygame.draw.rect(s, UI_THEME["panel"], avatar_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_rect, 2, border_radius=12)
        pulse = 70 + int(46 * (0.5 + 0.5 * pygame.math.Vector2(1, 0).rotate(self.pulse * 58).x))
        glow = pygame.Surface((avatar_rect.w + 24, avatar_rect.h + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (188, 154, 255, pulse), glow.get_rect(), border_radius=18)
        s.blit(glow, (avatar_rect.x - 12, avatar_rect.y - 12))
        av = self.app.assets.sprite("guides", "angel", (avatar_rect.w - 32, avatar_rect.h - 32), fallback=(40, 28, 62))
        s.blit(av, (avatar_rect.x + 16, avatar_rect.y + 16))

        lore_rect = pygame.Rect(left_col.x + 10, avatar_rect.bottom + 12, left_col.w - 20, max(120, left_col.bottom - avatar_rect.bottom - 24))
        pygame.draw.rect(s, UI_THEME["panel_2"], lore_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], lore_rect, 2, border_radius=10)
        lore = "El guía susurra: cada senda moldea tu armonía y tu precio."
        for i, ln in enumerate(self._wrap(self.app.small_font, lore, lore_rect.w - 24, 4)):
            s.blit(self.app.small_font.render(ln, True, UI_THEME["text"]), (lore_rect.x + 12, lore_rect.y + 14 + i * 28))

        pygame.draw.rect(s, UI_THEME["panel_2"], right_col, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], right_col, 2, border_radius=10)
        for i, opt in enumerate(self.options[:3]):
            r = self._choice_rects()[i]
            sel = self.selected_idx == i
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["gold"] if sel else UI_THEME["accent_violet"], r, 3 if sel else 2, border_radius=12)
            s.blit(self.app.small_font.render(opt.get("title", f"Opción {i+1}"), True, UI_THEME["gold"]), (r.x + 14, r.y + 12))
            s.blit(self.app.tiny_font.render(opt.get("effect_label", ""), True, UI_THEME["good"]), (r.x + 16, r.y + 44))
            for j, ln in enumerate(self._wrap(self.app.tiny_font, opt.get("lore", ""), r.w - 28, 2)):
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (r.x + 16, r.y + 72 + j * 18))

    def render(self, s):
        frame = self._layout(s)
        self._draw_header(s, frame)
        if self.mode in {"choose1of3", "boss_pack"}:
            self._draw_cards_mode(s)
        elif self.mode == "guide_choice":
            self._draw_guide_mode(s)

        if self.mode in {"choose1of3", "boss_pack"}:
            preview_card = self.hover_card
            if self.selected_idx is not None and self.selected_idx < len(self.cards):
                preview_card = self.cards[self.selected_idx]
            self.preview.render(s, self.right_rect, preview_card, app=self.app)

        confirm_enabled = self._confirm_enabled()
        pygame.draw.rect(s, UI_THEME["violet"] if confirm_enabled else (84, 76, 106), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        label = "Continuar" if self.mode == "guide_choice" else ("Confirmar" if self.mode != "boss_pack" else "Tomar recompensas")
        lbl = self.app.font.render(label, True, UI_THEME["text"])
        s.blit(lbl, (self.confirm_rect.centerx - lbl.get_width() // 2, self.confirm_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.back_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.back_rect, 2, border_radius=10)
        back_lbl = self.app.font.render("Volver", True, UI_THEME["text"])
        s.blit(back_lbl, (self.back_rect.centerx - back_lbl.get_width() // 2, self.back_rect.y + 16))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (self.left_rect.x, self.confirm_rect.y - 30))

        if self.reveal_t < 1.0:
            ov = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(180 * (1.0 - self.reveal_t))))
            s.blit(ov, (0, 0))
