import pygame

from game.ui.theme import UI_THEME


class RewardScreen:
    def __init__(self, app, reward_cards, gold):
        self.app = app
        self.reward_cards = reward_cards
        self.gold = gold
        self.confetti = [{"x": 220 + i * 30, "y": 0, "v": 40 + i * 4} for i in range(30)]
        self.toast = ""
        self.toast_t = 0

    def on_enter(self):
        self.app.run_state["gold"] += self.gold
        self.app.gain_xp(8)

    def _recover_if_needed(self):
        if self.app.available_nodes_count() <= 0:
            self.app.recover_map_progression()
            self.toast = "La Trama se reordena..."
            self.toast_t = 2.5
            if self.app.available_nodes_count() <= 0 and self.app.debug_overlay:
                raise RuntimeError("map progression broken even after recovery")

    def take(self, idx):
        if idx is not None and 0 <= idx < len(self.reward_cards):
            self.app.run_state["sideboard"].append(self.reward_cards[idx].definition.id)
        if self.app.available_nodes_count() <= 0 and self.app.current_node_id:
            node = self.app.node_lookup.get(self.app.current_node_id)
            if node:
                self.app._fallback_unlock_next_column(node)
        self._recover_if_needed()
        self.app.goto_map()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            cols = [pygame.Rect(170 + i * 520, 220, 420, 360) for i in range(3)]
            for i, r in enumerate(cols):
                if i < len(self.reward_cards) and r.collidepoint(pos):
                    self.take(i)
                    return
            if pygame.Rect(860, 630, 220, 64).collidepoint(pos):
                self.take(None)

    def update(self, dt):
        for c in self.confetti:
            c["y"] += c["v"] * dt
            if c["y"] > 720:
                c["y"] = 0
        self.toast_t = max(0, self.toast_t - dt)

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t("reward_title"), True, UI_THEME["text"]), (500, 74))
        s.blit(self.app.font.render(f"+{self.gold} {self.app.loc.t('gold')}", True, UI_THEME["gold"]), (580, 120))
        s.blit(self.app.small_font.render("Elige cartas que combinen con tu Sendero", True, UI_THEME["muted"]), (420, 180))
        lvl = self.app.run_state["level"]
        need = lvl * 20
        ratio = self.app.run_state["xp"] / max(1, need)
        pygame.draw.rect(s, UI_THEME["panel"], (450, 154, 360, 16), border_radius=8)
        pygame.draw.rect(s, UI_THEME["good"], (450, 154, int(360 * ratio), 16), border_radius=8)
        for c in self.confetti:
            pygame.draw.rect(s, UI_THEME["card_selected"], (c["x"], int(c["y"]), 4, 4))
        cols = [pygame.Rect(170 + i * 520, 220, 420, 360) for i in range(3)]
        for i, r in enumerate(cols):
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            s.blit(self.app.small_font.render(f"Pack {i+1}", True, UI_THEME["gold"]), (r.x + 14, r.y + 12))
            if i < len(self.reward_cards):
                card = self.reward_cards[i]
                art = self.app.assets.sprite("cards", card.definition.id, (390, 210), fallback=(84, 66, 122))
                s.blit(art, (r.x + 15, r.y + 44))
                s.blit(self.app.font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 16, r.y + 264))
                lines = self.app.loc.t(card.definition.text_key)
                s.blit(self.app.small_font.render(lines, True, UI_THEME["muted"]), (r.x + 16, r.y + 306))
        pygame.draw.rect(s, UI_THEME["violet"], (860, 630, 220, 64), border_radius=10)
        s.blit(self.app.font.render(self.app.loc.t("reward_skip"), True, UI_THEME["text"]), (928, 650))
        if self.toast_t > 0:
            pygame.draw.rect(s, UI_THEME["panel_2"], (740, 660, 440, 52), border_radius=10)
            s.blit(self.app.small_font.render(self.toast, True, UI_THEME["gold"]), (772, 675))
