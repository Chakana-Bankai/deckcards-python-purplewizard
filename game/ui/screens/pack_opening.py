import pygame

from game.combat.card import CardDef, CardInstance
from game.ui.components.card_detail_panel import CardDetailPanel
from game.ui.theme import UI_THEME

RARITY_ES = {"common": "Común", "uncommon": "Rara", "rare": "Épica", "legendary": "Legendaria", "basic": "Común"}


class PackOpeningScreen:
    def __init__(self, app):
        self.app = app
        self.msg = "Elige un sobre premium"
        self.packs = [pygame.Rect(120 + i * 560, 180, 520, 380) for i in range(3)]
        self.selected_pack = None
        self.cards = []
        self.selected_card = None
        self.confirm_rect = pygame.Rect(840, 980, 260, 64)
        self.detail_panel = CardDetailPanel(app)
        pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary", "uncommon", "common"}] or self.app.cards_data
        self.pool = pool

    def _open_pack(self, idx):
        self.selected_pack = idx
        picked = []
        leg_pool = [c for c in self.pool if c.get("rarity") == "legendary"]
        rare_pool = [c for c in self.pool if c.get("rarity") == "rare"]
        uncommon_pool = [c for c in self.pool if c.get("rarity") == "uncommon"]
        common_pool = [c for c in self.pool if c.get("rarity") in {"common", "basic"}]
        picked.append(self.app.rng.choice(leg_pool or rare_pool or self.pool))
        picked.append(self.app.rng.choice(rare_pool or uncommon_pool or self.pool))
        picked.append(self.app.rng.choice(uncommon_pool or common_pool or self.pool))
        picked.append(self.app.rng.choice(common_pool or self.pool))
        picked.append(self.app.rng.choice(self.pool))
        self.cards = [CardInstance(CardDef(**c)) for c in picked if c]
        self.msg = f"Sobre {idx+1} abierto. Selecciona 1 carta"

    def _grid_rect(self, i):
        col = i % 3
        row = i // 3
        return pygame.Rect(140 + col * 360, 620 + row * 170, 330, 150)

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
                if self.confirm_rect.collidepoint(pos) and self.selected_card is not None:
                    self.app.run_state["sideboard"].append(self.selected_card.definition.id)
                    self.app.consume_levelup_pending()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Botín / Sobres", True, UI_THEME["gold"]), (760, 42))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (640, 100))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())

        for i, r in enumerate(self.packs):
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=16)
            s.blit(self.app.big_font.render(f"SOBRE {i+1}", True, UI_THEME["text"]), (r.x + 140, r.y + 46))
            s.blit(self.app.small_font.render("5 opciones premium", True, UI_THEME["muted"]), (r.x + 150, r.y + 120))

        if self.cards:
            for i, card in enumerate(self.cards):
                r = self._grid_rect(i)
                hover = r.collidepoint(mouse)
                sel = self.selected_card is card
                col = (50, 36, 70) if hover else UI_THEME["panel"]
                pygame.draw.rect(s, col, r, border_radius=10)
                pygame.draw.rect(s, UI_THEME["gold"] if sel else UI_THEME["accent_violet"], r, 3 if sel else 1, border_radius=10)
                s.blit(self.app.small_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 10, r.y + 12))
                rarity_es = RARITY_ES.get(card.definition.rarity, card.definition.rarity.title())
                s.blit(self.app.tiny_font.render(rarity_es, True, UI_THEME["gold"]), (r.x + 10, r.y + 42))

        detail_rect = pygame.Rect(1240, 620, 620, 320)
        self.detail_panel.render(s, detail_rect, self.selected_card)

        enabled = self.selected_card is not None
        pygame.draw.rect(s, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        s.blit(self.app.font.render("Confirmar" if self.cards else "Elegir sobre", True, UI_THEME["text"]), (self.confirm_rect.x + 44, self.confirm_rect.y + 18))
