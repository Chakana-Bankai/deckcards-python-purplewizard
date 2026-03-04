from __future__ import annotations

import math
import random

import pygame

from game.art.gen_art32 import chakana_points


class LoadingScreen:
    def __init__(self, title_font, body_font):
        self.title_font = title_font
        self.body_font = body_font
        self.label = "Iniciando..."
        self.pct = 0.0
        self.particles = [{"x": random.randint(0, 1919), "y": random.randint(0, 1079), "vx": random.uniform(-10, 10), "vy": random.uniform(8, 20)} for _ in range(18)]

    def set_step(self, label: str, pct: float):
        self.label = label
        self.pct = max(0.0, min(1.0, float(pct)))

    def draw(self, screen: pygame.Surface, dt: float = 0.016):
        for y in range(1080):
            t = y / 1080.0
            c = (int(14 + 20 * t), int(10 + 16 * t), int(28 + 26 * t))
            pygame.draw.line(screen, c, (0, y), (1920, y))

        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] > 1090:
                p["y"] = -10
            if p["x"] < -10:
                p["x"] = 1930
            if p["x"] > 1930:
                p["x"] = -10
            pygame.draw.circle(screen, (130, 120, 190), (int(p["x"]), int(p["y"])), 2)

        tt = pygame.time.get_ticks() / 1000.0
        pulse = 1.0 + 0.06 * math.sin(tt * 2.4)
        pts = chakana_points((960, 360), int(96 * pulse), step=0.35)
        pygame.draw.polygon(screen, (214, 186, 252), pts, 4)
        pygame.draw.circle(screen, (110, 92, 180), (960, 360), int(142 * pulse), 1)

        title = self.title_font.render("CHAKANA PURPLE WIZARD", True, (236, 221, 158))
        screen.blit(title, title.get_rect(center=(960, 160)))

        bar = pygame.Rect(360, 860, 1200, 30)
        pygame.draw.rect(screen, (48, 42, 76), bar, border_radius=12)
        pygame.draw.rect(screen, (182, 146, 244), (bar.x, bar.y, int(bar.w * self.pct), bar.h), border_radius=12)
        pygame.draw.rect(screen, (230, 220, 255), bar, 2, border_radius=12)

        msg = self.body_font.render(self.label, True, (236, 236, 246))
        screen.blit(msg, msg.get_rect(center=(960, 826)))

        avatar_pts = chakana_points((960, 560), int(56 * pulse), step=0.35)
        pygame.draw.polygon(screen, (194, 152, 244), avatar_pts, 3)
