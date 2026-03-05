import pygame

from game.combat.card import CardDef, CardInstance
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.theme import UI_THEME

RARITY_ES = {"common": "Común", "uncommon": "Rara", "rare": "Épica", "legendary": "Legendaria", "basic": "Común"}


class PackOpeningScreen:
    def __init__(self, app):
        self.app = app
        self.msg = "Elige un sobre premium"
        self.packs = [pygame.Rect(90 + i * 600, 150, 560, 300) for i in range(3)]
        self.selected_pack = None
        self.cards = []
        self.selected_card = None
        self.hover_card = None
        self.confirm_rect = pygame.Rect(740, 954, 420, 60)
        self.detail_panel = CardPreviewPanel(app)
        self.legendary_pick_mode = False
        pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary", "uncommon", "common", "basic"}] or self.app.cards_data
        self.pool = pool

    def _open_pack(self, idx):
        self.selected_pack = idx
        self.selected_card = None
        self.hover_card = None
        self.legendary_pick_mode = bool(self.app.user_settings.get("pack_legendary_pick_enabled", True)) and self.app.rng.random() < 0.18

        if self.legendary_pick_mode:
            leg_pool = [c for c in self.pool if c.get("rarity") == "legendary"]
            base = leg_pool or [c for c in self.pool if c.get("rarity") == "rare"] or self.pool
            picked = [self.app.rng.choice(base) for _ in range(5)]
            self.msg = f"Sobre {idx+1}: evento raro — Elige 1 legendaria"
        else:
            leg_pool = [c for c in self.pool if c.get("rarity") == "legendary"]
            rare_pool = [c for c in self.pool if c.get("rarity") == "rare"]
            uncommon_pool = [c for c in self.pool if c.get("rarity") == "uncommon"]
            common_pool = [c for c in self.pool if c.get("rarity") in {"common", "basic"}]
            picked = [
                self.app.rng.choice(leg_pool or rare_pool or self.pool),
                self.app.rng.choice(rare_pool or uncommon_pool or self.pool),
                self.app.rng.choice(uncommon_pool or common_pool or self.pool),
                self.app.rng.choice(common_pool or self.pool),
                self.app.rng.choice(self.pool),
            ]
            self.msg = f"Sobre {idx+1} abierto. Recibirás las 5 cartas"
        self.cards = [CardInstance(CardDef(**c)) for c in picked if c]

    def _grid_rect(self, i):
        return pygame.Rect(96 + i * 236, 520, 220, 300)

    def _confirm_enabled(self):
        if not self.cards:
            return False
        return self.selected_card is not None if self.legendary_pick_mode else True

    def _confirm(self):
        if not self.cards:
            return
        if self.legendary_pick_mode:
            chosen = self.selected_card or self.cards[0]
            self.app.run_state["sideboard"].append(chosen.definition.id)
        else:
            for c in self.cards:
                self.app.run_state["sideboard"].append(c.definition.id)
        self.app.consume_levelup_pending()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if not self.cards:
                for i, r in enumerate(self.packs):
                    if r.collidepoint(pos):
                        self._open_pack(i)
                        self.app.sfx.play("ui_click")
                        return
            else:
                for i, c in enumerate(self.cards):
                    if self._grid_rect(i).collidepoint(pos):
                        self.selected_card = c
                        self.app.sfx.play("card_pick")
                        return
                if self.confirm_rect.collidepoint(pos) and self._confirm_enabled():
                    self._confirm()

    def update(self, dt):
        _ = dt

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Botín / Sobres", True, UI_THEME["gold"]), (760, 42))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (560, 102))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card = None

        for i, r in enumerate(self.packs):
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=16)
            s.blit(self.app.big_font.render(f"SOBRE {i+1}", True, UI_THEME["text"]), (r.x + 170, r.y + 54))
            s.blit(self.app.small_font.render("5 cartas chakánicas", True, UI_THEME["muted"]), (r.x + 165, r.y + 128))

        if self.cards:
            for i, card in enumerate(self.cards):
                r = self._grid_rect(i)
                hover = r.collidepoint(mouse)
                sel = self.selected_card is card
                if hover:
                    self.hover_card = card
                col = (50, 36, 70) if hover else UI_THEME["panel"]
                pygame.draw.rect(s, col, r, border_radius=10)
                pygame.draw.rect(s, UI_THEME["gold"] if sel or hover else UI_THEME["accent_violet"], r, 3 if sel or hover else 1, border_radius=10)
                art = self.app.assets.sprite("cards", card.definition.id, (r.w - 20, 170), fallback=(82, 52, 112))
                s.blit(art, (r.x + 10, r.y + 8))
                s.blit(self.app.tiny_font.render(self.app.loc.t(card.definition.name_key)[:20], True, UI_THEME["text"]), (r.x + 8, r.y + 190))
                rarity_es = RARITY_ES.get(card.definition.rarity, card.definition.rarity.title())
                s.blit(self.app.tiny_font.render(rarity_es, True, UI_THEME["gold"]), (r.x + 8, r.y + 214))

        detail_rect = pygame.Rect(1288, 164, 580, 760)
        preview_card = self.selected_card or self.hover_card
        self.detail_panel.render(s, detail_rect, preview_card)

        enabled = self._confirm_enabled()
        pygame.draw.rect(s, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.confirm_rect, 2, border_radius=10)
        label = "Confirmar legendaria" if self.legendary_pick_mode else "Confirmar: añadir 5 cartas"
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.confirm_rect.x + 48, self.confirm_rect.y + 18))
