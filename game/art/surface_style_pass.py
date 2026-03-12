from __future__ import annotations

import pygame


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def apply_subject_surface_style(target: pygame.Surface, skeleton: dict[str, object], tones: dict[str, tuple[int, int, int, int]], archetype: str):
    rect: pygame.Rect = skeleton['rect']
    cloth = tones['cloth'][:3]
    cloth_dark = tones['cloth_dark'][:3]
    trim = tones['trim'][:3]
    metal = tones['metal'][:3]
    rune = tones['rune'][:3]
    style = pygame.Surface(target.get_size(), pygame.SRCALPHA)

    fold_xs = [
        int(rect.left + rect.width * 0.36),
        int(rect.left + rect.width * 0.48),
        int(rect.left + rect.width * 0.61),
    ]
    for index, x in enumerate(fold_xs):
        start_y = int(rect.top + rect.height * (0.24 + index * 0.03))
        end_y = int(rect.bottom - rect.height * 0.12)
        shade = cloth_dark if index % 2 == 0 else _mix(cloth_dark, trim, 0.22)
        pygame.draw.line(style, (*shade, 34), (x, start_y), (x - rect.width // 20, end_y), max(1, rect.width // 70))
        pygame.draw.line(style, (*_mix(cloth, trim, 0.25), 22), (x + rect.width // 32, start_y + rect.height // 24), (x, end_y - rect.height // 18), 1)

    torso_panel = pygame.Rect(int(rect.left + rect.width * 0.30), int(rect.top + rect.height * 0.22), int(rect.width * 0.38), int(rect.height * 0.24))
    pygame.draw.rect(style, (*_mix(cloth, cloth_dark, 0.28), 10), torso_panel, border_radius=max(4, rect.width // 32))

    if archetype == 'archon':
        rune_rect = pygame.Rect(int(rect.centerx - rect.width * 0.035), int(rect.top + rect.height * 0.30), int(rect.width * 0.07), int(rect.height * 0.09))
        pygame.draw.ellipse(style, (*rune, 20), rune_rect, 2)
        pygame.draw.line(style, (*metal, 16), (rune_rect.centerx, rune_rect.top), (rune_rect.centerx, rune_rect.bottom), 1)
    elif archetype == 'guide_mage':
        shawl = [(int(rect.left + rect.width * 0.28), int(rect.top + rect.height * 0.26)), (int(rect.left + rect.width * 0.50), int(rect.top + rect.height * 0.22)), (int(rect.left + rect.width * 0.70), int(rect.top + rect.height * 0.30)), (int(rect.left + rect.width * 0.50), int(rect.top + rect.height * 0.36))]
        pygame.draw.polygon(style, (*_mix(trim, cloth, 0.55), 12), shawl)
    else:
        plate = pygame.Rect(int(rect.centerx - rect.width * 0.09), int(rect.top + rect.height * 0.26), int(rect.width * 0.18), int(rect.height * 0.10))
        pygame.draw.rect(style, (*metal, 16), plate, border_radius=max(4, rect.width // 30))
        pygame.draw.line(style, (*_mix(metal, (255, 255, 255), 0.35), 14), (plate.left + 2, plate.top + 2), (plate.right - 2, plate.top + 2), 1)

    target.blit(style, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def apply_weapon_surface_style(back_layer: pygame.Surface, front_layer: pygame.Surface, family: str, tones: dict[str, tuple[int, int, int, int]]):
    bounds = back_layer.get_bounding_rect(min_alpha=18).union(front_layer.get_bounding_rect(min_alpha=18)).clip(back_layer.get_rect())
    if bounds.width <= 0 or bounds.height <= 0:
        return
    style = pygame.Surface(back_layer.get_size(), pygame.SRCALPHA)
    wood = tones['wood'][:3]
    metal = tones['metal'][:3]
    rune = tones['rune'][:3]
    material = metal if family in {'spear', 'sword'} else wood
    hi = _mix(material, (255, 255, 255), 0.26)
    for y in range(bounds.top, bounds.bottom, max(3, bounds.height // 14)):
        alpha = 8 if family in {'staff', 'orb'} else 12
        pygame.draw.line(style, (*_mix(material, rune, 0.20), alpha), (bounds.left, y), (bounds.right, y + bounds.height // 28), 1)
    pygame.draw.line(style, (*hi, 14), (bounds.left + 2, bounds.top + 2), (bounds.right - 2, bounds.top + bounds.height // 6), 1)
    back_layer.blit(style, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    edge = pygame.Surface(front_layer.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(edge, (*_mix(rune, hi, 0.35), 8), bounds.inflate(2, 2), 1, border_radius=2)
    front_layer.blit(edge, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

