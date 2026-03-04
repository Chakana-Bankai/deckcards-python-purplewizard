from __future__ import annotations

import math

import pygame

GEN_AVATAR_VERSION = "chakana_v4"


def _stepped_cross_points(cx: int, cy: int, u: int) -> list[tuple[int, int]]:
    s1 = 3 * u
    s2 = 2 * u
    s3 = 1 * u
    return [
        (cx - s3, cy - s1), (cx + s3, cy - s1),
        (cx + s3, cy - s2), (cx + s2, cy - s2),
        (cx + s2, cy - s3), (cx + s1, cy - s3),
        (cx + s1, cy + s3), (cx + s2, cy + s3),
        (cx + s2, cy + s2), (cx + s3, cy + s2),
        (cx + s3, cy + s1), (cx - s3, cy + s1),
        (cx - s3, cy + s2), (cx - s2, cy + s2),
        (cx - s2, cy + s3), (cx - s1, cy + s3),
        (cx - s1, cy - s3), (cx - s2, cy - s3),
        (cx - s2, cy - s2), (cx - s3, cy - s2),
        (cx - s3, cy - s1), (cx - s2, cy - s1),
        (cx - s2, cy - s2), (cx - s3, cy - s2),
    ]


def _dither(surface: pygame.Surface, strength: int = 8):
    w, h = surface.get_size()
    for y in range(0, h, 2):
        for x in range((y // 2) % 2, w, 2):
            c = surface.get_at((x, y))
            surface.set_at((x, y), (max(0, c.r - strength), max(0, c.g - strength), max(0, c.b - strength), c.a))


def _render_base(size: int, glow_alpha: int = 36) -> pygame.Surface:
    obsidian = (10, 10, 16)
    royal = (124, 84, 214)
    royal_hi = (182, 138, 246)
    gold = (232, 196, 94)

    surf = pygame.Surface((size, size), flags=pygame.SRCALPHA, depth=32)
    surf.fill(obsidian)
    _dither(surf, 7)

    cx = size // 2
    cy = size // 2
    unit = max(3, size // 12)
    pts = _stepped_cross_points(cx, cy, unit)
    pygame.draw.polygon(surf, royal, pts)
    pygame.draw.polygon(surf, royal_hi, pts, 2)

    inset_pts = _stepped_cross_points(cx, cy, max(2, unit - 1))
    pygame.draw.polygon(surf, gold, inset_pts, 1)

    center = max(6, unit * 2)
    c_rect = pygame.Rect(cx - center // 2, cy - center // 2, center, center)
    pygame.draw.rect(surf, obsidian, c_rect)
    pygame.draw.rect(surf, gold, c_rect, 2)

    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(glow, (gold[0], gold[1], gold[2], max(0, min(120, glow_alpha))), (cx, cy), max(8, int(size * 0.34)), 0)
    surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return surf.convert_alpha()


def render_avatar(t: float = 0.0, size: int = 256) -> pygame.Surface:
    if isinstance(t, int) and size == 256:
        size = int(t)
        t = 0.0
    phase = math.sin((float(t) / 1.2) * (2.0 * math.pi))
    scale = 1.02 + 0.02 * phase
    target_size = max(16, int(size * scale))
    glow_alpha = 40 + int(22 * (0.5 + 0.5 * phase))
    base = _render_base(size, glow_alpha=glow_alpha)
    scaled = pygame.transform.scale(base, (target_size, target_size)).convert_alpha()
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    ox = (size - target_size) // 2
    oy = (size - target_size) // 2
    out.blit(scaled, (ox, oy))
    return out.convert_alpha()
