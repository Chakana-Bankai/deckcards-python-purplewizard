import pygame

from game.combat.card import CardDef, CardInstance
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_renderer import render_card_small
from game.ui.theme import UI_THEME
from game.systems.reward_system import PACK_ECONOMY


class PackOpeningScreen:
    def __init__(self, app):
        self.app = app
        self.msg = "Elige un sobre premium"
        self.packs = [pygame.Rect(80 + i * 390, 160, 360, 280) for i in range(3)]
        self.pack_defs = [
            {
                "id": "normal_pack",
                "title": "Pack Normal",
                "subtitle": "Base estable",
                "desc": "5 cartas de consistencia para escalar.",
                "flavor": "Ruta segura para estabilizar la Trama.",
                "color": (140, 128, 186),
            },
            {
                "id": "rare_choice_pack",
                "title": "Pack Raro",
                "subtitle": "Alto impacto",
                "desc": "Rarezas y control de ritmo.",
                "flavor": "Mayor riesgo, mayor impacto tactico.",
                "color": (116, 188, 228),
            },
            {
                "id": "ritual_reward_pack",
                "title": "Pack Ritual",
                "subtitle": "Armonia",
                "desc": "Sinergias de rito y lectura astral.",
                "flavor": "Afinado para sellos y preparacion.",
                "color": (196, 138, 238),
            },
        ]
        self.selected_pack = None
        self.cards = []
        self.selected_card = None
        self.hover_card = None
        self.confirm_rect = pygame.Rect(760, 980, 320, 56)
        self.back_rect = pygame.Rect(420, 980, 280, 56)
        self.preview = CardPreviewPanel(app=app)
        self.legendary_pick_mode = False
        source_cards = list(getattr(self.app, '_reward_card_pool', lambda: list(getattr(self.app, 'cards_data', []) or []))() or [])
        pool_all = [c for c in source_cards if c.get("rarity") in {"rare", "legendary", "uncommon", "common", "basic"}] or source_cards
        self.base_pool = [c for c in pool_all if not (str(c.get("id", "")).lower().startswith("hip_") or "hiperboria" in str(c.get("set", "")).lower())] or list(pool_all)
        self.hip_pool = [c for c in pool_all if c not in self.base_pool]
        self.pool = list(pool_all)
        self.reveal_mode = "fan"

    def _card_pool_by_pack(self, pack_id: str):
        run = self.app.run_state if isinstance(self.app.run_state, dict) else {}
        level = int(run.get("level", 1) or 1)
        hip_unlocked = bool(getattr(self.app, 'is_set_unlocked', lambda _sid: False)('hiperboria'))
        hip_chance = 0.0 if (not hip_unlocked) else (0.25 if level < 5 else 0.45)
        use_hip = bool(self.hip_pool) and self.app.rng.random() < hip_chance
        pool = list(self.hip_pool if use_hip else self.base_pool)
        if not pool:
            pool = list(self.pool)
        common_pool = [c for c in pool if c.get("rarity") in {"basic", "common"}] or pool
        uncommon_pool = [c for c in pool if c.get("rarity") == "uncommon"] or common_pool
        rare_pool = [c for c in pool if c.get("rarity") == "rare"] or uncommon_pool
        legendary_pool = [c for c in pool if c.get("rarity") == "legendary"] or rare_pool
        ritual_pool = [
            c for c in pool if any(tag in {"ritual", "harmony", "scry", "draw", "control"} for tag in (c.get("tags") or []))
        ] or uncommon_pool

        if pack_id == "rare_choice_pack":
            return rare_pool + uncommon_pool + common_pool, legendary_pool, rare_pool, uncommon_pool, common_pool
        if pack_id == "ritual_reward_pack":
            return ritual_pool + uncommon_pool + common_pool, legendary_pool, rare_pool, uncommon_pool, common_pool
        return common_pool + uncommon_pool + rare_pool, legendary_pool, rare_pool, uncommon_pool, common_pool

    def _open_pack(self, idx):
        if not (0 <= idx < len(self.pack_defs)):
            return
        self.selected_pack = idx
        self.selected_card = None
        self.hover_card = None
        pack = self.pack_defs[idx]
        pool, leg_pool, rare_pool, uncommon_pool, common_pool = self._card_pool_by_pack(pack["id"])

        self.legendary_pick_mode = bool(self.app.user_settings.get("pack_legendary_pick_enabled", True)) and self.app.rng.random() < 0.18

        if self.legendary_pick_mode:
            base = leg_pool or rare_pool or pool
            picked = [self.app.rng.choice(base) for _ in range(5)]
            self.msg = f"{pack['title']}: evento raro - Elige 1 legendaria"
        else:
            picked = [
                self.app.rng.choice(leg_pool or rare_pool or pool),
                self.app.rng.choice(rare_pool or uncommon_pool or pool),
                self.app.rng.choice(uncommon_pool or common_pool or pool),
                self.app.rng.choice(common_pool or pool),
                self.app.rng.choice(pool),
            ]
            self.msg = f"{pack['title']} abierto. Recibiras las 5 cartas"
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
        if self.legendary_pick_mode:
            chosen = self.selected_card or self.cards[0]
            self.app.run_state["sideboard"].append(chosen.definition.id)
            if hasattr(self.app, '_queue_set_discovery') and hasattr(self.app, '_detect_card_set'):
                self.app._queue_set_discovery(self.app._detect_card_set(chosen.definition.id))
        else:
            for c in self.cards:
                self.app.run_state["sideboard"].append(c.definition.id)
                if hasattr(self.app, '_queue_set_discovery') and hasattr(self.app, '_detect_card_set'):
                    self.app._queue_set_discovery(self.app._detect_card_set(c.definition.id))
        self.app.consume_levelup_pending()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.cards:
                self.cards = []
                self.msg = "Elige un sobre premium"
            else:
                self.selected_pack = None
                self.app.goto_map()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back_rect.collidepoint(pos):
                if self.cards:
                    self.cards = []
                    self.msg = "Elige un sobre premium"
                else:
                    self.selected_pack = None
                    self.app.goto_map()
                return
            if self.confirm_rect.collidepoint(pos) and self._confirm_enabled():
                self._confirm()
                return

            if not self.cards:
                for i, r in enumerate(self.packs):
                    if r.collidepoint(pos):
                        self._toggle_pack_selection(i)
                        self.app.sfx.play("ui_click")
                        return
            else:
                for i, c in enumerate(self.cards):
                    if self._grid_rect(i).collidepoint(pos):
                        self.selected_card = c
                        self.app.sfx.play("card_pick")
                        return

    def _grid_rect(self, i):
        return pygame.Rect(78 + i * 236, 520, 220, 300)

    def update(self, dt):
        _ = dt

    def _render_pack_preview(self, s):
        rect = pygame.Rect(1288, 160, 580, 340)
        pygame.draw.rect(s, UI_THEME["panel_2"], rect, border_radius=14)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=14)
        s.blit(self.app.small_font.render("Preview de sobre", True, UI_THEME["gold"]), (rect.x + 14, rect.y + 12))

        if self.selected_pack is None:
            s.blit(self.app.tiny_font.render("Selecciona un pack para ver identidad.", True, UI_THEME["muted"]), (rect.x + 14, rect.y + 48))
            s.blit(self.app.tiny_font.render("Normal: base | Raro: impacto | Ritual: sinergia.", True, UI_THEME["muted"]), (rect.x + 14, rect.y + 72))
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

        rule = "Regla: al abrir recibes 5 cartas."
        if self.legendary_pick_mode:
            rule = "Regla activa: evento raro, eliges 1 legendaria."
        s.blit(self.app.tiny_font.render(rule, True, UI_THEME["gold"]), (rect.x + 14, y))

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Botin / Sobres", True, UI_THEME["gold"]), (760, 42))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (520, 102))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card = None

        for i, r in enumerate(self.packs):
            pdef = self.pack_defs[i]
            hovered = r.collidepoint(mouse)
            selected = self.selected_pack == i
            col = UI_THEME["panel_2"] if (hovered or selected) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=16)
            border_col = pdef["color"] if selected else UI_THEME["gold"]
            bw = 4 if selected else 2
            pygame.draw.rect(s, border_col, r, bw, border_radius=16)
            if selected:
                glow = pygame.Surface((r.w + 18, r.h + 18), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*pdef["color"], 66), glow.get_rect(), border_radius=20)
                s.blit(glow, (r.x - 9, r.y - 9))

            s.blit(self.app.big_font.render(pdef["title"], True, UI_THEME["text"]), (r.x + 48, r.y + 42))
            s.blit(self.app.small_font.render(pdef["subtitle"], True, pdef["color"]), (r.x + 48, r.y + 96))
            s.blit(self.app.tiny_font.render(pdef["desc"], True, UI_THEME["muted"]), (r.x + 48, r.y + 132))
            s.blit(self.app.tiny_font.render(pdef["flavor"], True, UI_THEME["text"]), (r.x + 48, r.y + 156))
            if selected:
                s.blit(self.app.tiny_font.render("Seleccionado", True, UI_THEME["gold"]), (r.x + 48, r.y + 248))

        if self.cards:
            for i, card in enumerate(self.cards):
                r = self._grid_rect(i)
                hover = r.collidepoint(mouse)
                sel = self.selected_card is card
                if hover:
                    self.hover_card = card
                render_card_small(
                    s,
                    r,
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
        self.preview.render(s, pygame.Rect(1288, 510, 580, 430), self.selected_card or self.hover_card, app=self.app)

        enabled = self._confirm_enabled()
        pygame.draw.rect(s, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        if not self.cards:
            label = "Abrir sobre" if self.selected_pack is not None else "Selecciona un sobre"
        else:
            label = "Confirmar legendaria" if self.legendary_pick_mode else "Tomar pack"
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.confirm_rect.x + 72, self.confirm_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.back_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.back_rect, 2, border_radius=10)
        back_lbl = "Cancelar" if self.cards else "Volver"
        s.blit(self.app.font.render(back_lbl, True, UI_THEME["text"]), (self.back_rect.x + 88, self.back_rect.y + 16))
