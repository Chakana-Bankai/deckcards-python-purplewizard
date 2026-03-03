import pygame

from game.combat.card import CardInstance
from game.settings import COLORS


class RewardScreen:
    def __init__(self, app, reward_cards, gold):
        self.app = app
        self.reward_cards = reward_cards
        self.gold = gold

    def on_enter(self):
        self.app.run_state["gold"] += self.gold

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, card in enumerate(self.reward_cards):
                r = pygame.Rect(220 + i * 290, 240, 240, 300)
                if r.collidepoint(pos):
                    self.app.run_state["deck"].append(card.definition.id)
                    self.app.goto_map()
                    return
            if pygame.Rect(560, 580, 160, 50).collidepoint(pos):
                self.app.goto_map()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(COLORS["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t("reward_title"), True, COLORS["text"]), (500, 80))
        s.blit(self.app.font.render(f"+{self.gold} {self.app.loc.t('gold')}", True, COLORS["gold"]), (580, 130))
        for i, card in enumerate(self.reward_cards):
            r = pygame.Rect(220 + i * 290, 240, 240, 300)
            pygame.draw.rect(s, COLORS["panel"], r, border_radius=8)
            s.blit(self.app.font.render(self.app.loc.t(card.definition.name_key), True, COLORS["text"]), (r.x + 10, r.y + 10))
            s.blit(self.app.small_font.render(self.app.loc.t(card.definition.text_key), True, COLORS["muted"]), (r.x + 10, r.y + 50))
        pygame.draw.rect(s, COLORS["violet_dark"], (560, 580, 160, 50), border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("reward_skip"), True, COLORS["text"]), (600, 592))
