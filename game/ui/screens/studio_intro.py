from __future__ import annotations

import math
import random

import pygame

from game.ui.theme import UI_THEME


class StudioIntroScreen:
    def __init__(self, app, next_fn, fade_in: float = 1.2, hold: float = 1.5, fade_out: float = 1.2):
        self.app = app
        self.next_fn = next_fn
        self.fade_in = float(fade_in)
        self.hold = float(hold)
        self.fade_out = float(fade_out)
        self.duration = self.fade_in + self.hold + self.fade_out
        self.t = 0.0
        self.particles = []
        base_size = max(54, int(self.app.big_font.get_height() * 1.6))
        self.title_font = pygame.font.SysFont("arial", base_size, bold=True)

    def on_enter(self):
        self.t = 0.0
        self.particles = [
            {
                "x": random.uniform(0, 1920),
                "y": random.uniform(0, 1080),
                "vx": random.uniform(-3.5, 3.5),
                "vy": random.uniform(6.0, 14.0),
                "r": random.randint(1, 2),
            }
            for _ in range(42)
        ]
        try:
            if hasattr(self.app, "sfx"):
                self.app.sfx.play("ui_click")
        except Exception:
            pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = self.duration + 0.01

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.next_fn()

    def _title_alpha(self) -> int:
        if self.t <= self.fade_in:
            return int(255 * (self.t / max(0.001, self.fade_in)))
        if self.t <= self.fade_in + self.hold:
            return 255
        out_t = self.t - self.fade_in - self.hold
        return int(255 * (1.0 - out_t / max(0.001, self.fade_out)))

    def render(self, surface):
        w, h = surface.get_size()
        for y in range(h):
            p = y / max(1, h - 1)
            c = (int(6 + 10 * p), int(8 + 10 * p), int(20 + 26 * p))
            pygame.draw.line(surface, c, (0, y), (w, y))

        t = pygame.time.get_ticks() / 1000.0
        halo = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(4):
            r = int(260 + i * 80 + 14 * (0.5 + 0.5 * math.sin(t + i)))
            col = (84, 72, 146, max(10, 34 - i * 7))
            pygame.draw.circle(halo, col, (w // 2, h // 2), r, 2)
        surface.blit(halo, (0, 0))

        for p in self.particles:
            p["x"] += p["vx"] * 0.016
            p["y"] += p["vy"] * 0.016
            if p["y"] > h + 8:
                p["y"] = -8
            if p["x"] < -8:
                p["x"] = w + 8
            if p["x"] > w + 8:
                p["x"] = -8
            pygame.draw.circle(surface, (170, 170, 214), (int(p["x"]), int(p["y"])), int(p["r"]))

        alpha = max(0, min(255, self._title_alpha()))
        label = self.title_font.render("CHAKANA STUDIO", True, (245, 245, 252))
        title = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        title.blit(label, (0, 0))
        title.set_alpha(alpha)
        surface.blit(title, title.get_rect(center=(w // 2, h // 2)))
