from __future__ import annotations

import math
import random

import pygame

from game.ui.system.layout import safe_area
from game.ui.system.typography import TITLE_FONT


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

    def on_enter(self):
        self.t = 0.0
        self.particles = [
            {
                "x": random.uniform(0, 1920),
                "y": random.uniform(0, 1080),
                "vx": random.uniform(-2.6, 2.6),
                "vy": random.uniform(4.8, 10.2),
                "r": random.randint(1, 2),
            }
            for _ in range(34)
        ]
        try:
            if hasattr(self.app, "sfx"):
                self.app.sfx.play("studio_intro")
        except Exception:
            pass

    def handle_event(self, event):
        _ = event
        return

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
        area = safe_area(w, h, 20, 20)

        for y in range(h):
            p = y / max(1, h - 1)
            c = (int(2 + 5 * p), int(3 + 6 * p), int(10 + 12 * p))
            pygame.draw.line(surface, c, (0, y), (w, y))

        t = pygame.time.get_ticks() / 1000.0
        halo = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(4):
            r = int(260 + i * 80 + 14 * (0.5 + 0.5 * math.sin(t + i)))
            col = (84, 72, 146, max(10, 34 - i * 7))
            pygame.draw.circle(halo, col, (area.centerx, area.centery), r, 2)
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
            pygame.draw.circle(surface, (142, 142, 192), (int(p["x"]), int(p["y"])), int(p["r"]))

        base_size = max(72, int(self.app.big_font.get_height() * 2.0))
        title_font = self.app.typography.get(TITLE_FONT, base_size)
        alpha = max(0, min(255, self._title_alpha()))
        label = title_font.render("CHAKANA STUDIO", True, (245, 245, 252))
        title = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        title.blit(label, (0, 0))
        title.set_alpha(alpha)
        surface.blit(title, title.get_rect(center=(area.centerx, area.centery)))
