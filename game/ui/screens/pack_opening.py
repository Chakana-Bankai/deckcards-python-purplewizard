import pygame

from game.combat.card import CardDef, CardInstance
from game.ui.theme import UI_THEME


class PackOpeningScreen:
    def __init__(self, app):
        self.app = app
        self.msg = "Elige 1 sobre premium"
        self.packs = [pygame.Rect(120 + i * 560, 200, 520, 560) for i in range(3)]
        self.selected_idx = None
        self.revealed = None
        self.cards = []
        self.confirm_rect = pygame.Rect(840, 860, 260, 64)
        pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary", "uncommon"}] or self.app.cards_data
        self.pool = pool

    def _open_pack(self, idx):
        self.revealed = idx
        picked = []
        leg_pool = [c for c in self.pool if c.get("rarity") == "legendary"]
        rare_pool = [c for c in self.pool if c.get("rarity") == "rare"]
        common_pool = [c for c in self.app.cards_data if c.get("rarity") in {"common", "uncommon"}]
        if leg_pool:
            picked.append(self.app.rng.choice(leg_pool))
        for _ in range(2):
            picked.append(self.app.rng.choice(rare_pool or self.pool))
        for _ in range(2):
            picked.append(self.app.rng.choice(common_pool or self.app.cards_data))
        self.cards = [CardInstance(CardDef(**c)) for c in picked if c]
        for card in self.cards:
            self.app.run_state["sideboard"].append(card.definition.id)
        self.msg = f"Elegiste SOBRE {idx+1}"
        self.app.sfx.play("card_pick")

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.revealed is None:
                for i, r in enumerate(self.packs):
                    if r.collidepoint(pos):
                        self.selected_idx = i
                        self.app.sfx.play("ui_click")
                        return
                if self.confirm_rect.collidepoint(pos) and self.selected_idx is not None:
                    self._open_pack(self.selected_idx)
            elif self.confirm_rect.collidepoint(pos):
                self.app.consume_levelup_pending()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Sobres de Ascenso", True, UI_THEME["gold"]), (700, 52))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (700, 112))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, r in enumerate(self.packs):
            col = UI_THEME["panel"] if self.revealed != i else UI_THEME["card_selected"]
            pygame.draw.rect(s, col, r, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=16)
            if self.revealed is None and r.collidepoint(mouse):
                pygame.draw.rect(s, (198, 172, 255), r.inflate(8, 8), 2, border_radius=18)
            s.blit(self.app.big_font.render(f"SOBRE {i+1}", True, UI_THEME["text"]), (r.x + 130, r.y + 40))
            s.blit(self.app.small_font.render("1 legend + 2 raras + 2 comunes", True, UI_THEME["muted"]), (r.x + 76, r.y + 120))
            if self.selected_idx == i and self.revealed is None:
                pygame.draw.rect(s, UI_THEME["gold"], r.inflate(12, 12), 4, border_radius=18)
                s.blit(self.app.small_font.render("SELECCIONADA", True, UI_THEME["gold"]), (r.x + 170, r.y - 30))

        if self.cards:
            for i, card in enumerate(self.cards):
                r = pygame.Rect(160 + i * 320, 780, 300, 64)
                pygame.draw.rect(s, UI_THEME["panel_2"], r, border_radius=10)
                s.blit(self.app.small_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 10, r.y + 8))
                s.blit(self.app.tiny_font.render(card.definition.rarity.upper(), True, UI_THEME["gold"]), (r.x + 10, r.y + 36))

        enabled = (self.selected_idx is not None and self.revealed is None) or self.revealed is not None
        pygame.draw.rect(s, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        s.blit(self.app.font.render("Confirmar" if self.revealed is None else "Continuar", True, UI_THEME["text"]), (self.confirm_rect.x + 54, self.confirm_rect.y + 18))
