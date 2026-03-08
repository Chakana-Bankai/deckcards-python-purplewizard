import pygame

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.theme import UI_THEME
from game.ui.system.brand import ChakanaBrand
from game.ui.system.icons import draw_icon_with_value
from game.ui.system.layout import anchor_bottom_center, anchor_top_right, build_three_column_layout, inset, safe_area


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
        self.merchant_rect = pygame.Rect(0, 0, 1, 1)
        self.hint_rect = pygame.Rect(0, 0, 1, 1)
        self.preview_rect = pygame.Rect(0, 0, 1, 1)
        self._screen_size = (1920, 1080)

        self.particles = [
            {"x": self.app.rng.randint(0, 1919), "y": self.app.rng.randint(0, 1079), "vx": self.app.rng.randint(-8, 8) / 10.0, "vy": self.app.rng.randint(2, 10) / 10.0}
            for _ in range(24)
        ]

    def on_enter(self):
        pass

    def _refresh_layout(self, s):
        w, h = s.get_size()
        self._screen_size = (w, h)

        root = safe_area(w, h, ChakanaBrand.SAFE_MARGIN + 8, ChakanaBrand.BOTTOM_SAFE_MARGIN)
        shell = inset(root, 14)
        self.merchant_rect = pygame.Rect(shell.x, shell.y, shell.w, 180)

        body = pygame.Rect(shell.x, self.merchant_rect.bottom + 14, shell.w, shell.h - 194)
        preview_w = min(420, max(320, int(body.w * 0.26)))
        cards_row = pygame.Rect(body.x, body.y, body.w - preview_w - 16, max(220, body.h - 92))
        self.preview_rect = pygame.Rect(cards_row.right + 16, body.y, preview_w, cards_row.h)
        footer = pygame.Rect(body.x, cards_row.bottom + 8, body.w, body.bottom - (cards_row.bottom + 8))

        self.cheap_rect, self.rare_rect, self.artifact_rect = build_three_column_layout(cards_row, gap=24, ratios=(1, 1, 1))
        self.hint_rect = inset(footer, 10)
        self.leave_rect = anchor_bottom_center(root, 300, 58, margin=0)

    def _buy_card(self, card, price, tag):
        if self.app.run_state["gold"] < price:
            self.msg = "No tienes oro suficiente"
            return
        self.app.run_state["gold"] -= price
        self.app.run_state["sideboard"].append(card["id"])
        self.msg = f"{tag}: {self.app.loc.t(card.get('name_key', card['id']))}"

    def _buy_artifact(self):
        if self.app.run_state["gold"] < self.artifact_price:
            self.msg = "No tienes oro suficiente"
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
        w, h = self._screen_size
        for p in self.particles:
            p["x"] += p["vx"] * dt * 60
            p["y"] += p["vy"] * dt * 60
            if p["y"] > h + 8:
                p["y"] = -6
            if p["x"] < -8:
                p["x"] = w + 8
            if p["x"] > w + 8:
                p["x"] = -8

    def _draw_offer_card(self, s, rect, card, title, price, tier_col):
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=14)
        pygame.draw.rect(s, tier_col, rect, 2, border_radius=14)
        s.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (rect.x + 14, rect.y + 12))
        draw_icon_with_value(s, "gold", int(price), UI_THEME["gold"], self.app.small_font, rect.x + 14, rect.y + 42, size=1)

        name = self.app.loc.t(card.get("name_key", card.get("id", "carta")))
        s.blit(self.app.tiny_font.render(name, True, UI_THEME["muted"]), (rect.x + 14, rect.y + 70))
        role = infer_card_role(card).replace("_", " ").title()
        rarity = str(card.get("rarity", "common")).title()
        s.blit(self.app.tiny_font.render(f"{rarity} | {role}", True, UI_THEME["text"]), (rect.x + 14, rect.y + 92))

        art = self.app.assets.sprite("cards", card.get("id", ""), (max(140, rect.w - 84), max(140, rect.h - 190)), fallback=(84, 66, 122))
        art_r = art.get_rect(center=(rect.centerx, rect.y + rect.h * 0.62))
        s.blit(art, art_r.topleft)
        s.blit(self.app.tiny_font.render("Click para comprar", True, UI_THEME["gold"]), (rect.x + 14, rect.bottom - 28))

    def _offer_hover_data(self, mouse_pos):
        if self.cheap_rect.collidepoint(mouse_pos):
            return {"type": "card", "title": "Rito menor", "price": self.cheap_price, "card": self.offer_card}
        if self.rare_rect.collidepoint(mouse_pos):
            return {"type": "card", "title": "Rito elevado", "price": self.rare_price, "card": self.rare_card}
        if self.artifact_rect.collidepoint(mouse_pos):
            return {"type": "artifact", "title": "Reliquia del Umbral", "price": self.artifact_price, "artifact": self.artifact}
        return None

    def _draw_preview_panel(self, s, hover_data):
        pygame.draw.rect(s, UI_THEME["panel_2"], self.preview_rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.preview_rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Vista previa", True, UI_THEME["gold"]), (self.preview_rect.x + 14, self.preview_rect.y + 12))

        if not hover_data:
            s.blit(self.app.tiny_font.render("Pasa el cursor sobre una oferta.", True, UI_THEME["muted"]), (self.preview_rect.x + 14, self.preview_rect.y + 46))
            s.blit(self.app.tiny_font.render("Veras costo, rol y efecto principal.", True, UI_THEME["muted"]), (self.preview_rect.x + 14, self.preview_rect.y + 70))
            return

        y = self.preview_rect.y + 46
        s.blit(self.app.small_font.render(hover_data["title"], True, UI_THEME["text"]), (self.preview_rect.x + 14, y))
        y += 28
        draw_icon_with_value(s, "gold", int(hover_data['price']), UI_THEME["gold"], self.app.tiny_font, self.preview_rect.x + 14, y - 1, size=1)
        y += 24

        if hover_data["type"] == "card":
            card = hover_data["card"]
            name = self.app.loc.t(card.get("name_key", card.get("id", "carta")))
            role = infer_card_role(card).replace("_", " ").title()
            summary = summarize_card_effect(card)
            effect_bits = []
            for key, lbl in (("damage", "Danio"), ("block", "Bloqueo"), ("draw", "Robo"), ("scry", "Prever"), ("harmony_delta", "Armonia"), ("rupture", "Ruptura")):
                val = int(summary.get(key, 0) or 0)
                if val:
                    if key == "harmony_delta":
                        effect_bits.append(f"{lbl} {val:+d}")
                    else:
                        effect_bits.append(f"{lbl} {val}")
            effect_line = " | ".join(effect_bits[:3]) if effect_bits else "Sinergia tactica variable."

            s.blit(self.app.small_font.render(name, True, UI_THEME["text"]), (self.preview_rect.x + 14, y))
            y += 30
            s.blit(self.app.tiny_font.render(f"Rol: {role}", True, UI_THEME["muted"]), (self.preview_rect.x + 14, y))
            y += 22
            s.blit(self.app.tiny_font.render(effect_line[:52], True, UI_THEME["text"]), (self.preview_rect.x + 14, y))
            y += 26
            s.blit(self.app.tiny_font.render("Compra directa al sideboard.", True, UI_THEME["muted"]), (self.preview_rect.x + 14, y))
            return

        artifact = hover_data["artifact"]
        rid = artifact.get("id", "artifact")
        name = self.app.loc.t(artifact.get("name_key", rid))
        desc = self.app.loc.t(artifact.get("text_key", "")) or "Reliquia antigua del comerciante."
        relic_art = self.app.assets.sprite("relics", rid, (112, 112), fallback=(96, 76, 124))
        relic_rect = relic_art.get_rect(topleft=(self.preview_rect.x + 14, y))
        s.blit(relic_art, relic_rect.topleft)
        s.blit(self.app.small_font.render(name, True, UI_THEME["text"]), (relic_rect.right + 12, y + 2))
        y += 30
        s.blit(self.app.tiny_font.render("Tipo: Reliquia", True, UI_THEME["muted"]), (relic_rect.right + 12, y))
        y += 22
        for line in desc.split(".")[:4]:
            txt = line.strip()
            if txt:
                s.blit(self.app.tiny_font.render(txt[:52], True, UI_THEME["text"]), (self.preview_rect.x + 14, y))
                y += 22

    def render(self, s):
        self._refresh_layout(s)
        self.app.bg_gen.render_parallax(s, "hanan", 3030, pygame.time.get_ticks() * 0.015, particles_on=True)
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())

        veil = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        veil.fill((18, 20, 34, 134))
        s.blit(veil, (0, 0))

        for p in self.particles:
            pygame.draw.circle(s, (138, 148, 188), (int(p["x"]), int(p["y"])), 2)

        pygame.draw.rect(s, UI_THEME["panel"], self.merchant_rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.merchant_rect, 2, border_radius=14)
        s.blit(self.app.big_font.render("Comerciante del Umbral", True, UI_THEME["text"]), (self.merchant_rect.x + 18, self.merchant_rect.y + 14))
        gold_rect = anchor_top_right(self.merchant_rect, 250, 32, margin=20)
        draw_icon_with_value(s, "gold", int(self.app.run_state["gold"]), UI_THEME["gold"], self.app.font, gold_rect.x, gold_rect.y, size=1)

        face_box = pygame.Rect(self.merchant_rect.x + 18, self.merchant_rect.y + 56, 140, 110)
        pygame.draw.rect(s, UI_THEME["panel_2"], face_box, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], face_box, 1, border_radius=10)
        face = self.app.assets.sprite("guides", "arcane_hacker", (100, 100), fallback=(70, 52, 102))
        s.blit(face, face.get_rect(center=face_box.center).topleft)
        s.blit(self.app.tiny_font.render("Comerciante del Umbral", True, UI_THEME["muted"]), (face_box.right + 16, face_box.y + 12))
        s.blit(self.app.tiny_font.render("Intercambio ritual en calma", True, UI_THEME["muted"]), (face_box.right + 16, face_box.y + 38))

        self._draw_offer_card(s, self.cheap_rect, self.offer_card, "Rito menor", self.cheap_price, (126, 176, 136))
        self._draw_offer_card(s, self.rare_rect, self.rare_card, "Rito elevado", self.rare_price, (166, 136, 216))

        pygame.draw.rect(s, UI_THEME["panel"], self.artifact_rect, border_radius=14)
        pygame.draw.rect(s, (220, 178, 92), self.artifact_rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Reliquia del Umbral", True, UI_THEME["gold"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 12))
        draw_icon_with_value(s, "gold", int(self.artifact_price), UI_THEME["gold"], self.app.small_font, self.artifact_rect.x + 14, self.artifact_rect.y + 44, size=1)
        rid = self.artifact.get("id", "artifact")
        relic_thumb = self.app.assets.sprite("relics", rid, (96, 96), fallback=(96, 76, 124))
        s.blit(relic_thumb, (self.artifact_rect.right - 112, self.artifact_rect.y + 58))
        s.blit(self.app.tiny_font.render(self.app.loc.t(self.artifact.get("name_key", rid)), True, UI_THEME["muted"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 70))
        desc = self.app.loc.t(self.artifact.get("text_key", ""))
        for i, line in enumerate((desc or "Reliquia antigua del comerciante.").split(".")[:2]):
            line = line.strip()
            if line:
                s.blit(self.app.tiny_font.render(line[:44], True, UI_THEME["text"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 104 + i * 20))
        s.blit(self.app.tiny_font.render("Click para comprar", True, UI_THEME["gold"]), (self.artifact_rect.x + 14, self.artifact_rect.bottom - 28))

        self._draw_preview_panel(s, self._offer_hover_data(mouse))

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
