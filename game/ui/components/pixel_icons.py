from __future__ import annotations

import pygame


_ICON_CACHE: dict[tuple[str, tuple[int, int, int], int], pygame.Surface] = {}


def _pix(surface: pygame.Surface, color: tuple[int, int, int], size: int, x: int, y: int):
    r = pygame.Rect(x * size, y * size, size, size)
    pygame.draw.rect(surface, color, r)


def render_icon(icon_type: str, color: tuple[int, int, int], size: int = 2) -> pygame.Surface:
    key = (str(icon_type), tuple(color), int(size))
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    px = max(1, int(size))
    surf = pygame.Surface((16 * px, 16 * px), pygame.SRCALPHA)
    c = tuple(int(v) for v in color[:3])

    if icon_type == "sword":
        for i in range(2, 10):
            _pix(surf, c, px, 3 + i // 2, i)
        for x in range(5, 11):
            _pix(surf, c, px, x, 10)
        for y in range(11, 14):
            _pix(surf, c, px, 8, y)
        _pix(surf, c, px, 7, 14)
        _pix(surf, c, px, 9, 14)
    elif icon_type == "shield":
        for y in range(3, 10):
            _pix(surf, c, px, 4, y)
            _pix(surf, c, px, 11, y)
        for x in range(5, 11):
            _pix(surf, c, px, x, 3)
        for d in range(0, 4):
            _pix(surf, c, px, 7 - d, 10 + d)
            _pix(surf, c, px, 8 + d, 10 + d)
    elif icon_type == "crack":
        points = [(3, 3), (6, 3), (5, 7), (9, 7), (7, 12), (11, 12), (6, 15), (8, 10), (4, 10)]
        for x, y in points:
            _pix(surf, c, px, x, y)
            _pix(surf, c, px, min(15, x + 1), y)
    elif icon_type == "star":
        for x, y in [(8, 2), (8, 3), (8, 4), (8, 11), (8, 12), (8, 13), (2, 8), (3, 8), (4, 8), (11, 8), (12, 8), (13, 8), (5, 5), (6, 6), (10, 10), (11, 11), (10, 6), (11, 5), (5, 11), (6, 10), (7, 7), (9, 9), (7, 9), (9, 7)]:
            _pix(surf, c, px, x, y)
    elif icon_type == "eye":
        pygame.draw.ellipse(surf, c, pygame.Rect(2 * px, 5 * px, 12 * px, 6 * px), max(1, px))
        pygame.draw.circle(surf, c, (8 * px, 8 * px), max(1, 2 * px))
    elif icon_type == "bolt":
        for x, y in [(7, 2), (8, 2), (6, 6), (7, 6), (5, 10), (6, 10), (9, 10), (10, 10), (7, 14), (8, 14), (8, 7), (9, 7), (7, 11), (8, 11)]:
            _pix(surf, c, px, x, y)
    elif icon_type == "scroll":
        pygame.draw.rect(surf, c, pygame.Rect(3 * px, 4 * px, 10 * px, 8 * px), max(1, px))
        pygame.draw.circle(surf, c, (4 * px, 12 * px), max(1, 2 * px), max(1, px))
        pygame.draw.circle(surf, c, (12 * px, 12 * px), max(1, 2 * px), max(1, px))
        pygame.draw.line(surf, c, (5 * px, 7 * px), (11 * px, 7 * px), max(1, px))
        pygame.draw.line(surf, c, (5 * px, 9 * px), (10 * px, 9 * px), max(1, px))
    else:
        pygame.draw.rect(surf, c, pygame.Rect(4 * px, 4 * px, 8 * px, 8 * px), max(1, px))

    _ICON_CACHE[key] = surf
    return surf


def draw_icon_with_value(surface: pygame.Surface, icon_type: str, value: int, color: tuple[int, int, int], font, x: int, y: int, size: int = 2):
    icon = render_icon(icon_type, color, size=size)
    surface.blit(icon, (x, y))
    txt = font.render(str(int(value)), True, color)
    surface.blit(txt, (x + icon.get_width() + 4, y + max(0, (icon.get_height() - txt.get_height()) // 2)))
    return x + icon.get_width() + txt.get_width() + 14
