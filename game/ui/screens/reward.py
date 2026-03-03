import pygame

from game.ui.theme import UI_THEME


class RewardScreen:
    def __init__(self, app, reward_cards, gold, xp_gained=0):
        self.app = app
        self.reward_cards = reward_cards
        self.gold = gold
        self.xp_gained = xp_gained
        self.confetti = [{"x": 220 + i * 30, "y": 0, "v": 40 + i * 4} for i in range(30)]
        self.toast = ""
        self.toast_t = 0
        self.selected_idx = None
        self.confirm_rect = pygame.Rect(830, 900, 260, 64)
        self.skip_rect = pygame.Rect(1110, 900, 220, 64)
        self.lessons = {"miedo":"El miedo se disuelve cuando respiras y observas.","arrogancia":"La arrogancia cae ante la escucha humilde.","apego":"Soltar también protege el corazón.","prisa":"La prisa rompe la forma de la Trama.","confusión":"La claridad nace al pausar.","soberbia":"Sin Ayni no hay victoria duradera.","desesperación":"Incluso en sombra, Pacha ofrece salida.","rigidez":"La flexibilidad sostiene la vida.","duda":"La duda se ordena con práctica."}

    def on_enter(self):
        self.app.run_state["gold"] += self.gold

    def _recover_if_needed(self):
        if self.app.available_nodes_count() <= 0:
            self.app.recover_map_progression()
            self.toast = "La Trama se reordena..."
            self.toast_t = 2.5

    def take(self, idx):
        if idx is not None and 0 <= idx < len(self.reward_cards):
            cid = self.reward_cards[idx].definition.id
            self.app.run_state["sideboard"].append(cid)
            self.app.sfx.play("card_pick")
            self.toast = f"Elegiste {cid}"
            self.toast_t = 1.8
        if self.app.available_nodes_count() <= 0 and self.app.current_node_id:
            node = self.app.node_lookup.get(self.app.current_node_id)
            if node:
                self.app._fallback_unlock_next_column(node)
        self._recover_if_needed()
        self.app.goto_map()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            cols = [pygame.Rect(120 + i * 560, 230, 520, 620) for i in range(3)]
            for i, r in enumerate(cols):
                if i < len(self.reward_cards) and r.collidepoint(pos):
                    self.selected_idx = i
                    self.app.sfx.play("ui_click")
                    return
            if self.confirm_rect.collidepoint(pos) and self.selected_idx is not None:
                self.take(self.selected_idx)
            if self.skip_rect.collidepoint(pos):
                self.take(None)

    def update(self, dt):
        for c in self.confetti:
            c["y"] += c["v"] * dt
            if c["y"] > 720:
                c["y"] = 0
        self.toast_t = max(0, self.toast_t - dt)

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t("reward_title"), True, UI_THEME["text"]), (760, 54))
        s.blit(self.app.font.render(f"+{self.gold} {self.app.loc.t('gold')}  +{self.xp_gained} XP", True, UI_THEME["gold"]), (700, 104))
        lk = self.app.debug.get("last_lesson_key", "duda")
        lesson = self.lessons.get(lk, self.lessons["duda"])
        s.blit(self.app.small_font.render(f"Lección: {lesson}", True, UI_THEME["muted"]), (620, 176))
        lvl = self.app.run_state["level"]
        need = lvl * 20
        ratio = self.app.run_state["xp"] / max(1, need)
        pygame.draw.rect(s, UI_THEME["panel"], (620, 146, 680, 18), border_radius=8)
        pygame.draw.rect(s, UI_THEME["good"], (620, 146, int(680 * ratio), 18), border_radius=8)
        for c in self.confetti:
            pygame.draw.rect(s, UI_THEME["card_selected"], (c["x"], int(c["y"]), 4, 4))

        cols = [pygame.Rect(120 + i * 560, 230, 520, 620) for i in range(3)]
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, r in enumerate(cols):
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            if r.collidepoint(mouse):
                pygame.draw.rect(s, (186, 158, 255), r.inflate(8, 8), 2, border_radius=14)
            s.blit(self.app.small_font.render(f"Pack {i+1}", True, UI_THEME["gold"]), (r.x + 16, r.y + 12))
            if i < len(self.reward_cards):
                card = self.reward_cards[i]
                art = self.app.assets.sprite("cards", card.definition.id, (488, 340), fallback=(84, 66, 122))
                s.blit(art, (r.x + 16, r.y + 50))
                s.blit(self.app.font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 16, r.y + 410))
                s.blit(self.app.small_font.render(self.app.loc.t(card.definition.text_key), True, UI_THEME["muted"]), (r.x + 16, r.y + 458))
            if i == self.selected_idx:
                pygame.draw.rect(s, UI_THEME["gold"], r.inflate(12, 12), 4, border_radius=14)
                s.blit(self.app.small_font.render("SELECCIONADA", True, UI_THEME["gold"]), (r.x + 170, r.y - 28))

        pygame.draw.rect(s, UI_THEME["violet"] if self.selected_idx is not None else (82, 78, 104), self.confirm_rect, border_radius=10)
        s.blit(self.app.font.render("Confirmar", True, UI_THEME["text"]), (self.confirm_rect.x + 70, self.confirm_rect.y + 18))
        pygame.draw.rect(s, UI_THEME["panel_2"], self.skip_rect, border_radius=10)
        s.blit(self.app.font.render(self.app.loc.t("reward_skip"), True, UI_THEME["text"]), (self.skip_rect.x + 40, self.skip_rect.y + 18))

        if self.toast_t > 0:
            pygame.draw.rect(s, UI_THEME["panel_2"], (700, 980, 520, 52), border_radius=10)
            s.blit(self.app.small_font.render(self.toast, True, UI_THEME["gold"]), (736, 994))
