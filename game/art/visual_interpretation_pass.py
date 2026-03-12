from __future__ import annotations

import math
import random

import pygame

from game.art.symbol_overlay import draw_symbol_overlay


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = _clamp(ratio, 0.0, 1.0)
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def resolve_energy_color(semantic: dict[str, object], palette) -> tuple[int, int, int]:
    energy = str(semantic.get("energy", "") or semantic.get("energy_type", "")).lower()
    if any(token in energy for token in ("solar", "sun", "dawn", "light")):
        return (244, 225, 140)
    if any(token in energy for token in ("void", "corrupt", "smoke", "crimson")):
        return (214, 118, 214)
    if any(token in energy for token in ("wisdom", "stable", "chakana", "mystic", "teal")):
        return (132, 234, 224)
    return palette[3] if len(palette) > 3 else (220, 220, 220)


def _mask_outline(mask_surface: pygame.Surface, color: tuple[int, int, int], alpha: int, width: int) -> pygame.Surface:
    outline = pygame.Surface(mask_surface.get_size(), pygame.SRCALPHA)
    bounds = mask_surface.get_bounding_rect(min_alpha=12)
    if bounds.width <= 0 or bounds.height <= 0:
        return outline
    for y in range(bounds.top, bounds.bottom):
        for x in range(bounds.left, bounds.right):
            if mask_surface.get_at((x, y)).a <= 12:
                continue
            for oy in range(-width, width + 1):
                for ox in range(-width, width + 1):
                    if ox == 0 and oy == 0:
                        continue
                    if ox * ox + oy * oy > width * width + 1:
                        continue
                    px = x + ox
                    py = y + oy
                    if px < 0 or py < 0 or px >= outline.get_width() or py >= outline.get_height():
                        continue
                    if mask_surface.get_at((px, py)).a > 12:
                        continue
                    prev = outline.get_at((px, py))
                    if prev.a < alpha:
                        outline.set_at((px, py), (color[0], color[1], color[2], alpha))
    return outline


def build_layered_halo(surface_size: tuple[int, int], layout: dict[str, object], semantic: dict[str, object], palette, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    color = resolve_energy_color(semantic, palette)
    rect: pygame.Rect = layout["rect"]
    anchor = layout.get("halo_anchor", rect.center)
    radius_x = max(18, int(rect.height * 0.28))
    radius_y = max(14, int(rect.height * 0.22))

    halo_core = pygame.Surface(surface_size, pygame.SRCALPHA)
    halo_glow = pygame.Surface(surface_size, pygame.SRCALPHA)
    halo_noise = pygame.Surface(surface_size, pygame.SRCALPHA)

    core_rect = pygame.Rect(int(anchor[0] - radius_x), int(anchor[1] - radius_y), radius_x * 2, radius_y * 2)
    glow_rect = core_rect.inflate(int(radius_x * 0.9), int(radius_y * 0.9))
    pygame.draw.ellipse(halo_glow, (*color, 54), glow_rect)
    pygame.draw.ellipse(halo_core, (*_mix(color, (255, 255, 255), 0.35), 96), core_rect, max(2, rect.width // 40))
    inner_rect = core_rect.inflate(-max(6, rect.width // 18), -max(6, rect.height // 14))
    pygame.draw.ellipse(halo_core, (*color, 38), inner_rect)

    for _ in range(18):
        angle = rng.uniform(0.0, math.tau)
        dist_x = rng.uniform(radius_x * 0.55, radius_x * 1.12)
        dist_y = rng.uniform(radius_y * 0.55, radius_y * 1.12)
        px = int(anchor[0] + math.cos(angle) * dist_x)
        py = int(anchor[1] + math.sin(angle) * dist_y)
        size = rng.randint(1, 3)
        pygame.draw.circle(halo_noise, (*_mix(color, (255, 255, 255), 0.18), 82), (px, py), size)
    return {
        "halo_core": halo_core,
        "halo_glow": halo_glow,
        "halo_noise": halo_noise,
        "halo_color": color,
    }


def apply_subject_clarity(subject_mask: pygame.Surface, subject_detail: pygame.Surface, layout: dict[str, object], semantic: dict[str, object], palette, halo_color: tuple[int, int, int]) -> None:
    rect: pygame.Rect = layout["rect"]
    torso_anchor = layout.get("torso_anchor", rect.center)
    subject_core = layout.get("subject_core_rect", rect)

    shadow_rect = pygame.Rect(
        int(torso_anchor[0] - rect.width * 0.12),
        int(torso_anchor[1] - rect.height * 0.02),
        int(rect.width * 0.24),
        int(rect.height * 0.24),
    ).clip(subject_detail.get_rect())
    if shadow_rect.width > 0 and shadow_rect.height > 0:
        pygame.draw.ellipse(subject_detail, (0, 0, 0, 64), shadow_rect)

    rim = _mask_outline(subject_mask, halo_color, 88, max(2, rect.width // 52))
    subject_detail.blit(rim, (0, 0))

    chest_symbol = pygame.Surface(subject_detail.get_size(), pygame.SRCALPHA)
    chest_rect = pygame.Rect(
        int(subject_core.centerx - rect.width * 0.08),
        int(subject_core.centery - rect.height * 0.02),
        int(rect.width * 0.16),
        int(rect.height * 0.16),
    )
    draw_symbol_overlay(
        chest_symbol,
        str(semantic.get("symbol", semantic.get("symbol_type", "chakana"))),
        chest_rect.center,
        chest_rect,
        palette,
    )
    subject_detail.blit(chest_symbol, (0, 0))


def build_effect_presence(surface_size: tuple[int, int], layout: dict[str, object], semantic: dict[str, object], halo_color: tuple[int, int, int], seed: int) -> dict[str, pygame.Surface]:
    rng = random.Random(seed + 97)
    energy_particles = pygame.Surface(surface_size, pygame.SRCALPHA)
    ambient_noise = pygame.Surface(surface_size, pygame.SRCALPHA)
    light_beams = pygame.Surface(surface_size, pygame.SRCALPHA)
    rect: pygame.Rect = layout["rect"]
    spawn = layout.get("fx_spawn_anchor", rect.midtop)

    for _ in range(12):
        px = int(rng.uniform(rect.left - rect.width * 0.15, rect.right + rect.width * 0.15))
        py = int(rng.uniform(rect.top - rect.height * 0.08, rect.bottom + rect.height * 0.08))
        pygame.draw.circle(energy_particles, (*halo_color, 102), (px, py), 2)

    for _ in range(18):
        px = int(rng.uniform(0, surface_size[0]))
        py = int(rng.uniform(0, surface_size[1]))
        ambient_noise.set_at((px, py), (*_mix(halo_color, (255, 255, 255), 0.10), 30))

    for offset in (-1, 0, 1):
        top = (int(spawn[0] + offset * rect.width * 0.18), int(rect.top - rect.height * 0.10))
        bottom = (int(spawn[0] + offset * rect.width * 0.08), int(rect.bottom))
        points = [
            (top[0] - 5, top[1]),
            (top[0] + 5, top[1]),
            (bottom[0] + 16, bottom[1]),
            (bottom[0] - 16, bottom[1]),
        ]
        pygame.draw.polygon(light_beams, (*halo_color, 28), points)

    return {
        "energy_particles": energy_particles,
        "ambient_noise": ambient_noise,
        "light_beams": light_beams,
    }
