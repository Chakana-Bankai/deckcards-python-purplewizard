from __future__ import annotations

import random
import pygame

from game.art.gen_art32 import add_rune_strokes, apply_fake_glow, dither, draw_sacred_geometry_bg, final_grade, seed_from_id

GEN_GUIDE_ART_VERSION = "guide32_v1"


def render_guide(guide_type: str) -> pygame.Surface:
    rng = random.Random(seed_from_id(f"guide:{guide_type}", GEN_GUIDE_ART_VERSION))
    low = pygame.Surface((64, 64), flags=pygame.SRCALPHA, depth=32)
    low.fill((24, 18, 36, 255))
    draw_sacred_geometry_bg(low, ((36, 26, 58), (88, 60, 132), (214, 188, 96)), rng)
    cx, cy = 32, 32
    if guide_type == "angel":
        pygame.draw.ellipse(low, (220, 206, 255), (10, 8, 44, 50))
    elif guide_type == "shaman":
        pygame.draw.polygon(low, (155, 190, 145), [(10, 14), (54, 14), (46, 56), (18, 56)])
    elif guide_type == "demon":
        pygame.draw.polygon(low, (220, 102, 142), [(32, 4), (58, 22), (50, 58), (14, 58), (6, 22)])
    else:
        pygame.draw.rect(low, (120, 214, 235), (10, 12, 44, 46), border_radius=8)
    for ex in (23, 41):
        pygame.draw.circle(low, (20, 18, 30), (ex, 30), 4)
        pygame.draw.circle(low, (235, 245, 255), (ex, 30), 2)
    add_rune_strokes(low, rng, n=8)
    dither(low, 0.12)
    apply_fake_glow(low)
    final_grade(low)
    return pygame.transform.scale(low, (256, 256)).convert_alpha()
