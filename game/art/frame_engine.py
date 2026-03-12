from __future__ import annotations

import pygame

from game.render.frame_renderer import apply_frame_overlay


def generate_frame_asset(size: tuple[int, int] = (512, 512), color: tuple[int, int, int] = (214, 186, 112)) -> pygame.Surface:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    apply_frame_overlay(surf, surf.get_rect(), "common", accent=color)
    return surf
