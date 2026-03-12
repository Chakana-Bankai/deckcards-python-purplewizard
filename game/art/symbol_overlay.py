from __future__ import annotations

import pygame


def draw_symbol_overlay(surface: pygame.Surface, symbol_type: str, anchor: tuple[int, int], subject_rect: pygame.Rect, palette: tuple[tuple[int, int, int], ...]):
    color = palette[3] if len(palette) > 3 else (220, 220, 220)
    size = max(14, int(subject_rect.height * 0.18))
    x, y = int(anchor[0]), int(anchor[1])
    if 'solar' in str(symbol_type).lower():
        pygame.draw.circle(surface, (*color, 72), (x, y), size)
        pygame.draw.circle(surface, (*color, 110), (x, y), max(4, size // 3), 1)
    elif 'corrupt' in str(symbol_type).lower() or 'seal' in str(symbol_type).lower():
        rect = pygame.Rect(x - size, y - size, size * 2, size * 2)
        pygame.draw.rect(surface, (*color, 68), rect, 2)
    else:
        pts = [(x, y - size), (x + size, y), (x, y + size), (x - size, y)]
        pygame.draw.polygon(surface, (*color, 72), pts, 2)
