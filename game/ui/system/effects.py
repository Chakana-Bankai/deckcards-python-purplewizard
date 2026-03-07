"""Lightweight visual effect helpers for pygame UI."""

from __future__ import annotations

import math
import pygame


def subtle_pulse(ticks: int, speed: float = 180.0, lo: float = 0.88, hi: float = 1.0) -> float:
    wave = 0.5 + 0.5 * math.sin(ticks / max(1.0, speed))
    return lo + (hi - lo) * wave


def glow_surface(size: tuple[int, int], color: tuple[int, int, int], alpha: int, radius: int = 14) -> pygame.Surface:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, max(0, min(255, alpha))), surf.get_rect(), border_radius=radius)
    return surf


def hover_shadow(rect: pygame.Rect, alpha: int = 120) -> tuple[pygame.Surface, tuple[int, int]]:
    shadow = pygame.Surface((rect.w + 22, rect.h + 22), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, alpha), shadow.get_rect(), border_radius=18)
    return shadow, (rect.x - 11, rect.y - 8)


def rgb_aura_phase(ticks: int, offset: float = 0.0) -> float:
    return 0.5 + 0.5 * math.sin((ticks * 0.01) + offset)


def text_fade_alpha(progress: float) -> int:
    p = max(0.0, min(1.0, progress))
    return int(255 * p)


def particle_drift(x: float, y: float, vx: float, vy: float, dt: float) -> tuple[float, float]:
    return x + vx * dt, y + vy * dt
