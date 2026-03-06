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

    def draw(self, s: pygame.Surface, x: int, y: int, mana: int, max_mana: int = 6, buffed: bool = False):
        cap = max(1, int(max_mana))
        mana = max(0, min(int(mana), cap))
        full = mana >= cap
        base_pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150.0)
        feedback = 1.0 + (0.10 * math.sin(pygame.time.get_ticks() / 70.0) if self.pulse_t > 0 else 0.0)

        spacing = 18
        for i in range(cap):
            cx = x + i * spacing
            cy = y
            filled = i < mana

            if filled and full:
                r = int(6 + 1.3 * base_pulse)
            else:
                r = 6
            if filled:
                r = int(r * feedback)

            if filled:
                core = (246, 210, 122)
                rim = (255, 236, 172)
                if buffed:
                    core = (164, 226, 255)
                    rim = (198, 244, 255)
                    glow = pygame.Surface((22, 22), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (116, 214, 255, 86), (11, 11), 10)
                    s.blit(glow, (cx - 11, cy - 11))
            else:
                core = (76, 74, 98)
                rim = (104, 98, 132)

            pygame.draw.circle(s, core, (cx, cy), r)
            pygame.draw.circle(s, rim, (cx, cy), r, 1)
            pygame.draw.circle(s, (22, 18, 32), (cx, cy), max(2, r - 2), 1)
