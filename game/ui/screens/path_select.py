import pygame

from game.ui.theme import UI_THEME


class PathSelectScreen:
    def __init__(self, app):
        self.app = app
        self.options = [
            ("Ataque", ["strike"] * 6 + ["defend"] * 4 + ["arcane_pulse", "violet_bolt"]),
            ("Magia", ["strike"] * 4 + ["defend"] * 4 + ["lesser_seal", "arcane_pulse", "void_limit", "cauterize_rupture"]),
            ("Defensa", ["strike"] * 4 + ["defend"] * 6 + ["prismatic_shield", "phase_shift"]),
        ]

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_menu()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, (name, deck) in enumerate(self.options):
                r = pygame.Rect(100 + i * 390, 160, 320, 500)
                if r.collidepoint(pos):
                    self.app.start_run_with_deck(deck)
                    return

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Elige tu Sendero", True, UI_THEME["text"]), (430, 70))
        for i, (name, deck) in enumerate(self.options):
            r = pygame.Rect(100 + i * 390, 160, 320, 500)
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=10)
            s.blit(self.app.font.render(name, True, UI_THEME["gold"]), (r.x + 110, r.y + 18))
            for j, cid in enumerate(deck[:12]):
                cd = self.app.card_defs.get(cid, self.app.card_defs.get("strike"))
                s.blit(self.app.tiny_font.render(self.app.loc.t(cd.get("name_key", cid)), True, UI_THEME["text"]), (r.x + 14, r.y + 58 + j * 34))
