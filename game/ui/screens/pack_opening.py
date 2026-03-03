import pygame

from game.combat.card import CardDef, CardInstance
from game.ui.theme import UI_THEME


class PackOpeningScreen:
    def __init__(self, app):
        self.app = app
        self.msg = "Elige 1 sobre premium"
        self.packs = [pygame.Rect(180 + i * 520, 180, 420, 460) for i in range(3)]
        self.revealed = None
        self.cards = []
        pool = [c for c in self.app.cards_data if c.get("rarity") in {"rare", "legendary", "uncommon"}] or self.app.cards_data
        self.pool = pool

    def _open_pack(self, idx):
        if self.revealed is not None:
            return
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
        self.msg = "Sobre abierto: +5 cartas premium"

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.revealed is None:
                for i, r in enumerate(self.packs):
                    if r.collidepoint(pos):
                        self._open_pack(i)
                        return
            elif pygame.Rect(830, 660, 260, 60).collidepoint(pos):
                self.app.consume_levelup_pending()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Sobres de Ascenso", True, UI_THEME["gold"]), (700, 52))
        s.blit(self.app.font.render(self.msg, True, UI_THEME["text"]), (720, 110))
        for i, r in enumerate(self.packs):
            shake = int(2 * pygame.math.Vector2(1, 0).rotate(pygame.time.get_ticks() * 0.2 + i * 70).x) if self.revealed is None else 0
            rr = r.move(shake, 0)
            col = UI_THEME["panel"] if self.revealed != i else UI_THEME["card_selected"]
            pygame.draw.rect(s, col, rr, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], rr, 2, border_radius=16)
            s.blit(self.app.big_font.render(f"SOBRE {i+1}", True, UI_THEME["text"]), (rr.x + 90, rr.y + 40))
            s.blit(self.app.small_font.render("1 legend + 2 raras + 2 comunes", True, UI_THEME["muted"]), (rr.x + 36, rr.y + 120))

        if self.cards:
            for i, card in enumerate(self.cards):
                r = pygame.Rect(240 + i * 290, 500, 250, 130)
                pygame.draw.rect(s, UI_THEME["panel_2"], r, border_radius=10)
                s.blit(self.app.small_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (r.x + 10, r.y + 20))
                s.blit(self.app.tiny_font.render(card.definition.rarity.upper(), True, UI_THEME["gold"]), (r.x + 10, r.y + 56))
            pygame.draw.rect(s, UI_THEME["violet"], (830, 660, 260, 60), border_radius=10)
            s.blit(self.app.font.render("Continuar", True, UI_THEME["text"]), (900, 677))
