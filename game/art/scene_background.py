from __future__ import annotations

import random

import pygame

from game.art.scene_engine import _draw_background
from game.art.visual_interpretation_pass import resolve_energy_color


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def _far_gradient(surface: pygame.Surface, top_color, bottom_color) -> None:
    h = surface.get_height()
    w = surface.get_width()
    for y in range(h):
        ratio = y / max(1, h - 1)
        color = _mix(top_color, bottom_color, ratio)
        pygame.draw.line(surface, (*color, 255), (0, y), (w, y))


def render_scene_background(size: tuple[int, int], semantic: dict, palette, seed: int) -> dict[str, pygame.Surface]:
    rng = random.Random(seed)
    energy_color = resolve_energy_color(semantic, palette)

    background_far = pygame.Surface(size, pygame.SRCALPHA)
    background_mid = pygame.Surface(size, pygame.SRCALPHA)
    background_near = pygame.Surface(size, pygame.SRCALPHA)

    top = _mix(palette[2], energy_color, 0.12)
    bottom = _mix(palette[0], palette[2], 0.35)
    _far_gradient(background_far, top, bottom)

    raw_bg = pygame.Surface(size, pygame.SRCALPHA)
    _draw_background(raw_bg, semantic, palette, rng)
    background_mid.blit(raw_bg, (0, 0))
    mute = pygame.Surface(size, pygame.SRCALPHA)
    mute.fill((0, 0, 0, 124))
    background_mid.blit(mute, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    for idx in range(4):
        width = int(size[0] * (0.18 + idx * 0.06))
        height = int(size[1] * (0.12 + idx * 0.03))
        x = int(size[0] * (0.10 + idx * 0.17))
        y = int(size[1] * (0.43 + idx * 0.04))
        pts = [(x, y + height), (x + width // 2, y), (x + width, y + height)]
        pygame.draw.polygon(background_mid, (*_mix(palette[2], energy_color, 0.08), 42), pts)

    band = pygame.Rect(0, int(size[1] * 0.70), size[0], int(size[1] * 0.30))
    pygame.draw.rect(background_mid, (*palette[2], 36), band)

    for _ in range(12):
        px = int(rng.uniform(0, size[0]))
        py = int(rng.uniform(size[1] * 0.08, size[1] * 0.92))
        pygame.draw.circle(background_near, (*energy_color, 102), (px, py), 2)

    background = pygame.Surface(size, pygame.SRCALPHA)
    environment = pygame.Surface(size, pygame.SRCALPHA)
    background.blit(background_far, (0, 0))
    background.blit(background_mid, (0, 0))
    environment.blit(background_near, (0, 0))
    return {
        'background_far': background_far,
        'background_mid': background_mid,
        'background_near': background_near,
        'background': background,
        'environment': environment,
    }
