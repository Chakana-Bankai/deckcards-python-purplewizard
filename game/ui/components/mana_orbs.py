from __future__ import annotations

import math
import pygame


class ManaOrbsWidget:
    def __init__(self):
        self.prev_mana = None
        self.pulse_t = 0.0

    def update(self, mana: int):
        if self.prev_mana is None:
            self.prev_mana = mana
        if mana != self.prev_mana:
            self.pulse_t = 0.35
            self.prev_mana = mana

    def tick(self, dt: float):
        self.pulse_t = max(0.0, self.pulse_t - dt)

    def draw(self, s: pygame.Surface, x: int, y: int, mana: int, max_mana: int = 6):
        pulse = 1.0 + (0.12 * math.sin(pygame.time.get_ticks() / 70.0) if self.pulse_t > 0 else 0.0)
        for i in range(max_mana):
            col = (246, 210, 122) if i < mana else (76, 74, 98)
            r = int(10 * pulse) if i < mana else 10
            pygame.draw.circle(s, col, (x + i * 30, y), r)
            pygame.draw.circle(s, (22, 18, 32), (x + i * 30, y), r, 2)
