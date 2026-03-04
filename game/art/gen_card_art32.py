from __future__ import annotations

import random
import pygame

from game.art.gen_art32 import add_rune_strokes, apply_fake_glow, dither, draw_sacred_geometry_bg, draw_symbol, final_grade, palette_for_family, seed_from_id

GEN_CARD_ART_VERSION = "card32_v2"


def render_card(card_id: str, family: str, symbol: str) -> pygame.Surface:
    rng = random.Random(seed_from_id(card_id, GEN_CARD_ART_VERSION))
    low = pygame.Surface((128, 96), flags=pygame.SRCALPHA, depth=32)
    low.fill((20, 14, 30, 255))
    pal = palette_for_family(family)
    draw_sacred_geometry_bg(low, pal, rng)
    draw_symbol(low, symbol, rng)
    add_rune_strokes(low, rng, n=12)
    dither(low, 0.12)
    apply_fake_glow(low, pal[3], 2)
    final_grade(low)
    out = pygame.Surface((320, 220), flags=pygame.SRCALPHA, depth=32)
    out.fill((18, 12, 28, 255))
    out.blit(pygame.transform.scale(low, (320, 220)), (0, 0))
    return out.convert_alpha()
