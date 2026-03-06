import pygame

from game.ui.theme import UI_THEME


class ShopScreen:
    def __init__(self, app, offer_card):
        self.app = app
        self.offer_card = offer_card
        premium_pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary", "uncommon"}]
        self.rare_card = self.app.rng.choice(premium_pool) if premium_pool else offer_card
        relic_pool = list(getattr(self.app, "relics_data", []) or [])
        self.artifact = self.app.rng.choice(relic_pool) if relic_pool else {"id": "violet_seal", "name_key": "relic_violet_seal_name", "text_key": "relic_violet_seal_desc"}

        self.msg = ""
        self.hint = "El comerciante conoce caminos olvidados."

        self.cheap_price = 35
        self.rare_price = 85
        self.artifact_price = 130

        self.cheap_rect = pygame.Rect(0, 0, 1, 1)
        self.rare_rect = pygame.Rect(0, 0, 1, 1)
        self.artifact_rect = pygame.Rect(0, 0, 1, 1)
        self.leave_rect = pygame.Rect(0, 0, 1, 1)
        self.particles = [
            {"x": self.app.rng.randint(0, 1919), "y": self.app.rng.randint(0, 1079), "vx": self.app.rng.randint(-8, 8) / 10.0, "vy": self.app.rng.randint(2, 10) / 10.0}
            for _ in range(24)
        ]

    def on_enter(self):
        pass

    def _refresh_layout(self, s):
        w, h = s.get_size()
        content = pygame.Rect(86, 150, w - 172, h - 270)
        top_h = 180
        middle_h = content.h - top_h - 120

        self.merchant_rect = pygame.Rect(content.x, content.y, content.w, top_h)
        row = pygame.Rect(content.x, self.merchant_rect.bottom + 14, content.w, middle_h)
        card_w = (row.w - 24 * 2) // 3
        self.cheap_rect = pygame.Rect(row.x, row.y, card_w, row.h)
        self.rare_rect = pygame.Rect(self.cheap_rect.right + 24, row.y, card_w, row.h)
        self.artifact_rect = pygame.Rect(self.rare_rect.right + 24, row.y, card_w, row.h)

        self.leave_rect = pygame.Rect(w // 2 - 150, h - 94, 300, 58)
        self.hint_rect = pygame.Rect(content.x + 18, content.bottom - 84, content.w - 36, 60)

    def _buy_card(self, card, price, tag):
        if self.app.run_state["gold"] < price:
            self.msg = "No alcanza oro"
            return
        self.app.run_state["gold"] -= price
        self.app.run_state["sideboard"].append(card["id"])
        self.msg = f"{tag}: {self.app.loc.t(card.get('name_key', card['id']))}"

    def _buy_artifact(self):
        if self.app.run_state["gold"] < self.artifact_price:
            self.msg = "No alcanza oro"
            return
        rid = self.artifact.get("id")
        if rid in self.app.run_state.get("relics", []):
            self.msg = "Ya posees este artefacto"
            return
        self.app.run_state["gold"] -= self.artifact_price
        self.app.run_state.setdefault("relics", []).append(rid)
        self.msg = f"Artefacto: {self.app.loc.t(self.artifact.get('name_key', rid))}"

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

            if self.cheap_rect.collidepoint(pos):
                self._buy_card(self.offer_card, self.cheap_price, "Compra")
            elif self.rare_rect.collidepoint(pos):
                self._buy_card(self.rare_card, self.rare_price, "Compra rara")
            elif self.artifact_rect.collidepoint(pos):
                self._buy_artifact()
            elif self.leave_rect.collidepoint(pos):
                self.app._complete_current_node()
                self.app.goto_map()

    def update(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt * 60
            p["y"] += p["vy"] * dt * 60
            if p["y"] > 1088:
                p["y"] = -6
            if p["x"] < -8:
                p["x"] = 1928
            if p["x"] > 1928:
                p["x"] = -8

    def _draw_offer_card(self, s, rect, card, title, price, tier_col):
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=14)
        pygame.draw.rect(s, tier_col, rect, 2, border_radius=14)
        s.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (rect.x + 14, rect.y + 12))
        s.blit(self.app.small_font.render(f"{price} oro", True, UI_THEME["text"]), (rect.x + 14, rect.y + 44))
        s.blit(self.app.tiny_font.render(self.app.loc.t(card.get("name_key", card.get("id", "carta"))), True, UI_THEME["muted"]), (rect.x + 14, rect.y + 70))
        art = self.app.assets.sprite("cards", card.get("id", ""), (rect.w - 26, rect.h - 128), fallback=(84, 66, 122))
        art_r = art.get_rect(center=(rect.centerx, rect.y + rect.h * 0.62))
        s.blit(art, art_r.topleft)

    def render(self, s):
        self._refresh_layout(s)
        self.app.bg_gen.render_parallax(s, "hanan", 3030, pygame.time.get_ticks() * 0.015, particles_on=True)

        veil = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        veil.fill((18, 20, 34, 134))
        s.blit(veil, (0, 0))

        for p in self.particles:
            pygame.draw.circle(s, (138, 148, 188), (int(p["x"]), int(p["y"])), 2)

        pygame.draw.rect(s, UI_THEME["panel"], self.merchant_rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.merchant_rect, 2, border_radius=14)
        s.blit(self.app.big_font.render(self.app.loc.t("shop_title"), True, UI_THEME["text"]), (self.merchant_rect.x + 18, self.merchant_rect.y + 14))
        s.blit(self.app.font.render(f"{self.app.loc.t('gold')}: {self.app.run_state['gold']}", True, UI_THEME["gold"]), (self.merchant_rect.right - 260, self.merchant_rect.y + 26))

        face_box = pygame.Rect(self.merchant_rect.x + 18, self.merchant_rect.y + 56, 140, 110)
        pygame.draw.rect(s, UI_THEME["panel_2"], face_box, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], face_box, 1, border_radius=10)
        face = self.app.assets.sprite("guides", "arcane_hacker", (100, 100), fallback=(70, 52, 102))
        s.blit(face, face.get_rect(center=face_box.center).topleft)
        s.blit(self.app.tiny_font.render("Mercader", True, UI_THEME["muted"]), (face_box.right + 16, face_box.y + 12))
        s.blit(self.app.tiny_font.render("Tienda en calma meditativa", True, UI_THEME["muted"]), (face_box.right + 16, face_box.y + 38))

        self._draw_offer_card(s, self.cheap_rect, self.offer_card, "Tier: cheap", self.cheap_price, (126, 176, 136))
        self._draw_offer_card(s, self.rare_rect, self.rare_card, "Tier: rare", self.rare_price, (166, 136, 216))

        pygame.draw.rect(s, UI_THEME["panel"], self.artifact_rect, border_radius=14)
        pygame.draw.rect(s, (220, 178, 92), self.artifact_rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Tier: artifact", True, UI_THEME["gold"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 12))
        s.blit(self.app.small_font.render(f"{self.artifact_price} oro", True, UI_THEME["text"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 44))
        rid = self.artifact.get("id", "artifact")
        s.blit(self.app.tiny_font.render(self.app.loc.t(self.artifact.get("name_key", rid)), True, UI_THEME["muted"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 70))
        desc = self.app.loc.t(self.artifact.get("text_key", ""))
        for i, line in enumerate((desc or "Reliquia antigua del comerciante.").split(".")[:2]):
            line = line.strip()
            if line:
                s.blit(self.app.tiny_font.render(line[:44], True, UI_THEME["text"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 104 + i * 20))

        pygame.draw.rect(s, UI_THEME["violet"], self.leave_rect, border_radius=10)
        leave_lbl = self.app.font.render(self.app.loc.t("shop_leave"), True, UI_THEME["text"])
        s.blit(leave_lbl, leave_lbl.get_rect(center=self.leave_rect.center))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.hint_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.hint_rect, 1, border_radius=10)
        hint_lbl = self.app.tiny_font.render(self.hint, True, UI_THEME["muted"])
        s.blit(hint_lbl, hint_lbl.get_rect(center=self.hint_rect.center))

        if self.msg:
            col = UI_THEME["good"] if "No" not in self.msg and "Ya" not in self.msg else UI_THEME["bad"]
            s.blit(self.app.font.render(self.msg, True, col), (self.merchant_rect.x + 20, self.hint_rect.y - 32))
