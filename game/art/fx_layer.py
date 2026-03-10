from __future__ import annotations

import random
import pygame


def draw_fx(surface: pygame.Surface, semantic: dict, palette, rng: random.Random):
    desc = ' '.join([
        str(semantic.get('effects', '') or ''),
        str(semantic.get('effects_desc', '') or ''),
        str(semantic.get('energy', '') or ''),
    ]).lower()
    color = palette[3]
    w, h = surface.get_size()
    subtle = 'subtle' in desc or 'calm' in desc or 'ward' in desc
    n_streaks = 2 if subtle else 4
    n_orbs = 3 if subtle else 5
    n_sparks = 10 if subtle else 16
    focus_band_y = int(h * 0.58)
    focus_band_h = int(h * 0.24)

    for _ in range(n_streaks):
        x1 = rng.randint(int(w * 0.18), int(w * 0.42))
        y1 = rng.randint(focus_band_y, focus_band_y + focus_band_h)
        x2 = x1 + rng.randint(int(w * 0.16), int(w * 0.28))
        y2 = y1 - rng.randint(4, int(h * 0.1))
        pygame.draw.line(surface, (*color, 118), (x1, y1), (x2, y2), rng.randint(2, 4))

    for _ in range(n_orbs):
        cx = rng.randint(int(w * 0.28), int(w * 0.72))
        cy = rng.randint(int(h * 0.28), int(h * 0.68))
        radius = rng.randint(max(4, w // 42), max(8, w // 26))
        pygame.draw.circle(surface, (*color, 78), (cx, cy), radius)
        pygame.draw.circle(surface, (*color, 128), (cx, cy), max(2, radius // 2))

    for _ in range(n_sparks):
        sx = rng.randint(int(w * 0.12), int(w * 0.88))
        sy = rng.randint(int(h * 0.1), int(h * 0.86))
        pygame.draw.circle(surface, (*color, rng.randint(72, 132)), (sx, sy), rng.randint(1, 2))
