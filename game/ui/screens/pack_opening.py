import pygame

from game.combat.card import CardDef, CardInstance
from game.systems.reward_system import PACK_ECONOMY
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_renderer import render_card_small
from game.ui.theme import UI_THEME
from game.ui.system.pack_covers import draw_pack_cover


class PackOpeningScreen:
    def __init__(self, app, reward_data=None, source: str = "reward"):
        self.app = app
        self.reward_data = reward_data if isinstance(reward_data, dict) else {}
        self.source = str(source or "reward")

        self.msg = "Elige 1 de 3 sobres rituales"
        self.packs = [
            pygame.Rect(96, 198, 350, 562),
            pygame.Rect(486, 198, 350, 562),
            pygame.Rect(876, 198, 350, 562),
        ]
        self.pack_defs = [
            {
                "id": "base_pack",
                "title": "Sobre del Origen",
                "subtitle": "Fundamentos",
                "desc": "Cartas base para sostener consistencia.",
                "flavor": "El mazo aprende a respirar antes del riesgo.",
                "color": (140, 128, 186),
            },
            {
                "id": "hiperborea_pack",
                "title": "Sobre de Hiperborea",
                "subtitle": "Conocimiento polar",
                "desc": "Tecnicas antiguas de precision y rito.",
                "flavor": "Sellos helados emergen desde civilizaciones olvidadas.",
                "color": (144, 208, 236),
            },
            {
                "id": "mystery_pack",
                "title": "Sobre del Velo",
                "subtitle": "Umbral incierto",
                "desc": "Mezcla impredecible con potencial alto.",
                "flavor": "El vacio entrega poder a cambio de incertidumbre.",
                "color": (196, 138, 238),
            },
        ]

        self.selected_pack = None
        self.forced_pack_id = str(self.reward_data.get("pack_category", "") or "").lower()
        self._pack_alias = {
            "normal_pack": "base_pack",
            "rare_choice_pack": "mystery_pack",
            "ritual_reward_pack": "mystery_pack",
            "legendary_reward": "mystery_pack",
            "base_pack": "base_pack",
            "hiperborea_pack": "hiperborea_pack",
            "mystery_pack": "mystery_pack",
        }

        self.cards = []
        self.selected_card = None
        self.hover_card = None
        self.confirm_rect = pygame.Rect(1290, 962, 280, 58)
        self.back_rect = pygame.Rect(982, 962, 250, 58)
        self.preview = CardPreviewPanel(app=app)
        self.legendary_pick_mode = False

        source_cards = list(getattr(self.app, "_reward_card_pool", lambda: list(getattr(self.app, "cards_data", []) or []))() or [])
        pool_all = [c for c in source_cards if c.get("rarity") in {"rare", "legendary", "uncommon", "common", "basic"}] or source_cards
        self.base_pool = [
            c
            for c in pool_all
            if not (
                str(c.get("id", "")).lower().startswith("hip_")
                or ("hiperboria" in str(c.get("set", "")).lower())
                or ("hiperborea" in str(c.get("set", "")).lower())
            )
        ] or list(pool_all)
        self.hip_pool = [c for c in pool_all if c not in self.base_pool]
        self.pool = list(pool_all)

    def on_enter(self):
        self.app.rng.shuffle(self.pack_defs)
        forced_id = self._pack_alias.get(self.forced_pack_id, self.forced_pack_id)
        auto_open_forced = self.source in {"shop", "shop_pack", "levelup_pending", "boss_reward", "direct_pack"}
        if forced_id and auto_open_forced:
            idx = next((i for i, x in enumerate(self.pack_defs) if str(x.get("id", "")).lower() == forced_id), None)
            if idx is not None:
                self._open_pack(idx)
                return
        self.selected_pack = None
        self.cards = []
        self.selected_card = None
        self.hover_card = None
        if self.source == "reward":
            self.msg = "Elige 1 de 3 sobres rituales"

    def _card_pool_by_pack(self, pack_id: str):
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        level = int(run.get("level", 1) or 1)
        hip_chance = float(
            getattr(getattr(self.app, "meta_director", None), "hiperborea_chance", lambda _run, lvl: (0.0 if lvl < 3 else (0.25 if lvl < 5 else 0.45)))(run, level)
        )

        base_pool = list(self.base_pool)
        hip_pool = list(self.hip_pool)
        all_pool = list(self.pool)

        common_pool = [c for c in all_pool if c.get("rarity") in {"basic", "common"}] or all_pool
        uncommon_pool = [c for c in all_pool if c.get("rarity") == "uncommon"] or common_pool
        rare_pool = [c for c in all_pool if c.get("rarity") == "rare"] or uncommon_pool
        legendary_pool = [c for c in all_pool if c.get("rarity") == "legendary"] or rare_pool

        if pack_id == "base_pack":
            source = [c for c in (base_pool or all_pool) if c.get("rarity") in {"basic", "common", "uncommon"}] or (base_pool or all_pool)
            return source, legendary_pool, rare_pool, uncommon_pool, common_pool

        if pack_id == "hiperborea_pack":
            source = [
                c
                for c in (hip_pool or all_pool)
                if str(c.get("id", "")).lower().startswith("hip_")
                or ("hiperboria" in str(c.get("set", "")).lower())
                or ("hiperborea" in str(c.get("set", "")).lower())
            ] or (hip_pool or all_pool)
            return (
                source,
                [c for c in source if c.get("rarity") == "legendary"] or legendary_pool,
                [c for c in source if c.get("rarity") == "rare"] or rare_pool,
                [c for c in source if c.get("rarity") == "uncommon"] or uncommon_pool,
                [c for c in source if c.get("rarity") in {"basic", "common"}] or common_pool,
            )

        use_hip = bool(hip_pool) and self.app.rng.random() < hip_chance
        source = list(hip_pool if use_hip else all_pool)
        return (
            source,
            [c for c in source if c.get("rarity") == "legendary"] or legendary_pool,
            [c for c in source if c.get("rarity") == "rare"] or rare_pool,
            [c for c in source if c.get("rarity") == "uncommon"] or uncommon_pool,
            [c for c in source if c.get("rarity") in {"basic", "common"}] or common_pool,
        )

    def _open_pack(self, idx):
        if not (0 <= idx < len(self.pack_defs)):
            return
        self.selected_pack = idx
        self.selected_card = None
        self.hover_card = None

        pack = self.pack_defs[idx]
        forced_id = self._pack_alias.get(self.forced_pack_id, self.forced_pack_id)
        if forced_id:
            mapped = next((x for x in self.pack_defs if str(x.get("id", "")).lower() == forced_id), None)
            if isinstance(mapped, dict):
                pack = mapped
                self.selected_pack = next((i for i, x in enumerate(self.pack_defs) if x is mapped), idx)
            self.forced_pack_id = ""

        if hasattr(getattr(self.app, "meta_director", None), "remember"):
            self.app.meta_director.remember(self.app.run_state, "recent_pack_ids", str(pack.get("id", "base_pack")), cap=4)

        pool, leg_pool, rare_pool, uncommon_pool, common_pool = self._card_pool_by_pack(pack["id"])
        self.legendary_pick_mode = False

        picked = [
            self.app.rng.choice(common_pool or pool),
            self.app.rng.choice(common_pool or pool),
            self.app.rng.choice(common_pool or pool),
            self.app.rng.choice(rare_pool or uncommon_pool or pool),
        ]
        bonus_legendary = bool(leg_pool) and self.app.rng.random() < 0.10
        if bonus_legendary:
            picked.append(self.app.rng.choice(leg_pool))
            self.msg = f"{pack['title']} abierto. 3 comunes + 1 rara + bonus legendaria"
        else:
            self.msg = f"{pack['title']} abierto. 3 comunes + 1 rara"

        self.cards = [CardInstance(CardDef.from_dict(c)) for c in picked if c]

    def _toggle_pack_selection(self, idx):
        if self.selected_pack == idx:
            self.selected_pack = None
        else:
            self.selected_pack = idx

    def _confirm_enabled(self):
        if not self.cards:
            return self.selected_pack is not None
        return self.selected_card is not None if self.legendary_pick_mode else True

    def _confirm(self):
        if not self.cards:
            if self.selected_pack is not None:
                self._open_pack(self.selected_pack)
            return

        run_state = self.app.run_state if isinstance(getattr(self.app, "run_state", None), dict) else {}
        sideboard = run_state.get("sideboard") if isinstance(run_state.get("sideboard"), list) else []
        run_state["sideboard"] = sideboard
        self.app.run_state = run_state

        if self.legendary_pick_mode:
            chosen = self.selected_card or self.cards[0]
            sideboard.append(chosen.definition.id)
            if hasattr(self.app, "_queue_set_discovery") and hasattr(self.app, "_detect_card_set"):
                self.app._queue_set_discovery(self.app._detect_card_set(chosen.definition.id))
        else:
            for card in self.cards:
                sideboard.append(card.definition.id)
                if hasattr(self.app, "_queue_set_discovery") and hasattr(self.app, "_detect_card_set"):
                    self.app._queue_set_discovery(self.app._detect_card_set(card.definition.id))

        if self.source == "levelup_pending":
            self.app.consume_levelup_pending()
        else:
            self.app.goto_map()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.cards:
                self.cards = []
                self.msg = "Elige 1 de 3 sobres rituales"
            else:
                self.selected_pack = None
                self.app.goto_map()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_rect.collidepoint(pos):
                if self.cards:
                    self.cards = []
                    self.msg = "Elige 1 de 3 sobres rituales"
                else:
                    self.selected_pack = None
                    self.app.goto_map()
                return
            if self.confirm_rect.collidepoint(pos) and self._confirm_enabled():
                self._confirm()
                return

            if not self.cards:
                for i, rect in enumerate(self.packs):
                    if rect.collidepoint(pos):
                        self._toggle_pack_selection(i)
                        self.app.sfx.play("ui_click")
                        return
            else:
                for i, card in enumerate(self.cards):
                    if self._grid_rect(i).collidepoint(pos):
                        self.selected_card = card
                        self.app.sfx.play("card_pick")
                        return

    def _grid_rect(self, i):
        return pygame.Rect(86 + i * 214, 582, 196, 270)

    def update(self, dt):
        _ = dt

    def _render_pack_preview(self, s):
        rect = pygame.Rect(1290, 168, 560, 720)
        pygame.draw.rect(s, UI_THEME["panel_2"], rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Lectura del sobre", True, UI_THEME["gold"]), (rect.x + 14, rect.y + 12))

        if self.selected_pack is None:
            s.blit(self.app.tiny_font.render("Selecciona una portada para abrir el pack.", True, UI_THEME["muted"]), (rect.x + 14, rect.y + 48))
            s.blit(self.app.tiny_font.render("Origen: consistencia | Hiperborea: identidad | Velo: sorpresa.", True, UI_THEME["muted"]), (rect.x + 14, rect.y + 72))
            if self.source == "reward":
                s.blit(self.app.tiny_font.render("Recompensa ritual: elige tu sobre antes de abrirlo.", True, UI_THEME["gold"]), (rect.x + 14, rect.y + 102))
            return

        pdef = self.pack_defs[self.selected_pack]
        color = pdef["color"]
        y = rect.y + 48
        s.blit(self.app.big_font.render(pdef["title"], True, color), (rect.x + 14, y))
        y += 44
        s.blit(self.app.small_font.render(pdef["subtitle"], True, UI_THEME["text"]), (rect.x + 14, y))
        y += 32
        s.blit(self.app.tiny_font.render(pdef["desc"], True, UI_THEME["muted"]), (rect.x + 14, y))
        y += 24
        s.blit(self.app.tiny_font.render(pdef["flavor"], True, UI_THEME["text"]), (rect.x + 14, y))
        y += 30
        pack_meta = PACK_ECONOMY.get(pdef["id"], {})
        ev = pack_meta.get("expected_value", {}) if isinstance(pack_meta, dict) else {}
        ev_text = f"EV: {ev.get('cards_total', 3)} cartas | foco {ev.get('rarity_focus', 'mixto')}"
        s.blit(self.app.tiny_font.render(ev_text, True, UI_THEME["text"]), (rect.x + 14, y))
        y += 24
        rule = "Regla: 3 comunes + 1 rara."
        if self.cards and len(self.cards) >= 5:
            rule = "Regla activa: bonus legendaria (10%)."
        s.blit(self.app.tiny_font.render(rule, True, UI_THEME["gold"]), (rect.x + 14, y))

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Sobres rituales", True, UI_THEME["gold"]), (748, 42))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (460, 102))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card = None

        for i, rect in enumerate(self.packs):
            pdef = self.pack_defs[i]
            hovered = rect.collidepoint(mouse)
            selected = self.selected_pack == i
            draw_pack_cover(s, rect, self.app, pdef["id"], pdef["title"], selected=selected, hovered=hovered)

        if self.cards:
            for i, card in enumerate(self.cards):
                rect = self._grid_rect(i)
                hover = rect.collidepoint(mouse)
                sel = self.selected_card is card
                if hover:
                    self.hover_card = card
                render_card_small(
                    s,
                    rect,
                    card,
                    theme=UI_THEME,
                    state={
                        "app": self.app,
                        "ctx": None,
                        "selected": sel,
                        "hovered": hover,
                        "render_context": "pack_view",
                    },
                )

        self._render_pack_preview(s)
        self.preview.render(s, pygame.Rect(1290, 780, 560, 150), self.selected_card or self.hover_card, app=self.app)

        enabled = self._confirm_enabled()
        pygame.draw.rect(s, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        label = "Abrir sobre" if not self.cards and self.selected_pack is not None else ("Selecciona un sobre" if not self.cards else "Tomar lote")
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.confirm_rect.x + 48, self.confirm_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.back_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.back_rect, 2, border_radius=10)
        back_lbl = "Cancelar" if self.cards else "Volver"
        s.blit(self.app.font.render(back_lbl, True, UI_THEME["text"]), (self.back_rect.x + 72, self.back_rect.y + 16))

