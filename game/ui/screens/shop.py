import pygame

from game.ui.theme import UI_THEME


class ShopScreen:
    def __init__(self, app, offer_card):
        self.app = app
        self.offer_card = offer_card
        premium_pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary"}]
        self.premium_card = self.app.rng.choice(premium_pool) if premium_pool else offer_card
        self.msg = ""
        self.buy_price = 45
        self.premium_price = 90
        self.remove_price = 70

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
            if pygame.Rect(120, 200, 360, 320).collidepoint(pos):
                if self.app.run_state["gold"] >= self.buy_price:
                    self.app.run_state["gold"] -= self.buy_price
                    self.app.run_state["sideboard"].append(self.offer_card["id"])
                    self.msg = "+1 carta al pool"
                else:
                    self.msg = "No alcanza oro"
            if pygame.Rect(500, 200, 360, 320).collidepoint(pos):
                if self.app.run_state["gold"] >= self.premium_price:
                    self.app.run_state["gold"] -= self.premium_price
                    self.app.run_state["sideboard"].append(self.premium_card["id"])
                    self.msg = "+1 carta premium"
                else:
                    self.msg = "No alcanza oro"
            if pygame.Rect(880, 200, 280, 140).collidepoint(pos):
                if self.app.run_state["gold"] >= self.remove_price and self.app.run_state["deck"]:
                    self.app.run_state["gold"] -= self.remove_price
                    self.app.run_state["deck"].pop(0)
                    self.msg = "Carta removida"
                else:
                    self.msg = "No alcanza oro"
            if pygame.Rect(900, 380, 240, 72).collidepoint(pos):
                self.app._complete_current_node()
                self.app.goto_map()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t("shop_title"), True, UI_THEME["text"]), (540, 54))
        s.blit(self.app.font.render(f"{self.app.loc.t('gold')}: {self.app.run_state['gold']}", True, UI_THEME["gold"]), (990, 56))
        pygame.draw.rect(s, UI_THEME["panel"], (120, 200, 360, 320), border_radius=10)
        s.blit(self.app.font.render(f"{self.app.loc.t('shop_buy')} ({self.buy_price})", True, UI_THEME["text"]), (138, 220))
        s.blit(self.app.small_font.render(self.app.loc.t(self.offer_card["name_key"]), True, UI_THEME["muted"]), (138, 260))
        art = self.app.assets.sprite("cards", self.offer_card["id"], (250, 150), fallback=(84, 66, 122))
        s.blit(art, (170, 300))

        pygame.draw.rect(s, UI_THEME["panel"], (500, 200, 360, 320), border_radius=10)
        s.blit(self.app.font.render(f"Premium ({self.premium_price})", True, UI_THEME["text"]), (518, 220))
        s.blit(self.app.small_font.render(self.app.loc.t(self.premium_card["name_key"]), True, UI_THEME["gold"]), (518, 260))
        art2 = self.app.assets.sprite("cards", self.premium_card["id"], (250, 150), fallback=(112, 76, 140))
        s.blit(art2, (550, 300))

        pygame.draw.rect(s, UI_THEME["panel"], (880, 200, 280, 140), border_radius=10)
        s.blit(self.app.font.render(f"{self.app.loc.t('shop_remove')} ({self.remove_price})", True, UI_THEME["text"]), (892, 226))
        s.blit(self.app.small_font.render("Remueve 1 carta del mazo", True, UI_THEME["muted"]), (892, 266))

        pygame.draw.rect(s, UI_THEME["violet"], (900, 380, 240, 72), border_radius=10)
        s.blit(self.app.font.render(self.app.loc.t("shop_leave"), True, UI_THEME["text"]), (980, 404))
        if self.msg:
            s.blit(self.app.font.render(self.msg, True, UI_THEME["good"] if "No" not in self.msg else UI_THEME["bad"]), (500, 550))
