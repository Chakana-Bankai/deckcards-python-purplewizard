from __future__ import annotations

import math

import pygame

from game.art.gen_art32 import chakana_points
from game.ui.theme import UI_THEME
from game.ui.system.typography import ChakanaTypography, SMALL_FONT


class LoadingWidget:
    def __init__(self, hints: list[str] | None = None):
        self.hints = list(hints or [
            "La Chakana conecta los tres mundos.",
            "El equilibrio entre ataque y armonia define al guerrero.",
            "Prever el destino es tan importante como atacar.",
        ])
        self.hint_idx = 0
        self._hint_t = 0.0
        self._hint_font = None

    def set_hints(self, hints: list[str]):
        clean = [str(h).strip() for h in (hints or []) if str(h).strip()]
        if clean:
            self.hints = clean
            self.hint_idx = 0
            self._hint_t = 0.0

    def set_hint(self, label: str | None = None):
        return

    def tick(self, dt: float):
        self._hint_t += max(0.0, float(dt))
        if self._hint_t > 5.0:
            self._hint_t = 0.0
            self.hint_idx = (self.hint_idx + 1) % len(self.hints)

    def draw(self, surface: pygame.Surface, body_font, *, hint_text: str | None = None):
        w, h = surface.get_size()
        t = pygame.time.get_ticks() / 1000.0

        anchor = (w - 110, h - 90)
        core_size = 22
        rot = t * 0.42

        ring = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(ring, (170, 150, 232, 36), (60, 60), 46, 1)
        pygame.draw.circle(ring, (170, 150, 232, 26), (60, 60), 35, 1)
        surface.blit(ring, (anchor[0] - 60, anchor[1] - 60))

        pulse = 1.0 + 0.05 * math.sin(t * 2.1)
        pts = chakana_points(anchor, int(core_size * pulse), step=rot)
        pygame.draw.polygon(surface, (235, 218, 168), pts, 2)

        orbit_r = 32
        ox = anchor[0] + int(math.cos(t * 0.9) * orbit_r)
        oy = anchor[1] + int(math.sin(t * 0.9) * orbit_r)
        pygame.draw.circle(surface, (158, 214, 242), (ox, oy), 3)

        glow = pygame.Surface((84, 84), pygame.SRCALPHA)
        alpha = 30 + int(24 * (0.5 + 0.5 * math.sin(t * 2.0)))
        pygame.draw.circle(glow, (194, 170, 255, alpha), (42, 42), 24)
        surface.blit(glow, (anchor[0] - 42, anchor[1] - 42))

        hint = str(hint_text or self.hints[self.hint_idx])
        if self._hint_font is None:
            size = max(16, int(getattr(body_font, "get_height", lambda: 22)() * 0.72))
            self._hint_font = ChakanaTypography().get(SMALL_FONT, size)
        txt = self._hint_font.render(hint, True, UI_THEME["muted"])
        surface.blit(txt, txt.get_rect(center=(w // 2, h - 34)))

