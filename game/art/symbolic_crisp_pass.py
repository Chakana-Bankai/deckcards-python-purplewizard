from __future__ import annotations

import pygame

from game.art.style_lock import symbolic_style_active


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def _outline(surface: pygame.Surface, color: tuple[int, int, int], alpha_cutoff: int = 20, radius: int = 1, alpha: int = 255):
    mask = pygame.mask.from_surface(surface, alpha_cutoff)
    pts = mask.outline()
    if len(pts) <= 1:
        return
    for ox, oy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
        shifted = [(x + ox, y + oy) for x, y in pts]
        pygame.draw.lines(surface, (*color, alpha), True, shifted, max(1, radius))


def apply_subject_crisp_pass(target: pygame.Surface, skeleton: dict[str, object], tones: dict[str, tuple[int, int, int, int]], archetype: str):
    if not symbolic_style_active():
        return
    rect: pygame.Rect = skeleton['rect']
    overlay = pygame.Surface(target.get_size(), pygame.SRCALPHA)
    trim = tones['trim'][:3]
    shadow = tones['shadow'][:3]
    cloth = tones['cloth'][:3]
    chest = pygame.Rect(int(rect.left + rect.width * 0.30), int(rect.top + rect.height * 0.18), int(rect.width * 0.40), int(rect.height * 0.18))
    waist = pygame.Rect(int(rect.left + rect.width * 0.34), int(rect.top + rect.height * 0.43), int(rect.width * 0.28), int(rect.height * 0.10))
    pygame.draw.rect(overlay, (*_mix(cloth, trim, 0.18), 36), chest, border_radius=0)
    pygame.draw.rect(overlay, (*_mix(trim, shadow, 0.15), 42), waist, border_radius=0)
    seam_x = int(rect.centerx)
    pygame.draw.line(overlay, (*shadow, 72), (seam_x, chest.top), (seam_x, rect.bottom - rect.height // 8), max(1, rect.width // 60))
    if archetype == 'solar_warrior':
        l = (int(rect.left + rect.width * 0.20), int(rect.top + rect.height * 0.28))
        c = (int(rect.centerx), int(rect.top + rect.height * 0.20))
        r = (int(rect.right - rect.width * 0.20), int(rect.top + rect.height * 0.28))
        pygame.draw.lines(overlay, (*trim, 86), False, [l, c, r], max(1, rect.width // 70))
    elif archetype == 'archon':
        sig = pygame.Rect(int(rect.centerx - rect.width * 0.04), int(rect.top + rect.height * 0.24), int(rect.width * 0.08), int(rect.height * 0.10))
        pygame.draw.rect(overlay, (*trim, 50), sig, 1)
    else:
        halo = pygame.Rect(int(rect.centerx - rect.width * 0.10), int(rect.top + rect.height * 0.10), int(rect.width * 0.20), int(rect.width * 0.20))
        pygame.draw.ellipse(overlay, (*trim, 46), halo, 1)
    target.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    _outline(target, shadow, 18, 1, 224)


def apply_weapon_crisp_pass(back_layer: pygame.Surface, front_layer: pygame.Surface, family: str, tones: dict[str, tuple[int, int, int, int]]):
    if not symbolic_style_active():
        return
    shadow = tones['shadow'][:3]
    hi = tones['rune'][:3] if family in {'staff', 'orb'} else tones['metal'][:3]
    _outline(back_layer, shadow, 18, 1, 240)
    _outline(front_layer, shadow, 18, 1, 248)
    bounds = back_layer.get_bounding_rect(min_alpha=18).union(front_layer.get_bounding_rect(min_alpha=18)).clip(back_layer.get_rect())
    if bounds.width <= 0 or bounds.height <= 0:
        return
    accent = pygame.Surface(back_layer.get_size(), pygame.SRCALPHA)
    pygame.draw.line(accent, (*hi, 84), (bounds.left + 1, bounds.top + 1), (bounds.right - 1, bounds.top + max(2, bounds.height // 5)), 1)
    pygame.draw.rect(accent, (*shadow, 48), bounds.inflate(2, 2), 1)
    back_layer.blit(accent, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def apply_scene_crisp_pass(surface: pygame.Surface, subject_rect: pygame.Rect):
    if not symbolic_style_active():
        return
    w, h = surface.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    horizon_y = int(h * 0.33)
    ground_y = int(h * 0.70)
    pygame.draw.line(overlay, (255, 255, 255, 18), (0, horizon_y), (w, horizon_y), 1)
    pygame.draw.line(overlay, (0, 0, 0, 26), (0, ground_y), (w, ground_y), 2)
    accent_y = int(subject_rect.bottom + max(6, subject_rect.height * 0.06))
    pygame.draw.line(overlay, (255, 255, 255, 10), (subject_rect.left - 6, accent_y), (subject_rect.right + 6, accent_y), 1)
    surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
