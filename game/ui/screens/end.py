import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EndScreen:
    def __init__(self, app, victory=True):
        self.app = app
        self.victory = victory
        self.banner = TypewriterBanner()
        self.lines = app.lore_data.get("ending_lines", ["La Trama respira en paz.", "Un ciclo termina, otro nace."])
        self.idx = 0
        self.t = 0
        self.buttons = {
            "primary": pygame.Rect(760, 760, 400, 68),
            "menu": pygame.Rect(760, 842, 400, 68),
        }

    def on_enter(self):
        msg = self.lines[0] if self.victory else "Moraleja: caer también enseña el camino."
        self.banner.set(msg, 2.0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.buttons["primary"].collidepoint(pos):
                if self.victory and self.app.run_state:
                    self.app.goto_map()
                else:
                    self.app.new_run()
            elif self.buttons["menu"].collidepoint(pos):
                self.app.goto_menu()

    def update(self, dt):
        self.t += dt
        if self.victory and self.t > 3.3:
            self.t = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.banner.set(self.lines[self.idx], 2.8)

    def render(self, s):
        sky, silhouettes, fog = self.app.bg_gen.get_layers("Templo Obsidiana", 777)
        s.blit(sky, (0, 0)); s.blit(silhouettes, (0, 0)); s.blit(fog, (0, 0))
        panel = pygame.Rect(360, 170, 1200, 560)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=18)
        title = "Victoria" if self.victory else "Derrota"
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (860, 230))
        s.blit(self.app.font.render(self.banner.current, True, UI_THEME["text"]), (430, 318))
        labels = {
            "primary": "Continuar" if self.victory else "Reiniciar",
            "menu": "Volver al Menú",
        }
        for k, r in self.buttons.items():
            pygame.draw.rect(s, UI_THEME["violet"], r, border_radius=12)
            s.blit(self.app.small_font.render(labels[k], True, UI_THEME["text"]), (r.x + 130, r.y + 22))
