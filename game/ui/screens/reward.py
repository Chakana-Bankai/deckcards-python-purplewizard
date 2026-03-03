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
            for i, card in enumerate(self.reward_cards):
                r = pygame.Rect(180 + i * 300, 220, 260, 320)
                if r.collidepoint(pos):
                    self.take(i)
                    return
            if pygame.Rect(560, 580, 180, 56).collidepoint(pos):
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
        for i, card in enumerate(self.reward_cards):
            r = pygame.Rect(180 + i * 300, 220, 260, 320)
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=10)
            art = self.app.assets.sprite("cards", card.definition.id, (240, 170), fallback=(84, 66, 122))
            s.blit(art, (r.x + 10, r.y + 10))
            s.blit(self.app.font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 10, r.y + 190))
            s.blit(self.app.small_font.render(self.app.loc.t(card.definition.text_key), True, UI_THEME["muted"]), (r.x + 10, r.y + 230))
        pygame.draw.rect(s, UI_THEME["violet"], (560, 580, 180, 56), border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("reward_skip"), True, UI_THEME["text"]), (608, 595))
        if self.toast_t > 0:
            pygame.draw.rect(s, UI_THEME["panel_2"], (740, 660, 440, 52), border_radius=10)
            s.blit(self.app.small_font.render(self.toast, True, UI_THEME["gold"]), (772, 675))
