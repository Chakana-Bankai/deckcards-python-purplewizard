from __future__ import annotations

import pygame


def generate_frame_asset(size: tuple[int, int] = (512, 512), color: tuple[int, int, int] = (214, 186, 112)) -> pygame.Surface:
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    border = max(10, int(min(w, h) * 0.04))
    art_rect = pygame.Rect(border * 2, border * 2, w - border * 4, h - border * 4)
    pygame.draw.rect(surf, (*color, 220), (border, border, w - border * 2, h - border * 2), border // 2, border_radius=10)
    pygame.draw.rect(surf, (0, 0, 0, 0), art_rect)
    for cx, cy in ((border + 14, border + 14), (w - border - 14, border + 14), (border + 14, h - border - 14), (w - border - 14, h - border - 14)):
        pygame.draw.circle(surf, (*color, 190), (cx, cy), 10, 2)
        pygame.draw.arc(surf, (*color, 160), pygame.Rect(cx - 18, cy - 18, 36, 36), 0.4, 2.7, 1)
    top = (w // 2, border + 6)
    bot = (w // 2, h - border - 6)
    for cx, cy in (top, bot):
        pygame.draw.arc(surf, (*color, 190), pygame.Rect(cx - 28, cy - 12, 56, 24), 3.3, 6.1, 2)
        pygame.draw.line(surf, (*color, 190), (cx - 20, cy), (cx + 20, cy), 2)
    return surf
