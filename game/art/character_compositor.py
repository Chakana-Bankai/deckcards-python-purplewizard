from __future__ import annotations

import random

import pygame

from game.art.character_templates import resolve_character_template
from game.art.pose_templates import resolve_pose_template
from game.art.weapon_templates import resolve_weapon_template
from game.art.silhouette_resolver import resolve_character_silhouette


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = _clamp(ratio, 0.0, 1.0)
    return (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )


def _pt(point) -> tuple[int, int]:
    return (int(point[0]), int(point[1]))


def _capsule(surface: pygame.Surface, a, b, width: int, color):
    pa = _pt(a)
    pb = _pt(b)
    width = max(1, int(width))
    pygame.draw.line(surface, color, pa, pb, width)
    pygame.draw.circle(surface, color, pa, max(1, width // 2))
    pygame.draw.circle(surface, color, pb, max(1, width // 2))


def _blit_mask_tint(target: pygame.Surface, mask_surface: pygame.Surface, color, alpha_scale: float = 1.0):
    bounds = mask_surface.get_bounding_rect(min_alpha=12)
    if bounds.width <= 0 or bounds.height <= 0:
        return
    alpha_scale = _clamp(alpha_scale, 0.0, 1.0)
    for y in range(bounds.top, bounds.bottom):
        for x in range(bounds.left, bounds.right):
            a = mask_surface.get_at((x, y)).a
            if a <= 12:
                continue
            target.set_at((x, y), (color[0], color[1], color[2], int(min(255, a * alpha_scale))))


def _subject_center_shift(semantic: dict) -> float:
    try:
        return float(semantic.get('subject_center_shift', 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _subject_scale_boost(semantic: dict) -> float:
    try:
        return float(semantic.get('subject_scale_boost', 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _build_skeleton(size: tuple[int, int], template: dict[str, object], pose: dict[str, object], semantic: dict) -> tuple[dict[str, object], pygame.Rect]:
    width, height = size
    width_ratio = float(template.get('width_ratio', 0.56)) + _subject_scale_boost(semantic) * 0.65
    height_ratio = float(template.get('height_ratio', 0.60)) + _subject_scale_boost(semantic) * 0.40
    width_ratio = _clamp(width_ratio, 0.58, 0.76)
    height_ratio = _clamp(height_ratio, 0.64, 0.80)

    rect = pygame.Rect(0, 0, int(width * width_ratio), int(height * height_ratio))
    center_x = int(width * (0.50 + _subject_center_shift(semantic)))
    center_y = int(height * 0.56)
    rect.center = (center_x, center_y)
    rect.clamp_ip(pygame.Rect(0, 0, width, height))

    cx = rect.centerx
    top = rect.top
    left = rect.left
    right = rect.right

    def rel(point):
        return (rect.left + rect.width * point[0], rect.top + rect.height * point[1])

    head = (cx, top + rect.height * 0.11)
    torso = (cx, top + rect.height * 0.35)
    hip = rel((0.50 + pose['hip_offset'][0], pose['hip_offset'][1]))
    shoulder_left = rel((0.50 + pose['shoulder_left_offset'][0], pose['shoulder_left_offset'][1]))
    shoulder_right = rel((0.50 + pose['shoulder_right_offset'][0], pose['shoulder_right_offset'][1]))
    hand_left = rel((0.50 + pose['hand_left_offset'][0], pose['hand_left_offset'][1]))
    hand_right = rel((0.50 + pose['hand_right_offset'][0], pose['hand_right_offset'][1]))
    foot_left = rel((0.50 + pose['foot_left_offset'][0], pose['foot_left_offset'][1]))
    foot_right = rel((0.50 + pose['foot_right_offset'][0], pose['foot_right_offset'][1]))

    weapon_origin = (hand_right[0] + rect.width * 0.025, hand_right[1] - rect.height * 0.01)
    symbol_center = (cx, top + rect.height * 0.08)
    halo_anchor = (cx, top + rect.height * 0.14)
    fx_spawn = (cx, top + rect.height * 0.24)
    back_anchor = (cx - rect.width * 0.10, torso[1] + rect.height * 0.02)

    skeleton = {
        'rect': rect,
        'scale': rect.height,
        'head_anchor': head,
        'torso_anchor': torso,
        'shoulder_left_anchor': shoulder_left,
        'shoulder_right_anchor': shoulder_right,
        'hip_anchor': hip,
        'hand_left_anchor': hand_left,
        'hand_right_anchor': hand_right,
        'foot_left_anchor': foot_left,
        'foot_right_anchor': foot_right,
        'left_hand_anchor': hand_left,
        'right_hand_anchor': hand_right,
        'back_anchor': back_anchor,
        'weapon_origin_anchor': weapon_origin,
        'symbol_center_anchor': symbol_center,
        'halo_anchor': halo_anchor,
        'fx_spawn_anchor': fx_spawn,
    }
    return skeleton, rect


def _weapon_tip(origin, rect: pygame.Rect, weapon: dict[str, object], orientation: str) -> tuple[float, float]:
    length = rect.height * float(weapon.get('length', 0.50))
    if orientation == 'diagonal':
        return (origin[0] + length * 0.82, origin[1] - length * 0.56)
    if orientation == 'defensive':
        return (origin[0] + length * 0.36, origin[1] - length * 0.40)
    return (origin[0], origin[1] - length)


def _render_subject_volume(target: pygame.Surface, skeleton: dict[str, object], archetype: str, color):
    rect: pygame.Rect = skeleton['rect']
    head = _pt(skeleton['head_anchor'])
    torso = _pt(skeleton['torso_anchor'])
    hip = _pt(skeleton['hip_anchor'])
    sl = _pt(skeleton['shoulder_left_anchor'])
    sr = _pt(skeleton['shoulder_right_anchor'])
    fl = _pt(skeleton['foot_left_anchor'])
    fr = _pt(skeleton['foot_right_anchor'])

    if archetype == 'archon':
        mass = [
            (sl[0] - rect.width // 6, sl[1]),
            (head[0] - rect.width // 10, head[1] - rect.height // 14),
            (sr[0] + rect.width // 6, sr[1]),
            (hip[0] + rect.width // 4, hip[1] + rect.height // 8),
            (fr[0] + rect.width // 12, fr[1]),
            (fl[0] - rect.width // 12, fl[1]),
            (hip[0] - rect.width // 4, hip[1] + rect.height // 8),
        ]
    elif archetype == 'guide_mage':
        mass = [
            (sl[0] - rect.width // 7, sl[1]),
            (head[0], head[1] - rect.height // 12),
            (sr[0] + rect.width // 7, sr[1]),
            (hip[0] + rect.width // 4, hip[1] + rect.height // 8),
            (fr[0] + rect.width // 14, fr[1]),
            (fl[0] - rect.width // 14, fl[1]),
            (hip[0] - rect.width // 4, hip[1] + rect.height // 8),
        ]
    else:
        mass = [
            (sl[0] - rect.width // 7, sl[1] - rect.height // 40),
            (sr[0] + rect.width // 7, sr[1] - rect.height // 40),
            (torso[0] + rect.width // 4, torso[1] + rect.height // 6),
            (hip[0] + rect.width // 4, hip[1] + rect.height // 8),
            (fr[0] + rect.width // 18, fr[1]),
            (fl[0] - rect.width // 18, fl[1]),
            (hip[0] - rect.width // 4, hip[1] + rect.height // 8),
            (torso[0] - rect.width // 4, torso[1] + rect.height // 6),
        ]
    pygame.draw.polygon(target, (*color, 255), mass)
    pygame.draw.ellipse(target, (*color, 255), pygame.Rect(head[0] - rect.width // 14, head[1] - rect.height // 16, rect.width // 7, rect.height // 8))


def _render_subject_detail(target: pygame.Surface, skeleton: dict[str, object], archetype: str, palette):
    rect: pygame.Rect = skeleton['rect']
    low = _mix(palette[2], palette[0], 0.30)
    mid = _mix(palette[1], palette[3], 0.18)
    accent = _mix(palette[3], (255, 255, 255), 0.12)

    torso = _pt(skeleton['torso_anchor'])
    hip = _pt(skeleton['hip_anchor'])
    head = _pt(skeleton['head_anchor'])
    sl = _pt(skeleton['shoulder_left_anchor'])
    sr = _pt(skeleton['shoulder_right_anchor'])

    if archetype == 'archon':
        chest = [
            (sl[0] + 8, sl[1] + 2),
            (sr[0] - 8, sr[1] + 2),
            (torso[0] + rect.width // 11, torso[1] + rect.height // 10),
            (hip[0] + rect.width // 12, hip[1] + rect.height // 14),
            (hip[0] - rect.width // 12, hip[1] + rect.height // 14),
            (torso[0] - rect.width // 11, torso[1] + rect.height // 10),
        ]
        pygame.draw.polygon(target, (*mid, 210), chest)
        robe = pygame.Rect(int(rect.centerx - rect.width * 0.10), int(torso[1]), int(rect.width * 0.20), int(rect.height * 0.48))
        pygame.draw.rect(target, (*accent, 180), robe, border_radius=max(6, rect.width // 18))
        crown = pygame.Rect(head[0] - rect.width // 18, head[1] - rect.height // 12, rect.width // 9, rect.height // 14)
        pygame.draw.ellipse(target, (*accent, 170), crown)
    elif archetype == 'guide_mage':
        mantle = [
            (sl[0], sl[1] + 4),
            (sr[0], sr[1] + 4),
            (rect.centerx + rect.width // 8, torso[1] + rect.height // 5),
            (rect.centerx - rect.width // 8, torso[1] + rect.height // 5),
        ]
        pygame.draw.polygon(target, (*mid, 200), mantle)
        sash = pygame.Rect(int(rect.centerx - rect.width * 0.07), int(torso[1] + rect.height * 0.08), int(rect.width * 0.14), int(rect.height * 0.32))
        pygame.draw.rect(target, (*accent, 160), sash, border_radius=max(6, rect.width // 20))
        orb_glow = pygame.Rect(head[0] - rect.width // 10, head[1] + rect.height // 18, rect.width // 5, rect.width // 5)
        pygame.draw.ellipse(target, (*accent, 90), orb_glow, 2)
    else:
        armor = [
            (sl[0] - 4, sl[1]),
            (sr[0] + 4, sr[1]),
            (torso[0] + rect.width // 8, torso[1] + rect.height // 8),
            (hip[0] + rect.width // 14, hip[1]),
            (hip[0] - rect.width // 14, hip[1]),
            (torso[0] - rect.width // 8, torso[1] + rect.height // 8),
        ]
        pygame.draw.polygon(target, (*mid, 220), armor)
        belt = pygame.Rect(int(rect.centerx - rect.width * 0.14), int(hip[1] - rect.height * 0.03), int(rect.width * 0.28), int(rect.height * 0.06))
        pygame.draw.rect(target, (*accent, 160), belt, border_radius=max(4, rect.width // 28))
        pauldron_l = pygame.Rect(sl[0] - rect.width // 12, sl[1] - rect.height // 20, rect.width // 8, rect.height // 10)
        pauldron_r = pygame.Rect(sr[0] - rect.width // 24, sr[1] - rect.height // 20, rect.width // 8, rect.height // 10)
        pygame.draw.ellipse(target, (*low, 200), pauldron_l)
        pygame.draw.ellipse(target, (*low, 200), pauldron_r)

    face = pygame.Rect(head[0] - rect.width // 18, head[1] - rect.height // 18, rect.width // 9, rect.height // 10)
    pygame.draw.ellipse(target, (*_mix(mid, accent, 0.35), 150), face)


def _render_weapon(target: pygame.Surface, skeleton: dict[str, object], weapon: dict[str, object], palette, orientation: str):
    rect: pygame.Rect = skeleton['rect']
    origin = skeleton['weapon_origin_anchor']
    tip = _weapon_tip(origin, rect, weapon, orientation)
    skeleton['weapon_tip_anchor'] = tip

    shaft = _mix(palette[0], palette[2], 0.42)
    bright = _mix(palette[3], (255, 255, 255), 0.10)
    dark = _mix(palette[0], (0, 0, 0), 0.40)
    width = max(4, int(rect.width * float(weapon.get('thickness', 0.04))))
    family = str(weapon.get('family', 'staff'))

    if family in {'staff', 'spear', 'sword'}:
        _capsule(target, origin, tip, width, (*shaft, 255))
        if family == 'spear':
            head = [
                _pt(tip),
                _pt((tip[0] - width * 2.0, tip[1] + width * 1.2)),
                _pt((tip[0] - width * 0.6, tip[1] + width * 3.2)),
                _pt((tip[0] + width * 1.1, tip[1] + width * 1.4)),
            ]
            pygame.draw.polygon(target, (*bright, 255), head)
        elif family == 'sword':
            guard_y = origin[1] - width
            pygame.draw.line(target, (*bright, 255), _pt((origin[0] - width * 1.5, guard_y)), _pt((origin[0] + width * 1.5, guard_y)), max(2, width // 2))
            blade = [
                _pt((origin[0] - width * 0.55, origin[1])),
                _pt((origin[0] + width * 0.55, origin[1])),
                _pt((tip[0] + width * 0.25, tip[1] + width * 0.7)),
                _pt((tip[0] - width * 0.25, tip[1] + width * 0.7)),
            ]
            pygame.draw.polygon(target, (*bright, 240), blade)
        else:
            cap = pygame.Rect(int(tip[0] - width), int(tip[1] - width * 1.5), width * 2, width * 3)
            pygame.draw.ellipse(target, (*bright, 235), cap)
    else:
        orb_center = (tip[0], tip[1] + rect.height * 0.06)
        support = (origin[0], origin[1] - rect.height * 0.18)
        _capsule(target, origin, support, max(4, width - 1), (*dark, 255))
        pygame.draw.circle(target, (*bright, 245), _pt(orb_center), max(8, width * 2))
        pygame.draw.circle(target, (*dark, 255), _pt(orb_center), max(8, width * 2), 2)
        pygame.draw.circle(target, (*bright, 90), _pt(orb_center), max(12, width * 3), 2)
        skeleton['weapon_tip_anchor'] = orb_center


def compose_character_subject(surface_size: tuple[int, int], semantic: dict, palette, rng: random.Random) -> dict[str, object]:
    del rng
    template = resolve_character_template(semantic)
    pose = resolve_pose_template(semantic)
    weapon = resolve_weapon_template(semantic, template)
    skeleton, rect = _build_skeleton(surface_size, template, pose, semantic)
    skeleton['weapon_tip_anchor'] = _weapon_tip(skeleton['weapon_origin_anchor'], rect, weapon, str(pose.get('weapon_orientation', 'vertical')))

    subject_mask = pygame.Surface(surface_size, pygame.SRCALPHA)
    subject_detail = pygame.Surface(surface_size, pygame.SRCALPHA)
    object_layer = pygame.Surface(surface_size, pygame.SRCALPHA)

    base_color = _mix(palette[0], palette[1], 0.35)
    archetype = str(template.get('archetype', 'solar_warrior'))
    silhouette = resolve_character_silhouette(surface_size, skeleton, archetype, (*base_color, 255))
    subject_mask.blit(silhouette, (0, 0))
    _render_subject_volume(subject_mask, skeleton, archetype, base_color)
    _blit_mask_tint(subject_mask, silhouette, base_color, 1.0)
    _render_subject_detail(subject_detail, skeleton, archetype, palette)
    _render_weapon(object_layer, skeleton, weapon, palette, str(pose.get('weapon_orientation', 'vertical')))

    subject_rect = silhouette.get_bounding_rect(min_alpha=12)
    core_w = max(18, int(subject_rect.width * 0.34))
    core_h = max(18, int(subject_rect.height * 0.30))
    torso = skeleton['torso_anchor']
    subject_core_rect = pygame.Rect(int(torso[0] - core_w / 2), int(torso[1] - core_h * 0.18), core_w, core_h).clip(pygame.Rect((0, 0), surface_size))

    layout = dict(skeleton)
    layout.update(
        {
            'rect': subject_rect,
            'subject_core_rect': subject_core_rect,
            'pose_family': str(pose.get('pose_id', 'idle')),
            'template_id': str(template.get('template_id', 'solar_warrior_base')),
            'weapon_template_id': str(weapon.get('weapon_id', 'staff')),
        }
    )

    return {
        'subject_mask': subject_mask,
        'subject_detail': subject_detail,
        'object_layer': object_layer,
        'layout': layout,
        'template': template,
        'pose': pose,
        'weapon': weapon,
    }
