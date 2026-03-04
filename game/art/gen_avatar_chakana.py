from __future__ import annotations

import pygame

GEN_AVATAR_VERSION = "chakana_v3"


def _chakana_20(center: tuple[int, int], size: int) -> list[tuple[int, int]]:
    cx, cy = center
    s = max(12, size)
    t = max(4, s // 3)
    return [
        (cx - t, cy - s), (cx + t, cy - s),
        (cx + t, cy - t), (cx + s, cy - t),
        (cx + s, cy + t), (cx + t, cy + t),
        (cx + t, cy + s), (cx - t, cy + s),
        (cx - t, cy + t), (cx - s, cy + t),
        (cx - s, cy - t), (cx - t, cy - t),
        (cx - t, cy - s + t), (cx, cy - s + t),
        (cx, cy - t), (cx + s - t, cy),
        (cx, cy + t), (cx, cy + s - t),
        (cx - t, cy), (cx - s + t, cy),
    ]


def render_avatar(size: int = 256) -> pygame.Surface:
    surf = pygame.Surface((size, size), flags=pygame.SRCALPHA, depth=32)
    surf.fill((20, 14, 32, 255))
    c = size // 2
    pts = _chakana_20((c, c), int(size * 0.32))
    pygame.draw.polygon(surf, (206, 174, 248), pts, 4)
    sq = int(size * 0.16)
    pygame.draw.rect(surf, (24, 18, 36), pygame.Rect(c - sq // 2, c - sq // 2, sq, sq))
    pygame.draw.rect(surf, (206, 174, 248), pygame.Rect(c - sq // 2, c - sq // 2, sq, sq), 2)
    stars = [(c + 52, c - 56), (c + 70, c - 72), (c + 88, c - 60), (c + 74, c - 44)]
    for st in stars:
        pygame.draw.circle(surf, (238, 236, 255), st, 3)
    return surf.convert_alpha()
