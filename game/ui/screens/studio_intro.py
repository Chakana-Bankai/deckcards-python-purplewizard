from __future__ import annotations

import random

import pygame

from game.ui.theme import UI_THEME


class StudioIntroScreen:
    def __init__(self, app, next_fn, duration: float = 2.5):
        self.app = app
        self.next_fn = next_fn
        self.duration = float(duration)
        self.t = 0.0
        self.particles = []

    def on_enter(self):
        self.t = 0.0
        self.particles = [
            {"x": random.randint(0, 1919), "y": random.randint(0, 1079), "vx": random.uniform(-6, 6), "vy": random.uniform(10, 22)}
            for _ in range(30)
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = self.duration + 0.01

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.next_fn()

    def render(self, surface):
        w, h = surface.get_size()
        for y in range(h):
            p = y / max(1, h - 1)
            c = (int(8 + 18 * p), int(8 + 12 * p), int(20 + 30 * p))
            pygame.draw.line(surface, c, (0, y), (w, y))

        for p in self.particles:
            p["x"] += p["vx"] * 0.016
            p["y"] += p["vy"] * 0.016
            if p["y"] > h + 8:
                p["y"] = -8
            if p["x"] < -8:
                p["x"] = w + 8
            if p["x"] > w + 8:
                p["x"] = -8
            pygame.draw.circle(surface, (120, 114, 180), (int(p["x"]), int(p["y"])), 2)

        alpha = min(255, max(0, int((self.t / max(0.2, self.duration * 0.55)) * 255)))
        label = self.app.big_font.render("CHAKANA STUDIO", True, UI_THEME["gold"])
        title = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        title.blit(label, (0, 0))
        title.set_alpha(alpha)
        surface.blit(title, title.get_rect(center=(w // 2, h // 2)))
