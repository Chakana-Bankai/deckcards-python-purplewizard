import pygame

from game.ui.components.card_effect_summary import infer_card_role
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.theme import UI_THEME
from game.ui.system.brand import ChakanaBrand
from game.ui.system.icons_atlas import draw_icon_with_value
from game.ui.system.layout import anchor_bottom_center, anchor_top_right, build_three_column_layout, inset, safe_area


class ShopScreen:
    def __init__(self, app, offer_card):
        self.app = app
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        all_cards = list(getattr(self.app, "_reward_card_pool", lambda: list(getattr(self.app, 'cards_data', []) or []))() or [])
        hip_pool = [
            c
            for c in all_cards
            if str(c.get("id", "")).lower().startswith("hip_")
            or ("hiperboria" in str(c.get("set", "")).lower())
            or ("hiperborea" in str(c.get("set", "")).lower())
        ]
        base_pool = [c for c in all_cards if c not in hip_pool] or list(all_cards)
        # Expose pools for diagnostics/QA without changing shop behavior.
        self.hip_pool = list(hip_pool)
        self.base_pool = list(base_pool)
        stage_level = int(run.get("level", 1) or 1)
        hip_chance = float(getattr(getattr(self.app, "meta_director", None), "hiperborea_chance", lambda r, lvl: (0.0 if lvl < 3 else (0.25 if lvl < 5 else 0.45)))(run, stage_level))
        source_pool = hip_pool if hip_pool and self.app.rng.random() < hip_chance else all_cards

        self.offer_card = self.app.rng.choice(source_pool or all_cards or [offer_card]) if all_cards else offer_card
        premium_pool = [c for c in (source_pool or all_cards) if c.get("rarity") in {"rare", "legendary", "uncommon"}]
        if not premium_pool:
            premium_pool = [c for c in all_cards if c.get("rarity") in {"rare", "legendary", "uncommon"}]
        self.rare_card = self.app.rng.choice(premium_pool) if premium_pool else self.offer_card

        relic_pool = list(getattr(self.app, "relics_data", []) or [])
        self.artifact = self.app.rng.choice(relic_pool) if relic_pool else {"id": "violet_seal", "name_key": "relic_violet_seal_name", "text_key": "relic_violet_seal_desc"}
        self._set_hint = "Hiperborea activa" if (self.offer_card in hip_pool or self.rare_card in hip_pool) else "Set base"
        self.pack_offer = self.app.rng.choice(["base_pack", "hiperborea_pack"])
        self.pack_price = 95

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
        self.preview_card = CardPreviewPanel(app=app)
        self.selected_offer = None
        self.buy_cheap_btn = pygame.Rect(0, 0, 1, 1)
        self.buy_rare_btn = pygame.Rect(0, 0, 1, 1)
        self.buy_artifact_btn = pygame.Rect(0, 0, 1, 1)
        self.buy_pack_btn = pygame.Rect(0, 0, 1, 1)
        self.active_tab = "packs"
        self.tab_rects = {
            "packs": pygame.Rect(0, 0, 1, 1),
            "relics": pygame.Rect(0, 0, 1, 1),
            "sell": pygame.Rect(0, 0, 1, 1),
        }
        self.sell_btn = pygame.Rect(0, 0, 1, 1)
        self.pack_prev_btn = pygame.Rect(0, 0, 1, 1)
        self.pack_next_btn = pygame.Rect(0, 0, 1, 1)
        self.sell_rows: list[tuple[pygame.Rect, str, int, int]] = []

        self.particles = [
            {"x": self.app.rng.randint(0, 1919), "y": self.app.rng.randint(0, 1079), "vx": self.app.rng.randint(-8, 8) / 10.0, "vy": self.app.rng.randint(2, 10) / 10.0}
            for _ in range(24)
        ]

    def _pack_label(self, pack_id: str) -> str:
        pid = str(pack_id or "").lower().strip()
        labels = {
            "base_pack": "Sobre del Origen",
            "hiperborea_pack": "Sobre de Hiperborea",
            "mystery_pack": "Sobre del Velo",
        }
        return labels.get(pid, "Sobre Ritual")

    def on_enter(self):
        pass

    def _refresh_layout(self, s):
        w, h = s.get_size()
        self._screen_size = (w, h)

        root = safe_area(w, h, ChakanaBrand.SAFE_MARGIN + 8, ChakanaBrand.BOTTOM_SAFE_MARGIN)
        shell = inset(root, 14)
        self.merchant_rect = pygame.Rect(shell.x, shell.y, shell.w, 180)

        body = pygame.Rect(shell.x, self.merchant_rect.bottom + 14, shell.w, shell.h - 194)
        preview_w = min(460, max(340, int(body.w * 0.28)))
        cards_row = pygame.Rect(body.x, body.y, body.w - preview_w - 16, max(220, body.h - 92))
        self.preview_rect = pygame.Rect(cards_row.right + 16, body.y, preview_w, cards_row.h)
        footer = pygame.Rect(body.x, cards_row.bottom + 8, body.w, body.bottom - (cards_row.bottom + 8))

        self.cheap_rect, self.rare_rect, self.artifact_rect = build_three_column_layout(cards_row, gap=24, ratios=(1, 1, 1))
        self.buy_cheap_btn = pygame.Rect(self.cheap_rect.x + 14, self.cheap_rect.bottom - 34, self.cheap_rect.w - 28, 24)
        self.buy_rare_btn = pygame.Rect(self.rare_rect.x + 14, self.rare_rect.bottom - 34, self.rare_rect.w - 28, 24)
        self.buy_artifact_btn = pygame.Rect(self.artifact_rect.x + 14, self.artifact_rect.bottom - 34, self.artifact_rect.w - 28, 24)
        footer_inner = inset(footer, 10)
        self.leave_rect = anchor_top_right(footer_inner, 260, 52, margin=0)
        self.hint_rect = pygame.Rect(footer_inner.x, footer_inner.y, max(260, footer_inner.w - self.leave_rect.w - 14), footer_inner.h)
        self.buy_pack_btn = pygame.Rect(self.leave_rect.x - 226, self.leave_rect.y, 210, 52)
        self.pack_prev_btn = pygame.Rect(self.buy_pack_btn.x - 42, self.buy_pack_btn.y + 8, 30, 36)
        self.pack_next_btn = pygame.Rect(self.buy_pack_btn.right + 10, self.buy_pack_btn.y + 8, 30, 36)
        self.hint_rect = pygame.Rect(footer_inner.x, footer_inner.y, max(260, footer_inner.w - self.leave_rect.w - self.buy_pack_btn.w - 92), footer_inner.h)

        tx = self.merchant_rect.x + 186
        ty = self.merchant_rect.y + 118
        self.tab_rects["packs"] = pygame.Rect(tx, ty, 118, 34)
        self.tab_rects["relics"] = pygame.Rect(tx + 126, ty, 118, 34)
        self.tab_rects["sell"] = pygame.Rect(tx + 252, ty, 118, 34)
        self.sell_btn = pygame.Rect(self.hint_rect.right - 220, self.hint_rect.y + 8, 210, max(36, self.hint_rect.h - 16))
    def _blit_contained(self, s: pygame.Surface, image: pygame.Surface, slot: pygame.Rect):
        iw, ih = image.get_size()
        if iw <= 0 or ih <= 0:
            return
        scale = min(slot.w / float(iw), slot.h / float(ih))
        tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
        img = pygame.transform.scale(image, (tw, th))
        s.blit(img, img.get_rect(center=slot.center).topleft)

    def _buy_card(self, card, price, tag):
        if self.app.run_state["gold"] < price:
            self.msg = "No tienes oro suficiente"
            return
        self.app.run_state["gold"] -= price
        self.app.run_state["sideboard"].append(card["id"])
        if hasattr(self.app, '_queue_set_discovery') and hasattr(self.app, '_detect_card_set'):
            self.app._queue_set_discovery(self.app._detect_card_set(card.get('id', '')))
        if hasattr(getattr(self.app, "meta_director", None), "remember"):
            self.app.meta_director.remember(self.app.run_state, "recent_shop_card_ids", str(card.get("id", "")), cap=5)
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
        if hasattr(self.app, '_add_relics_to_inventory'):
            added = self.app._add_relics_to_inventory([rid], source="shop_buy_relic")
            if not added:
                self.app.run_state["gold"] += self.artifact_price
                self.msg = "Slots de reliquia llenos"
                return
        else:
            self.app.run_state.setdefault("relics", []).append(rid)
        self.msg = f"Artefacto: {self.app.loc.t(self.artifact.get('name_key', rid))}"

    def _buy_pack(self):
        if self.app.run_state["gold"] < self.pack_price:
            self.msg = "No tienes oro suficiente"
            return
        self.app.run_state["gold"] -= self.pack_price
        self.msg = f"Sobre adquirido: {self._pack_label(self.pack_offer)}"
        reward_data = {
            "type": "choose1of3",
            "pack_category": str(self.pack_offer),
            "pack_title": self._pack_label(self.pack_offer),
            "pack_lore": "Un legado sellado por el mercader del umbral.",
        }
        if hasattr(self.app, "goto_pack_opening"):
            self.app.goto_pack_opening(reward_data=reward_data, source="shop")
        else:
            self.app.sm.set(__import__("game.ui.screens.pack_opening", fromlist=["PackOpeningScreen"]).PackOpeningScreen(self.app, reward_data=reward_data, source="shop"))
    def _duplicate_inventory_rows(self):
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        cards = list(run.get("deck", []) or []) + list(run.get("sideboard", []) or [])
        counts = {}
        for cid in cards:
            key = str(cid or "").strip()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        rows = []
        for cid, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            dup = int(cnt) - 1
            if dup <= 0:
                continue
            price = self._card_sell_price(cid)
            rows.append((cid, dup, price))
        return rows

    def _card_sell_price(self, cid: str) -> int:
        card = dict((self.app.card_defs or {}).get(str(cid), {}) or {})
        rarity = str(card.get("rarity", "common") or "common").lower()
        by = {"basic": 8, "common": 12, "uncommon": 24, "rare": 55, "legendary": 120}
        return int(by.get(rarity, 12))

    def _sell_duplicate(self, cid: str):
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        deck = list(run.get("deck", []) or [])
        side = list(run.get("sideboard", []) or [])
        total = sum(1 for x in (deck + side) if str(x) == str(cid))
        if total <= 1:
            self.msg = "No hay duplicados para vender"
            return
        # prefer sideboard removal first
        removed = False
        for arr_name in ("sideboard", "deck"):
            arr = side if arr_name == "sideboard" else deck
            for i, x in enumerate(arr):
                if str(x) == str(cid):
                    arr.pop(i)
                    removed = True
                    break
            if removed:
                break
        if not removed:
            self.msg = "No hay duplicados para vender"
            return
        run["deck"] = deck
        run["sideboard"] = side
        gain = self._card_sell_price(cid)
        run["gold"] = int(run.get("gold", 0) or 0) + gain
        self.msg = f"Vendida copia de {cid} (+{gain} oro)"

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

            for tid, tr in self.tab_rects.items():
                if tr.collidepoint(pos):
                    self.active_tab = tid
                    return

            if self.pack_prev_btn.collidepoint(pos):
                seq = ["base_pack", "hiperborea_pack"]
                cur = seq.index(self.pack_offer) if self.pack_offer in seq else 0
                self.pack_offer = seq[(cur - 1) % len(seq)]
                return
            if self.pack_next_btn.collidepoint(pos):
                seq = ["base_pack", "hiperborea_pack"]
                cur = seq.index(self.pack_offer) if self.pack_offer in seq else 0
                self.pack_offer = seq[(cur + 1) % len(seq)]
                return

            if self.active_tab == "packs" and self.buy_cheap_btn.collidepoint(pos):
                self._buy_card(self.offer_card, self.cheap_price, "Compra")
            elif self.active_tab == "packs" and self.buy_pack_btn.collidepoint(pos):
                self._buy_pack()
            elif self.active_tab == "packs" and self.buy_rare_btn.collidepoint(pos):
                self._buy_card(self.rare_card, self.rare_price, "Compra rara")
            elif self.active_tab == "relics" and self.buy_artifact_btn.collidepoint(pos):
                self._buy_artifact()
            elif self.active_tab == "sell" and self.sell_btn.collidepoint(pos):
                rows = self._duplicate_inventory_rows()
                if rows:
                    self._sell_duplicate(rows[0][0])
                else:
                    self.msg = "No hay duplicados para vender"
            elif self.cheap_rect.collidepoint(pos):
                self.selected_offer = "cheap"
            elif self.rare_rect.collidepoint(pos):
                self.selected_offer = "rare"
            elif self.artifact_rect.collidepoint(pos):
                self.selected_offer = "artifact"
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
        s.blit(self.app.tiny_font.render(name[:26], True, UI_THEME["muted"]), (rect.x + 14, rect.y + 70))
        role = infer_card_role(card).replace("_", " ").title()
        rarity = str(card.get("rarity", "common")).title()
        s.blit(self.app.tiny_font.render(f"{rarity} | {role}", True, UI_THEME["text"]), (rect.x + 14, rect.y + 92))

        art_slot = pygame.Rect(rect.x + 14, rect.y + 116, rect.w - 28, rect.h - 152)
        pygame.draw.rect(s, UI_THEME["panel_2"], art_slot, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], art_slot, 1, border_radius=10)
        art = self.app.assets.sprite("cards", card.get("id", ""), (260, 360), fallback=(84, 66, 122))
        self._blit_contained(s, art, art_slot.inflate(-18, -18))
        s.blit(self.app.tiny_font.render("Click para previsualizar", True, UI_THEME["gold"]), (rect.x + 14, rect.bottom - 56))

    def _offer_hover_data(self, mouse_pos):
        if self.cheap_rect.collidepoint(mouse_pos):
            return {"type": "card", "title": "Rito menor", "price": self.cheap_price, "card": self.offer_card}
        if self.rare_rect.collidepoint(mouse_pos):
            return {"type": "card", "title": "Rito elevado", "price": self.rare_price, "card": self.rare_card}
        if self.artifact_rect.collidepoint(mouse_pos):
            return {"type": "artifact", "title": "Reliquia del Umbral", "price": self.artifact_price, "artifact": self.artifact}
        if self.selected_offer == "cheap":
            return {"type": "card", "title": "Rito menor", "price": self.cheap_price, "card": self.offer_card}
        if self.selected_offer == "rare":
            return {"type": "card", "title": "Rito elevado", "price": self.rare_price, "card": self.rare_card}
        if self.selected_offer == "artifact":
            return {"type": "artifact", "title": "Reliquia del Umbral", "price": self.artifact_price, "artifact": self.artifact}
        return None

    def _draw_preview_panel(self, s, hover_data):
        pygame.draw.rect(s, UI_THEME["panel_2"], self.preview_rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.preview_rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Vista previa ritual", True, UI_THEME["gold"]), (self.preview_rect.x + 14, self.preview_rect.y + 12))

        if not hover_data:
            s.blit(self.app.tiny_font.render("Pasa el cursor sobre una oferta.", True, UI_THEME["muted"]), (self.preview_rect.x + 14, self.preview_rect.y + 46))
            s.blit(self.app.tiny_font.render("Aqui veras costo, rol y descripcion.", True, UI_THEME["muted"]), (self.preview_rect.x + 14, self.preview_rect.y + 70))
            return

        y = self.preview_rect.y + 46
        s.blit(self.app.small_font.render(hover_data["title"], True, UI_THEME["text"]), (self.preview_rect.x + 14, y))
        y += 28
        draw_icon_with_value(s, "gold", int(hover_data["price"]), UI_THEME["gold"], self.app.small_font, self.preview_rect.x + 14, y - 3, size=1)
        y += 28

        frame = pygame.Rect(self.preview_rect.x + 12, y + 2, self.preview_rect.w - 24, self.preview_rect.h - (y - self.preview_rect.y) - 14)
        pygame.draw.rect(s, UI_THEME["panel"], frame, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], frame, 1, border_radius=10)

        art_slot = pygame.Rect(frame.x + 12, frame.y + 12, frame.w - 24, int(frame.h * 0.62))
        pygame.draw.rect(s, UI_THEME["panel_2"], art_slot, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], art_slot, 1, border_radius=8)

        text_y = art_slot.bottom + 10
        text_w = frame.w - 24

        if hover_data["type"] == "card":
            card = hover_data["card"]
            card_rect = art_slot.inflate(-8, -8)
            self.preview_card.render(s, card_rect, card, app=self.app, render_context="shop_view")
            name = self.app.loc.t(card.get("name_key", card.get("id", "Carta")))
            role = infer_card_role(card).replace("_", " ").title()
            effect = self.app.loc.t(card.get("text_key", ""))
            s.blit(self.app.small_font.render(name[:30], True, UI_THEME["text"]), (frame.x + 12, text_y))
            s.blit(self.app.tiny_font.render(f"Rol: {role}", True, UI_THEME["muted"]), (frame.x + 12, text_y + 24))
            s.blit(self.app.tiny_font.render((effect or "Sin descripcion")[:52], True, UI_THEME["text"]), (frame.x + 12, text_y + 44))
            return

        artifact = hover_data["artifact"]
        rid = artifact.get("id", "artifact")
        name = self.app.loc.t(artifact.get("name_key", rid))
        desc = self.app.loc.t(artifact.get("text_key", "")) or "Reliquia antigua del comerciante."
        relic_art = self.app.assets.sprite("relics", rid, (176, 176), fallback=(96, 76, 124))
        self._blit_contained(s, relic_art, art_slot.inflate(-10, -10))

        s.blit(self.app.small_font.render(name[:30], True, UI_THEME["text"]), (frame.x + 12, text_y))
        s.blit(self.app.tiny_font.render("Tipo: Reliquia", True, UI_THEME["muted"]), (frame.x + 12, text_y + 24))
        for i, line in enumerate([p.strip() for p in desc.split(".") if p.strip()][:2]):
            s.blit(self.app.tiny_font.render(line[:54], True, UI_THEME["text"]), (frame.x + 12, text_y + 44 + i * 18))

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
        s.blit(self.app.big_font.render("Comerciante del Umbral", True, UI_THEME["text"]), (self.merchant_rect.x + 18, self.merchant_rect.y + 10))
        s.blit(self.app.tiny_font.render("Intercambio ritual y reliquias del viaje", True, UI_THEME["muted"]), (self.merchant_rect.x + 20, self.merchant_rect.y + 46))
        s.blit(self.app.tiny_font.render(self._set_hint, True, UI_THEME["gold"]), (self.merchant_rect.x + 20, self.merchant_rect.y + 66))
        s.blit(self.app.tiny_font.render("Categorias: Cartas / Reliquias / Sobres", True, UI_THEME["muted"]), (self.merchant_rect.x + 20, self.merchant_rect.y + 86))
        for tid, tr in self.tab_rects.items():
            on = (tid == self.active_tab)
            pygame.draw.rect(s, UI_THEME["panel_2"], tr, border_radius=8)
            pygame.draw.rect(s, UI_THEME["gold"] if on else UI_THEME["accent_violet"], tr, 2 if on else 1, border_radius=8)
            lbl = {"packs": "Packs", "relics": "Reliquias", "sell": "Vender"}.get(tid, tid)
            s.blit(self.app.tiny_font.render(lbl, True, UI_THEME["gold"] if on else UI_THEME["muted"]), (tr.x + 10, tr.y + 9))
        gold_rect = anchor_top_right(self.merchant_rect, 320, 46, margin=18)
        pygame.draw.rect(s, UI_THEME["panel_2"], gold_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], gold_rect, 2, border_radius=10)
        s.blit(self.app.tiny_font.render("ORO DISPONIBLE", True, UI_THEME["muted"]), (gold_rect.x + 10, gold_rect.y + 4))
        draw_icon_with_value(s, "gold", int(self.app.run_state["gold"]), UI_THEME["gold"], self.app.small_font, gold_rect.x + 10, gold_rect.y + 18, size=2)

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
        thumb_slot = pygame.Rect(self.artifact_rect.right - 122, self.artifact_rect.y + 58, 108, 108)
        pygame.draw.rect(s, UI_THEME["panel_2"], thumb_slot, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], thumb_slot, 1, border_radius=8)
        relic_thumb = self.app.assets.sprite("relics", rid, (128, 128), fallback=(96, 76, 124))
        self._blit_contained(s, relic_thumb, thumb_slot.inflate(-14, -14))
        s.blit(self.app.tiny_font.render(self.app.loc.t(self.artifact.get("name_key", rid))[:24], True, UI_THEME["muted"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 70))
        desc = self.app.loc.t(self.artifact.get("text_key", ""))
        for i, line in enumerate((desc or "Reliquia antigua del comerciante.").split(".")[:2]):
            line = line.strip()
            if line:
                s.blit(self.app.tiny_font.render(line[:44], True, UI_THEME["text"]), (self.artifact_rect.x + 14, self.artifact_rect.y + 104 + i * 20))
        s.blit(self.app.tiny_font.render("Click para previsualizar", True, UI_THEME["gold"]), (self.artifact_rect.x + 14, self.artifact_rect.bottom - 56))

        self._draw_preview_panel(s, self._offer_hover_data(mouse))

        for rect in (self.buy_cheap_btn, self.buy_rare_btn, self.buy_artifact_btn):
            pygame.draw.rect(s, UI_THEME["violet"], rect, border_radius=7)
            pygame.draw.rect(s, UI_THEME["gold"], rect, 1, border_radius=7)
            lbl = self.app.tiny_font.render("COMPRAR", True, UI_THEME["text"])
            s.blit(lbl, lbl.get_rect(center=rect.center))


        pygame.draw.rect(s, UI_THEME["violet"], self.buy_pack_btn, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.buy_pack_btn, 2, border_radius=10)
        ptxt = self.app.tiny_font.render(f"{self._pack_label(self.pack_offer).upper()} ({self.pack_price})", True, UI_THEME["text"])
        s.blit(ptxt, ptxt.get_rect(center=self.buy_pack_btn.center))
        pygame.draw.rect(s, UI_THEME["panel_2"], self.pack_prev_btn, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.pack_prev_btn, 1, border_radius=8)
        s.blit(self.app.small_font.render("<", True, UI_THEME["text"]), (self.pack_prev_btn.x + 9, self.pack_prev_btn.y + 4))
        pygame.draw.rect(s, UI_THEME["panel_2"], self.pack_next_btn, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.pack_next_btn, 1, border_radius=8)
        s.blit(self.app.small_font.render(">", True, UI_THEME["text"]), (self.pack_next_btn.x + 9, self.pack_next_btn.y + 4))
        pygame.draw.rect(s, UI_THEME["violet"], self.leave_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.leave_rect, 2, border_radius=10)
        leave_lbl = self.app.font.render("Volver", True, UI_THEME["text"])
        s.blit(leave_lbl, leave_lbl.get_rect(center=self.leave_rect.center))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.hint_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.hint_rect, 1, border_radius=10)
        hint_lbl = self.app.tiny_font.render(self.hint, True, UI_THEME["muted"])
        s.blit(hint_lbl, (self.hint_rect.x + 12, self.hint_rect.centery - hint_lbl.get_height() // 2))

        if self.active_tab == "sell":
            rows = self._duplicate_inventory_rows()
            info = "Sin duplicados" if not rows else ", ".join([f"{cid} x{dup} (+{price})" for cid, dup, price in rows[:2]])
            s.blit(self.app.tiny_font.render(f"Duplicados: {info}", True, UI_THEME["text"]), (self.hint_rect.x + 12, self.hint_rect.y + 8))
            pygame.draw.rect(s, UI_THEME["violet"], self.sell_btn, border_radius=10)
            pygame.draw.rect(s, UI_THEME["gold"], self.sell_btn, 2, border_radius=10)
            s.blit(self.app.tiny_font.render("VENDER 1 DUPLICADA", True, UI_THEME["text"]), self.app.tiny_font.render("VENDER 1 DUPLICADA", True, UI_THEME["text"]).get_rect(center=self.sell_btn.center))

        if self.msg:
            col = UI_THEME["good"] if "No" not in self.msg and "Ya" not in self.msg else UI_THEME["bad"]
            s.blit(self.app.font.render(self.msg, True, col), (self.merchant_rect.x + 20, self.hint_rect.y - 32))

