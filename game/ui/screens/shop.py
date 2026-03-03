import pygame

from game.settings import COLORS


class ShopScreen:
    def __init__(self, app, offer_card):
        self.app = app
        self.offer_card = offer_card

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.app.toggle_language()
            if event.key == pygame.K_ESCAPE:
                self.app._complete_current_node()
                self.app.goto_map()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            if pygame.Rect(160, 220, 330, 240).collidepoint(pos) and self.app.run_state["gold"] >= 40:
                self.app.run_state["gold"] -= 40
                self.app.run_state["deck"].append(self.offer_card["id"])
            if pygame.Rect(560, 220, 330, 240).collidepoint(pos) and self.app.run_state["gold"] >= 30 and self.app.run_state["deck"]:
                self.app.run_state["gold"] -= 30
                self.app.run_state["deck"].pop(0)
            if pygame.Rect(980, 220, 220, 70).collidepoint(pos):
                self.app._complete_current_node()
                self.app.goto_map()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(COLORS["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t("shop_title"), True, COLORS["text"]), (560, 60))
        s.blit(self.app.font.render(f"{self.app.loc.t('gold')}: {self.app.run_state['gold']}", True, COLORS["gold"]), (1020, 60))
        pygame.draw.rect(s, COLORS["panel"], (160, 220, 330, 240), border_radius=8)
        s.blit(self.app.font.render(f"{self.app.loc.t('shop_buy')} (40)", True, COLORS["text"]), (180, 240))
        s.blit(self.app.small_font.render(self.app.loc.t(self.offer_card["name_key"]), True, COLORS["muted"]), (180, 280))
        pygame.draw.rect(s, COLORS["panel"], (560, 220, 330, 240), border_radius=8)
        s.blit(self.app.font.render(f"{self.app.loc.t('shop_remove')} (30)", True, COLORS["text"]), (580, 240))
        pygame.draw.rect(s, COLORS["violet_dark"], (980, 220, 220, 70), border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("shop_leave"), True, COLORS["text"]), (1040, 245))
