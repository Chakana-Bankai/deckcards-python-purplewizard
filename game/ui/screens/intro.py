import pygame

from game.ui.theme import UI_THEME


class IntroScreen:
    def __init__(self, app, next_fn=None):
        self.app = app
        self.next_fn = next_fn or self.app.goto_menu
        self.t = 0.0
        self.duration = 9.0
        self.lines = [
            "Chakana despierta donde la Trama se fractura.",
            "Cada sendero altera el equilibrio entre mundos.",
            "Solo tu voluntad puede sellar el Monolito.",
        ]
        self.idx = 0

    def on_enter(self):
        self.t = 0.0
        self.idx = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = self.duration

    def update(self, dt):
        self.t += dt
        # Narrative cadence: one short beat at a time.
        self.idx = min(len(self.lines) - 1, int(self.t // 2.8))
        if self.t >= self.duration:
            self.next_fn()

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Ruinas Chakana", 909, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        veil = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        veil.fill((10, 8, 20, 190))
        s.blit(veil, (0, 0))

        panel = pygame.Rect(300, 220, 1320, 450)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=16)

        title = self.app.big_font.render("CRONICA DE CHAKANA", True, UI_THEME["gold"])
        s.blit(title, title.get_rect(center=(panel.centerx, panel.y + 82)))

        line = self.lines[self.idx]
        body = self.app.font.render(line, True, UI_THEME["text"])
        s.blit(body, body.get_rect(center=(panel.centerx, panel.centery)))

        hint = self.app.small_font.render("Pulsa para continuar", True, UI_THEME["muted"])
        s.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 64)))
