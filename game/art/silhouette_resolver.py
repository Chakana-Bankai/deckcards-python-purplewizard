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


def _dims(skeleton: dict[str, object]) -> tuple[pygame.Rect, int, int]:
    rect: pygame.Rect = skeleton['rect']
    unit_w = max(6, rect.width // 18)
    unit_h = max(6, rect.height // 18)
    return rect, unit_w, unit_h


def _archon_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    rect, uw, uh = _dims(skeleton)
    head = skeleton['head_anchor']
    shoulders = (skeleton['shoulder_left_anchor'], skeleton['shoulder_right_anchor'])
    hips = skeleton['hip_anchor']
    feet = (skeleton['foot_left_anchor'], skeleton['foot_right_anchor'])
    robe = [
        (shoulders[0][0] - uw * 2.2, shoulders[0][1] + uh * 0.4),
        (head[0] - uw * 1.4, head[1] + uh * 0.5),
        (shoulders[1][0] + uw * 2.2, shoulders[1][1] + uh * 0.4),
        (hips[0] + uw * 2.8, hips[1] + uh * 2.3),
        (feet[1][0] + uw * 1.8, feet[1][1]),
        (feet[0][0] - uw * 1.8, feet[0][1]),
        (hips[0] - uw * 2.8, hips[1] + uh * 2.3),
    ]
    _poly(layer, color, robe)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - uw * 1.6), int(head[1] - uh * 2.0), int(uw * 3.2), int(uh * 3.8)))
    _capsule(layer, skeleton['shoulder_left_anchor'], skeleton['hand_left_anchor'], uw * 2.0, color)
    _capsule(layer, skeleton['shoulder_right_anchor'], skeleton['hand_right_anchor'], uw * 2.0, color)
    _capsule(layer, skeleton['hip_anchor'], skeleton['foot_left_anchor'], uw * 2.2, color)
    _capsule(layer, skeleton['hip_anchor'], skeleton['foot_right_anchor'], uw * 2.2, color)


def _warrior_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    rect, uw, uh = _dims(skeleton)
    head = skeleton['head_anchor']
    torso = skeleton['torso_anchor']
    sl = skeleton['shoulder_left_anchor']
    sr = skeleton['shoulder_right_anchor']
    hip = skeleton['hip_anchor']
    fl = skeleton['foot_left_anchor']
    fr = skeleton['foot_right_anchor']
    chest = [
        (sl[0] - uw * 2.2, sl[1] - uh * 0.2),
        (sr[0] + uw * 2.2, sr[1] - uh * 0.2),
        (torso[0] + uw * 3.0, torso[1] + uh * 2.4),
        (hip[0] + uw * 2.4, hip[1] + uh * 1.3),
        (hip[0] - uw * 2.4, hip[1] + uh * 1.3),
        (torso[0] - uw * 3.0, torso[1] + uh * 2.4),
    ]
    _poly(layer, color, chest)
    hip_plate = [
        (hip[0] - uw * 3.0, hip[1] + uh * 1.0),
        (hip[0] + uw * 3.0, hip[1] + uh * 1.0),
        (fr[0] - uw * 1.0, fr[1] - uh * 1.6),
        (fl[0] + uw * 1.0, fl[1] - uh * 1.6),
    ]
    _poly(layer, color, hip_plate)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - uw * 2.1), int(head[1] - uh * 2.1), int(uw * 4.2), int(uh * 4.2)))
    _capsule(layer, sl, skeleton['hand_left_anchor'], uw * 2.4, color)
    _capsule(layer, sr, skeleton['hand_right_anchor'], uw * 2.5, color)
    _capsule(layer, hip, fl, uw * 2.6, color)
    _capsule(layer, hip, fr, uw * 2.6, color)


def _mage_body(layer: pygame.Surface, skeleton: dict[str, object], color):
    rect, uw, uh = _dims(skeleton)
    head = skeleton['head_anchor']
    sl = skeleton['shoulder_left_anchor']
    sr = skeleton['shoulder_right_anchor']
    hip = skeleton['hip_anchor']
    fl = skeleton['foot_left_anchor']
    fr = skeleton['foot_right_anchor']
    robe = [
        (sl[0] - uw * 1.6, sl[1]),
        (head[0], head[1] - uh * 1.4),
        (sr[0] + uw * 1.6, sr[1]),
        (hip[0] + uw * 3.0, hip[1] + uh * 2.0),
        (fr[0] + uw * 1.3, fr[1]),
        (fl[0] - uw * 1.3, fl[1]),
        (hip[0] - uw * 3.0, hip[1] + uh * 2.0),
    ]
    _poly(layer, color, robe)
    pygame.draw.ellipse(layer, color, pygame.Rect(int(head[0] - uw * 1.8), int(head[1] - uh * 2.1), int(uw * 3.6), int(uh * 4.0)))
    _capsule(layer, sl, skeleton['hand_left_anchor'], uw * 1.8, color)
    _capsule(layer, sr, skeleton['hand_right_anchor'], uw * 1.8, color)
    _capsule(layer, hip, fl, uw * 2.0, color)
    _capsule(layer, hip, fr, uw * 2.0, color)


def resolve_character_silhouette(size: tuple[int, int], skeleton: dict[str, object], archetype: str, color) -> pygame.Surface:
    layer = pygame.Surface(size, pygame.SRCALPHA)
    if archetype == 'archon':
        _archon_body(layer, skeleton, color)
    elif archetype == 'guide_mage':
        _mage_body(layer, skeleton, color)
    else:
        _warrior_body(layer, skeleton, color)
    _capsule(layer, skeleton['hand_right_anchor'], skeleton['weapon_origin_anchor'], max(5, int(skeleton['scale'] * 0.08)), color)
    clean = _smooth_mask(layer)
    return _clear_strays(clean)
