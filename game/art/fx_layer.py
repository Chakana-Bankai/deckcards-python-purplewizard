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
    n_arcs = 3 if 'subtle' in desc else 5
    n_sparks = 12 if 'subtle' in desc else 20
    for _ in range(n_arcs):
        cx = rng.randint(int(w * 0.22), int(w * 0.78))
        cy = rng.randint(int(h * 0.18), int(h * 0.78))
        rw = rng.randint(max(32, w // 8), max(54, w // 4))
        rh = rng.randint(max(22, h // 10), max(42, h // 5))
        start = rng.uniform(0.1, 3.14)
        end = start + rng.uniform(0.8, 2.1)
        pygame.draw.arc(surface, (*color, 120), pygame.Rect(cx - rw // 2, cy - rh // 2, rw, rh), start, end, 2)
    for _ in range(n_sparks):
        sx = rng.randint(int(w * 0.15), int(w * 0.85))
        sy = rng.randint(int(h * 0.12), int(h * 0.84))
        pygame.draw.circle(surface, (*color, rng.randint(70, 140)), (sx, sy), rng.randint(1, 3))
