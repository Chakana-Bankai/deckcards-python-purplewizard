from __future__ import annotations

import math

import pygame

from game.art.gen_art32 import chakana_points
from game.ui.theme import UI_THEME


class LoadingWidget:
    def __init__(self):
        self.hints = [
            "La Chakana representa los tres mundos del espíritu.",
            "Kay Pacha, Hanan Pacha y Ukhu Pacha giran en equilibrio.",
            "Cada símbolo abre un sendero en la Trama.",
        ]
        self.hint_idx = 0
        self._hint_t = 0.0

    def set_hint(self, label: str | None = None):
        if label:
            self.hints[0] = str(label)
            self.hint_idx = 0

    def tick(self, dt: float):
        self._hint_t += max(0.0, float(dt))
        if self._hint_t > 4.0:
            self._hint_t = 0.0
            self.hint_idx = (self.hint_idx + 1) % len(self.hints)

    def draw(self, surface: pygame.Surface, body_font, *, hint_text: str | None = None):
        w, h = surface.get_size()
        t = pygame.time.get_ticks() / 1000.0

        anchor = (w - 120, h - 98)
        rot = t * 0.9
        pulse = 1.0 + 0.07 * math.sin(t * 3.2)
        pts = chakana_points(anchor, int(28 * pulse), step=rot)
        pygame.draw.polygon(surface, UI_THEME["gold"], pts, 3)
        pygame.draw.circle(surface, UI_THEME["accent_violet"], anchor, 44, 1)

        orb_r = 22
        ox = anchor[0] + int(math.cos(t * 2.3) * orb_r)
        oy = anchor[1] + int(math.sin(t * 2.3) * orb_r)
        glow = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(glow, (220, 196, 255, 180), (10, 10), 7)
        pygame.draw.circle(glow, (220, 196, 255, 110), (10, 10), 10, 2)
        surface.blit(glow, (ox - 10, oy - 10))

        hint = str(hint_text or self.hints[self.hint_idx])
        txt = body_font.render(hint, True, UI_THEME["muted"])
        surface.blit(txt, txt.get_rect(center=(w // 2, h - 66)))
