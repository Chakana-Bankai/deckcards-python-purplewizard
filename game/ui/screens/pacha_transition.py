import pygame

from game.art.gen_avatar_chakana import render_avatar
from game.ui.theme import UI_THEME


class PachaTransitionScreen:
    def __init__(self, app, title, next_fn, lore_line="Era una vez… la Trama susurró un cambio.", hint="Pulsa cualquier tecla", min_seconds=0.9, auto_seconds=6.0):
        self.app = app
        self.title = str(title or "Transición")
        self.next_fn = next_fn
        self.lore_line = str(lore_line)
        self.hint = str(hint)
        self.min_seconds = float(min_seconds)
        self.auto_seconds = float(auto_seconds)
        self.t = 0.0
        self.ready = False

    def on_enter(self):
        self.t = 0.0
        self.ready = False

    def _go_next(self):
        if self.ready:
            self.next_fn()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.ready = self.t >= self.min_seconds
            self._go_next()

    def update(self, dt):
        self.t += dt
        self.ready = self.t >= self.min_seconds
        if self.t >= self.auto_seconds:
            self.next_fn()

    def render(self, s):
        s.fill((10, 8, 18))
        w, h = s.get_size()
        panel = pygame.Rect(w // 2 - 520, h // 2 - 220, 1040, 440)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=18)
        pygame.draw.rect(s, UI_THEME["accent_violet"], panel, 2, border_radius=18)

        cx, cy = panel.x + 120, panel.y + 130
        pygame.draw.circle(s, UI_THEME["gold"], (cx, cy), 58, 2)
        pygame.draw.line(s, UI_THEME["gold"], (cx - 58, cy), (cx + 58, cy), 2)
        pygame.draw.line(s, UI_THEME["gold"], (cx, cy - 58), (cx, cy + 58), 2)
        pygame.draw.rect(s, UI_THEME["gold"], pygame.Rect(cx - 14, cy - 14, 28, 28), 2)
        avatar = render_avatar(pygame.time.get_ticks() / 1000.0, 110)
        s.blit(avatar, (panel.x + 70, panel.y + 210))

        s.blit(self.app.big_font.render(self.title, True, UI_THEME["gold"]), (panel.x + 240, panel.y + 70))
        s.blit(self.app.font.render(f"Era una vez… {self.lore_line}", True, UI_THEME["text"]), (panel.x + 240, panel.y + 156))
        s.blit(self.app.small_font.render(self.hint, True, UI_THEME["muted"]), (panel.x + 240, panel.y + 202))
        s.blit(self.app.small_font.render("Pulsa cualquier tecla", True, UI_THEME["good"] if self.ready else UI_THEME["muted"]), (panel.x + 240, panel.y + 312))
