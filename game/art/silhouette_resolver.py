from __future__ import annotations

import pygame


def _pt(value) -> tuple[int, int]:
    return (int(value[0]), int(value[1]))


def _capsule(surface: pygame.Surface, a, b, width: int, color):
    pa = _pt(a)
    pb = _pt(b)
    width = max(1, int(width))
    pygame.draw.line(surface, color, pa, pb, width)
    pygame.draw.circle(surface, color, pa, max(1, width // 2))
    pygame.draw.circle(surface, color, pb, max(1, width // 2))


def _poly(surface: pygame.Surface, color, points):
    pygame.draw.polygon(surface, color, [_pt(p) for p in points])


def _smooth_mask(surface: pygame.Surface) -> pygame.Surface:
    w, h = surface.get_size()
    up = pygame.transform.smoothscale(surface, (w * 2, h * 2)).convert_alpha()
    down = pygame.transform.smoothscale(up, (w, h)).convert_alpha()
    clean = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            c = down.get_at((x, y))
            if c.a >= 20:
                clean.set_at((x, y), (255, 255, 255, 255))
    return clean


def _clear_strays(surface: pygame.Surface) -> pygame.Surface:
    bounds = surface.get_bounding_rect(min_alpha=12)
    if bounds.width <= 0 or bounds.height <= 0:
        return surface
    out = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    out.blit(surface, bounds.topleft, bounds)
    return out


def _archon_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    head = skeleton['head_anchor']
    shoulders = (skeleton['shoulder_left_anchor'], skeleton['shoulder_right_anchor'])
    hips = skeleton['hip_anchor']
    feet = (skeleton['foot_left_anchor'], skeleton['foot_right_anchor'])
    robe = [
        (shoulders[0][0] - 8, shoulders[0][1] + 2),
        (head[0] - 10, head[1] + 4),
        (shoulders[1][0] + 8, shoulders[1][1] + 2),
        (hips[0] + 14, hips[1] + 18),
        (feet[1][0] + 10, feet[1][1]),
        (feet[0][0] - 10, feet[0][1]),
        (hips[0] - 14, hips[1] + 18),
    ]
    _poly(layer, color, robe)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - 9), int(head[1] - 11), 18, 22))
    _capsule(layer, skeleton['shoulder_left_anchor'], skeleton['hand_left_anchor'], 10, color)
    _capsule(layer, skeleton['shoulder_right_anchor'], skeleton['hand_right_anchor'], 10, color)
    _capsule(layer, skeleton['hip_anchor'], skeleton['foot_left_anchor'], 12, color)
    _capsule(layer, skeleton['hip_anchor'], skeleton['foot_right_anchor'], 12, color)


def _warrior_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    head = skeleton['head_anchor']
    torso = skeleton['torso_anchor']
    sl = skeleton['shoulder_left_anchor']
    sr = skeleton['shoulder_right_anchor']
    hip = skeleton['hip_anchor']
    fl = skeleton['foot_left_anchor']
    fr = skeleton['foot_right_anchor']
    chest = [
        (sl[0] - 10, sl[1]),
        (sr[0] + 10, sr[1]),
        (torso[0] + 16, torso[1] + 18),
        (hip[0] + 10, hip[1] + 10),
        (hip[0] - 10, hip[1] + 10),
        (torso[0] - 16, torso[1] + 18),
    ]
    _poly(layer, color, chest)
    hip_plate = [
        (hip[0] - 18, hip[1] + 6),
        (hip[0] + 18, hip[1] + 6),
        (fr[0] - 6, fr[1] - 10),
        (fl[0] + 6, fl[1] - 10),
    ]
    _poly(layer, color, hip_plate)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - 12), int(head[1] - 12), 24, 24))
    _capsule(layer, sl, skeleton['hand_left_anchor'], 12, color)
    _capsule(layer, sr, skeleton['hand_right_anchor'], 13, color)
    _capsule(layer, hip, fl, 13, color)
    _capsule(layer, hip, fr, 13, color)


def _mage_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    head = skeleton['head_anchor']
    sl = skeleton['shoulder_left_anchor']
    sr = skeleton['shoulder_right_anchor']
    hip = skeleton['hip_anchor']
    fl = skeleton['foot_left_anchor']
    fr = skeleton['foot_right_anchor']
    robe = [
        (sl[0] - 6, sl[1]),
        (head[0], head[1] - 8),
        (sr[0] + 6, sr[1]),
        (hip[0] + 18, hip[1] + 12),
        (fr[0] + 6, fr[1]),
        (fl[0] - 6, fl[1]),
        (hip[0] - 18, hip[1] + 12),
    ]
    _poly(layer, color, robe)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - 10), int(head[1] - 12), 20, 22))
    _capsule(layer, sl, skeleton['hand_left_anchor'], 9, color)
    _capsule(layer, sr, skeleton['hand_right_anchor'], 9, color)
    _capsule(layer, hip, fl, 10, color)
    _capsule(layer, hip, fr, 10, color)


def resolve_character_silhouette(size: tuple[int, int], skeleton: dict[str, object], archetype: str, color) -> pygame.Surface:
    layer = pygame.Surface(size, pygame.SRCALPHA)
    if archetype == 'archon':
        _archon_body(layer, skeleton, color)
    elif archetype == 'guide_mage':
        _mage_body(layer, skeleton, color)
    else:
        _warrior_body(layer, skeleton, color)
    # Keep the hand/weapon bridge continuous without merging the whole weapon into subject mass.
    _capsule(layer, skeleton['hand_right_anchor'], skeleton['weapon_origin_anchor'], max(4, int(skeleton['scale'] * 0.06)), color)
    clean = _smooth_mask(layer)
    return _clear_strays(clean)
