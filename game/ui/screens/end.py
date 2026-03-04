import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EndScreen:
    def __init__(self, app):
        self.app = app
        self.banner = TypewriterBanner()
        self.lines = app.lore_data.get("ending_lines", ["La Trama respira en paz.", "Un ciclo termina, otro nace."])
        self.idx = 0
        self.t = 0
        self.buttons = {
            "new": pygame.Rect(620, 760, 220, 68),
            "menu": pygame.Rect(860, 760, 220, 68),
            "credits": pygame.Rect(1100, 760, 220, 68),
        }

    def on_enter(self):
        self.banner.set(self.lines[0], 3.0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.buttons["new"].collidepoint(pos):
                self.app.new_run()
            elif self.buttons["menu"].collidepoint(pos):
                self.app.goto_menu()
            elif self.buttons["credits"].collidepoint(pos):
                self.app.goto_menu()

    def update(self, dt):
        self.t += dt
        if self.t > 3.3:
            self.t = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.banner.set(self.lines[self.idx], 2.8)

    def render(self, s):
        sky, silhouettes, fog = self.app.bg_gen.get_layers("Templo Obsidiana", 777)
        s.blit(sky, (0, 0))
        s.blit(silhouettes, (0, 0))
        s.blit(fog, (0, 0))
        panel = pygame.Rect(360, 170, 1200, 560)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=18)
        s.blit(self.app.big_font.render("La Trama de la Chakana", True, UI_THEME["gold"]), (650, 230))
        s.blit(self.app.font.render(self.banner.current, True, UI_THEME["text"]), (430, 318))
        run = self.app.run_state or {"gold": 0, "level": 1, "deck": [], "sideboard": []}
        stats = [
            f"Oro final: {run.get('gold', 0)}",
            f"Nivel final: {run.get('level', 1)}",
            f"Cartas adquiridas: {len(run.get('deck', [])) + len(run.get('sideboard', []))}",
        ]
        for i, line in enumerate(stats):
            s.blit(self.app.font.render(line, True, UI_THEME["muted"]), (430, 390 + i * 54))
        labels = {"new": "Nueva Trama", "menu": "Volver al Menú", "credits": "Créditos"}
        for k, r in self.buttons.items():
            pygame.draw.rect(s, UI_THEME["violet"], r, border_radius=12)
            s.blit(self.app.small_font.render(labels[k], True, UI_THEME["text"]), (r.x + 26, r.y + 22))
