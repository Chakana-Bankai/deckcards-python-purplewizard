from __future__ import annotations

import pygame

from game.art.gen_art32 import chakana_points

GEN_AVATAR_VERSION = "chakana_v2"


def render_avatar(size: int = 256) -> pygame.Surface:
    surf = pygame.Surface((size, size), flags=pygame.SRCALPHA, depth=32)
    surf.fill((22, 16, 34, 255))
    c = size // 2
    pts = chakana_points((c, c), int(size * 0.22), 0.35)
    pygame.draw.polygon(surf, (198, 156, 246), pts, 4)
    stars = [(c + 44, c - 58), (c + 62, c - 72), (c + 78, c - 60), (c + 66, c - 46)]
    for st in stars:
        pygame.draw.circle(surf, (236, 236, 255), st, 3)
    return surf.convert_alpha()
