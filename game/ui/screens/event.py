import pygame

from game.settings import COLORS


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            for i, ch in enumerate(self.event["choices"]):
                if pygame.Rect(180, 360 + i * 86, 920, 64).collidepoint(pos):
                    self.app.apply_event_effects(ch["effects"])
                    self.app._complete_current_node()
                    self.app.goto_map()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(COLORS["bg"])
        s.blit(self.app.big_font.render(self.app.loc.t(self.event["title_key"]), True, COLORS["text"]), (120, 80))
        s.blit(self.app.font.render(self.app.loc.t(self.event["body_key"]), True, COLORS["muted"]), (120, 150))
        for i, ch in enumerate(self.event["choices"]):
            r = pygame.Rect(180, 360 + i * 86, 920, 64)
            pygame.draw.rect(s, COLORS["panel"], r, border_radius=8)
            s.blit(self.app.font.render(self.app.loc.t(ch["text_key"]), True, COLORS["text"]), (200, r.y + 20))
