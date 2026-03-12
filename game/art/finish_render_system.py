from __future__ import annotations

import pygame


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = _clamp(ratio, 0.0, 1.0)
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def _outline(surface: pygame.Surface, color: tuple[int, int, int], alpha_cutoff: int, radius: int, alpha: int):
    mask = pygame.mask.from_surface(surface, alpha_cutoff)
    outline = mask.outline()
    if len(outline) <= 1:
        return
    for ox, oy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius), (-radius, -radius), (radius, -radius), (-radius, radius), (radius, radius)):
        pts = [(x + ox, y + oy) for x, y in outline]
        pygame.draw.lines(surface, (*color, alpha), True, pts, max(1, radius))


def apply_prop_finish(back_layer: pygame.Surface, front_layer: pygame.Surface, family: str, tones: dict[str, tuple[int, int, int, int]], rect: pygame.Rect):
    edge = tones['shadow'][:3]
    highlight = tones['metal'][:3] if family in {'spear', 'sword'} else tones['rune'][:3]
    _outline(back_layer, edge, 28, 2, 220)
    _outline(front_layer, edge, 28, 1, 230)
    bounds = back_layer.get_bounding_rect(min_alpha=16).union(front_layer.get_bounding_rect(min_alpha=16)).clip(back_layer.get_rect())
    if bounds.width <= 0 or bounds.height <= 0:
        return
    sheen = pygame.Surface(back_layer.get_size(), pygame.SRCALPHA)
    for y in range(bounds.top, bounds.bottom):
        for x in range(bounds.left, bounds.right):
            if back_layer.get_at((x, y)).a <= 16 and front_layer.get_at((x, y)).a <= 16:
                continue
            nx = (x - bounds.left) / max(1, bounds.width)
            ny = (y - bounds.top) / max(1, bounds.height)
            if nx > 0.62 or ny > 0.62:
                continue
            alpha = int(22 * (1.0 - nx) * (1.0 - ny * 0.5))
            if alpha <= 0:
                continue
            sheen.set_at((x, y), (*highlight, alpha))
    back_layer.blit(sheen, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def apply_material_finish(target: pygame.Surface, skeleton: dict[str, object], tones: dict[str, tuple[int, int, int, int]], archetype: str):
    rect: pygame.Rect = skeleton['rect']
    cloth_dark = tones['cloth_dark'][:3]
    trim = tones['trim'][:3]
    metal = tones['metal'][:3]
    rune = tones['rune'][:3]
    glaze = pygame.Surface(target.get_size(), pygame.SRCALPHA)
    torso = skeleton['torso_anchor']
    pelvis = skeleton['pelvis_anchor']
    torso_rect = pygame.Rect(int(rect.left + rect.width * 0.26), int(rect.top + rect.height * 0.18), int(rect.width * 0.48), int(rect.height * 0.34))
    for y in range(torso_rect.top, torso_rect.bottom):
        for x in range(torso_rect.left, torso_rect.right):
            if target.get_at((x, y)).a <= 18:
                continue
            ny = (y - torso_rect.top) / max(1, torso_rect.height)
            alpha = int(16 + ny * 18)
            glaze.set_at((x, y), (*cloth_dark, alpha))
    seam_x = int(torso[0])
    for y in range(int(torso_rect.top), int(min(target.get_height(), pelvis[1] + rect.height * 0.12))):
        if 0 <= seam_x < target.get_width() and target.get_at((seam_x, y)).a > 18:
            glaze.set_at((seam_x, y), (*trim, 42))
    if archetype == 'archon':
        clasp = pygame.Rect(int(torso[0] - rect.width * 0.04), int(torso[1] + rect.height * 0.10), int(rect.width * 0.08), int(rect.height * 0.05))
        pygame.draw.rect(glaze, (*metal, 54), clasp, border_radius=max(3, rect.width // 38))
    elif archetype == 'guide_mage':
        rune_rect = pygame.Rect(int(rect.centerx - rect.width * 0.05), int(rect.top + rect.height * 0.20), int(rect.width * 0.10), int(rect.height * 0.08))
        pygame.draw.ellipse(glaze, (*rune, 44), rune_rect, 2)
    else:
        plate = pygame.Rect(int(rect.centerx - rect.width * 0.06), int(rect.top + rect.height * 0.26), int(rect.width * 0.12), int(rect.height * 0.07))
        pygame.draw.rect(glaze, (*metal, 48), plate, border_radius=max(3, rect.width // 40))
    target.blit(glaze, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def apply_scene_finish(surface: pygame.Surface, subject_rect: pygame.Rect, palette):
    w, h = surface.get_size()
    vignette = pygame.Surface((w, h), pygame.SRCALPHA)
    center = subject_rect.center
    for y in range(h):
        for x in range(w):
            dx = abs(x - center[0]) / max(1.0, w * 0.55)
            dy = abs(y - center[1]) / max(1.0, h * 0.60)
            dist = dx * dx + dy * dy
            if dist < 0.65:
                continue
            alpha = min(44, int((dist - 0.65) * 54))
            if alpha <= 0:
                continue
            vignette.set_at((x, y), (0, 0, 0, alpha))
    surface.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    haze = pygame.Surface((w, h), pygame.SRCALPHA)
    band = pygame.Rect(0, int(h * 0.14), w, int(h * 0.32))
    tint = _mix(palette[1], palette[3], 0.18)
    pygame.draw.rect(haze, (*tint, 14), band)
    surface.blit(haze, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
