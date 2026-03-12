from __future__ import annotations

import random

import pygame

from game.art.body_volume_builder import build_body_volumes
from game.art.figure_skeleton_builder import build_figure_skeleton
from game.art.figure_detail_system import render_structure_pass
from game.art.costume_detail_pass import render_costume_detail_pass
from game.art.silhouette_merger import merge_body_volumes
from game.art.weapon_templates import resolve_weapon_template
from game.art.weapon_pose_resolver import bind_weapon_pose
from game.art.shape_language_profile import resolve_shape_language
from game.art.material_tone_system import build_material_tones


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


def _attenuate_central_subject_detail(target: pygame.Surface, skeleton: dict[str, object], archetype: str):
    if archetype not in {'archon', 'guide_mage'}:
        return
    rect: pygame.Rect = skeleton['rect']
    corridor = pygame.Rect(
        int(rect.centerx - rect.width * 0.08),
        int(rect.top + rect.height * 0.05),
        int(max(12, rect.width * 0.16)),
        int(rect.height * 0.58),
    ).clip(target.get_rect())
    for y in range(corridor.top, corridor.bottom):
        for x in range(corridor.left, corridor.right):
            c = target.get_at((x, y))
            if c.a <= 12:
                continue
            dx = abs(x - rect.centerx) / max(1.0, corridor.width / 2.0)
            factor = 0.42 + min(0.38, dx * 0.32)
            target.set_at((x, y), (int(c.r * factor), int(c.g * factor), int(c.b * factor), int(c.a * 0.72)))


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


def _clear_weapon_from_subject_core(back_target: pygame.Surface, front_target: pygame.Surface, subject_mask: pygame.Surface, skeleton: dict[str, object], family: str):
    if family not in {'staff', 'orb', 'spear'}:
        return
    rect: pygame.Rect = skeleton['rect']
    core: pygame.Rect = skeleton.get('subject_core_rect', rect.inflate(-max(8, rect.width // 3), -max(8, rect.height // 3))).clip(subject_mask.get_rect())
    head_guard = pygame.Rect(rect.left + rect.width // 5, rect.top, rect.width * 3 // 5, max(12, rect.height // 4)).clip(subject_mask.get_rect())
    keep_grip: pygame.Rect = skeleton.get('weapon_grip_rect', pygame.Rect(0, 0, 0, 0)).inflate(max(6, rect.width // 18), max(6, rect.height // 18)).clip(subject_mask.get_rect())
    clearance = core.union(head_guard).inflate(max(8, rect.width // 16), max(8, rect.height // 18)).clip(subject_mask.get_rect())

    def scrub(surface: pygame.Surface, fade_only: bool):
        for y in range(clearance.top, clearance.bottom):
            for x in range(clearance.left, clearance.right):
                if keep_grip.collidepoint(x, y):
                    continue
                if surface.get_at((x, y)).a <= 8:
                    continue
                if subject_mask.get_at((x, y)).a <= 12 and not head_guard.collidepoint(x, y):
                    continue
                c = surface.get_at((x, y))
                if fade_only:
                    surface.set_at((x, y), (int(c.r * 0.72), int(c.g * 0.72), int(c.b * 0.72), int(c.a * 0.44)))
                else:
                    surface.set_at((x, y), (0, 0, 0, 0))

    scrub(front_target, False)
    scrub(back_target, True)

def _render_subject_detail(target: pygame.Surface, skeleton: dict[str, object], archetype: str, palette, tones):
    rect: pygame.Rect = skeleton['rect']
    head = _pt(skeleton['head_anchor'])
    torso = _pt(skeleton['torso_anchor'])
    pelvis = _pt(skeleton['pelvis_anchor'])
    sl = _pt(skeleton['left_shoulder_anchor'])
    sr = _pt(skeleton['right_shoulder_anchor'])
    lel = _pt(skeleton['left_elbow_anchor'])
    rel = _pt(skeleton['right_elbow_anchor'])
    lha = _pt(skeleton['left_hand_anchor'])
    rha = _pt(skeleton['right_hand_anchor'])
    low = tones['cloth_dark'][:3]
    mid = tones['cloth'][:3]
    accent = tones['trim'][:3]
    shade = tones['shadow'][:3]

    if archetype == 'archon':
        left_fold = [(sl[0] - rect.width // 18, sl[1] + rect.height // 40), (torso[0] - rect.width // 10, torso[1] + rect.height // 24), (pelvis[0] - rect.width // 9, pelvis[1] + rect.height // 12), (pelvis[0] - rect.width // 5, pelvis[1] + rect.height // 5)]
        right_fold = [(sr[0] + rect.width // 18, sr[1] + rect.height // 40), (torso[0] + rect.width // 10, torso[1] + rect.height // 24), (pelvis[0] + rect.width // 9, pelvis[1] + rect.height // 12), (pelvis[0] + rect.width // 5, pelvis[1] + rect.height // 5)]
        chest_rune = pygame.Rect(int(torso[0] - rect.width * 0.045), int(torso[1] - rect.height * 0.02), int(rect.width * 0.09), int(rect.height * 0.10))
        pygame.draw.polygon(target, (*mid, 170), left_fold)
        pygame.draw.polygon(target, (*mid, 170), right_fold)
        chest_left_band = [(sl[0] - rect.width // 12, sl[1] + rect.height // 28), (torso[0] - rect.width // 9, torso[1] + rect.height // 28), (torso[0] - rect.width // 12, torso[1] + rect.height // 5), (pelvis[0] - rect.width // 10, pelvis[1] + rect.height // 14)]
        chest_right_band = [(sr[0] + rect.width // 18, sr[1] + rect.height // 28), (torso[0] + rect.width // 8, torso[1] + rect.height // 28), (torso[0] + rect.width // 10, torso[1] + rect.height // 5), (pelvis[0] + rect.width // 11, pelvis[1] + rect.height // 14)]
        pygame.draw.ellipse(target, (*accent, 120), chest_rune)
        pygame.draw.polygon(target, (*accent, 86), chest_left_band)
        pygame.draw.polygon(target, (*accent, 76), chest_right_band)
        pygame.draw.line(target, (*shade, 135), _pt((torso[0] - rect.width * 0.18, torso[1] + rect.height * 0.10)), _pt((pelvis[0] - rect.width * 0.06, pelvis[1] + rect.height * 0.24)), max(2, rect.width // 40))
        pygame.draw.line(target, (*shade, 135), _pt((torso[0] + rect.width * 0.18, torso[1] + rect.height * 0.10)), _pt((pelvis[0] + rect.width * 0.06, pelvis[1] + rect.height * 0.24)), max(2, rect.width // 40))
        pygame.draw.line(target, (*accent, 118), rel, rha, max(3, rect.width // 30))
    elif archetype == 'guide_mage':
        mantle_left = [(sl[0], sl[1] + rect.height // 36), (torso[0] - rect.width // 10, torso[1] + rect.height // 18), (pelvis[0] - rect.width // 8, pelvis[1] + rect.height // 7)]
        mantle_right = [(sr[0], sr[1] + rect.height // 36), (torso[0] + rect.width // 10, torso[1] + rect.height // 18), (pelvis[0] + rect.width // 8, pelvis[1] + rect.height // 7)]
        side_band = pygame.Rect(int(rect.centerx + rect.width * 0.04), int(torso[1] + rect.height * 0.05), int(rect.width * 0.07), int(rect.height * 0.24))
        orb_ring = pygame.Rect(int(head[0] - rect.width * 0.07), int(head[1] + rect.height * 0.04), int(rect.width * 0.14), int(rect.width * 0.14))
        arm_sash = [(sr[0], sr[1] + rect.height // 32), (rel[0] + rect.width // 26, rel[1] + rect.height // 20), (rha[0] + rect.width // 24, rha[1]), (torso[0] + rect.width // 10, torso[1] + rect.height // 8)]
        chest_band = [(sl[0] - rect.width // 14, sl[1] + rect.height // 24), (torso[0] - rect.width // 10, torso[1] + rect.height // 14), (torso[0] + rect.width // 9, torso[1] + rect.height // 10), (sr[0] + rect.width // 16, sr[1] + rect.height // 24)]
        pygame.draw.polygon(target, (*mid, 165), mantle_left)
        pygame.draw.polygon(target, (*mid, 165), mantle_right)
        pygame.draw.polygon(target, (*accent, 78), chest_band)
        pygame.draw.polygon(target, (*accent, 88), arm_sash)
        pygame.draw.rect(target, (*accent, 110), side_band, border_radius=max(4, rect.width // 30))
        pygame.draw.ellipse(target, (*accent, 92), orb_ring, 2)
        pygame.draw.line(target, (*accent, 120), rel, rha, max(3, rect.width // 32))
    else:
        left_plate = [(sl[0] - rect.width // 20, sl[1]), (torso[0] - rect.width // 13, torso[1] + rect.height // 18), (pelvis[0] - rect.width // 11, pelvis[1] + rect.height // 20), (pelvis[0] - rect.width // 5, pelvis[1] + rect.height // 18)]
        right_plate = [(sr[0] + rect.width // 18, sr[1]), (torso[0] + rect.width // 12, torso[1] + rect.height // 18), (pelvis[0] + rect.width // 11, pelvis[1] + rect.height // 20), (pelvis[0] + rect.width // 5, pelvis[1] + rect.height // 18)]
        belt = pygame.Rect(int(rect.centerx - rect.width * 0.14), int(pelvis[1] - rect.height * 0.03), int(rect.width * 0.28), int(rect.height * 0.05))
        paul_l = pygame.Rect(sl[0] - rect.width // 12, sl[1] - rect.height // 24, rect.width // 7, rect.height // 11)
        paul_r = pygame.Rect(sr[0] - rect.width // 30, sr[1] - rect.height // 24, rect.width // 7, rect.height // 11)
        pygame.draw.polygon(target, (*mid, 172), left_plate)
        pygame.draw.polygon(target, (*mid, 172), right_plate)
        pygame.draw.rect(target, (*accent, 118), belt, border_radius=max(4, rect.width // 30))
        pygame.draw.ellipse(target, (*low, 170), paul_l)
        pygame.draw.ellipse(target, (*low, 170), paul_r)

    pygame.draw.line(target, (*shade, 120), lel, lha, max(2, rect.width // 44))
    pygame.draw.line(target, (*shade, 126), rel, rha, max(2, rect.width // 40))
    face = pygame.Rect(head[0] - rect.width // 18, head[1] - rect.height // 18, rect.width // 9, rect.height // 9)
    pygame.draw.ellipse(target, (*_mix(mid, accent, 0.28), 120), face)


def _weapon_tip(origin, rect: pygame.Rect, weapon: dict[str, object], orientation: str):
    length = rect.height * float(weapon.get('length', 0.80))
    if orientation == 'diagonal':
        return (origin[0] + length * 0.78, origin[1] - length * 0.52)
    if orientation == 'support':
        return (origin[0] + rect.width * 0.03, origin[1] - length * 0.88)
    return (origin[0], origin[1] - length)


def _render_weapon_layers(back_target: pygame.Surface, front_target: pygame.Surface, skeleton: dict[str, object], weapon: dict[str, object], palette, tones):
    rect: pygame.Rect = skeleton['rect']
    profile = skeleton.get('shape_profile', {})
    origin = skeleton['weapon_origin_anchor']
    bridge = skeleton.get('weapon_bridge_anchor', ((origin[0] + skeleton['right_hand_anchor'][0]) / 2.0, (origin[1] + skeleton['right_hand_anchor'][1]) / 2.0))
    tip = skeleton.get('weapon_tip_anchor', _weapon_tip(origin, rect, weapon, skeleton['weapon_orientation']))
    skeleton['weapon_tip_anchor'] = tip
    family = str(weapon.get('family', 'staff'))
    shaft = tones['wood'][:3] if family in {'staff', 'orb'} else tones['metal'][:3]
    bright = tones['glow'][:3] if family in {'staff', 'orb'} else tones['metal'][:3]
    dark = tones['shadow'][:3]
    width_scale = float(profile.get('weapon_thickness_scale', 1.0))
    icon_scale = float(profile.get('icon_scale', 1.0))
    width = max(4, int(rect.width * float(weapon.get('thickness', 0.11)) * width_scale))

    grip_width = max(3, width - 1)
    _capsule(front_target, skeleton['right_hand_anchor'], bridge, max(2, grip_width - 1), (*shaft, 235))
    _capsule(front_target, bridge, origin, grip_width, (*shaft, 255))
    grip_rect = pygame.Rect(min(skeleton['right_hand_anchor'][0], origin[0]) - grip_width, min(skeleton['right_hand_anchor'][1], origin[1]) - grip_width, abs(skeleton['right_hand_anchor'][0] - origin[0]) + grip_width * 2, abs(skeleton['right_hand_anchor'][1] - origin[1]) + grip_width * 2)
    skeleton['weapon_grip_rect'] = grip_rect

    if family == 'staff':
        lane_x = skeleton.get('weapon_lane_anchor', (rect.right, rect.centery))[0]
        shaft_mid = (lane_x, origin[1] - rect.height * 0.04)
        shaft_tip = (shaft_mid[0], origin[1] - rect.height * 0.22)
        _capsule(back_target, origin, shaft_mid, max(4, width), (*shaft, 236))
        _capsule(back_target, shaft_mid, shaft_tip, max(5, width + 1), (*shaft, 255))
        crown_radius = max(6, int(width * 0.95 * icon_scale))
        ring_rect = pygame.Rect(int(shaft_tip[0] - crown_radius), int(shaft_tip[1] - crown_radius * 0.85), int(crown_radius * 2.0), int(crown_radius * 1.7))
        pygame.draw.ellipse(back_target, (*bright, 220), ring_rect, max(2, width // 3))
        pygame.draw.circle(back_target, (*bright, 240), _pt((shaft_tip[0], shaft_tip[1] - crown_radius * 0.10)), max(5, width))
        left_fin = [_pt((shaft_tip[0] - crown_radius * 1.35, shaft_tip[1] - crown_radius * 0.10)), _pt((shaft_tip[0] - crown_radius * 0.48, shaft_tip[1] - crown_radius * 0.72)), _pt((shaft_tip[0] - crown_radius * 0.30, shaft_tip[1] + crown_radius * 0.58))]
        right_fin = [_pt((shaft_tip[0] + crown_radius * 1.35, shaft_tip[1] - crown_radius * 0.10)), _pt((shaft_tip[0] + crown_radius * 0.48, shaft_tip[1] - crown_radius * 0.72)), _pt((shaft_tip[0] + crown_radius * 0.30, shaft_tip[1] + crown_radius * 0.58))]
        outer_echo = pygame.Rect(int(shaft_tip[0] + crown_radius * 0.45), int(shaft_tip[1] - crown_radius * 0.55), int(crown_radius * 1.2), int(crown_radius * 0.7))
        pygame.draw.polygon(back_target, (*bright, 210), left_fin)
        pygame.draw.polygon(back_target, (*bright, 210), right_fin)
        pygame.draw.ellipse(back_target, (*bright, 185), outer_echo)
        banner = [_pt((shaft_mid[0] + width * 0.2, shaft_mid[1] - width * 0.2)), _pt((shaft_mid[0] + width * 1.2, shaft_mid[1] + width * 0.5)), _pt((shaft_mid[0] + width * 0.3, shaft_mid[1] + width * 1.3))]
        pygame.draw.polygon(back_target, (*dark, 170), banner)
        skeleton['weapon_tip_anchor'] = shaft_tip
    elif family == 'orb':
        lane_x = skeleton.get('weapon_lane_anchor', (rect.right, rect.centery))[0]
        support_top = (lane_x, origin[1] - rect.height * 0.04)
        orb_center = (support_top[0], support_top[1] - rect.height * 0.03)
        _capsule(back_target, origin, support_top, max(4, width - 1), (*dark, 244))
        cradle_left = (orb_center[0] - width * 1.2, orb_center[1] + width * 0.7)
        cradle_right = (orb_center[0] + width * 1.2, orb_center[1] + width * 0.7)
        pygame.draw.arc(back_target, (*shaft, 230), pygame.Rect(int(orb_center[0] - width * 1.7), int(orb_center[1] - width * 1.35), int(width * 3.4), int(width * 3.0)), 0.2, 2.94, max(2, width // 3))
        _capsule(back_target, support_top, cradle_left, max(3, width - 2), (*shaft, 255))
        _capsule(back_target, support_top, cradle_right, max(3, width - 2), (*shaft, 255))
        orb_radius = max(6, int(width * 1.0 * icon_scale))
        pygame.draw.circle(back_target, (*bright, 245), _pt(orb_center), orb_radius)
        pygame.draw.circle(back_target, (*dark, 255), _pt(orb_center), orb_radius, 2)
        halo_rect = pygame.Rect(int(orb_center[0] - width * 1.4), int(orb_center[1] - width * 1.2), int(width * 2.8), int(width * 2.4))
        pygame.draw.ellipse(back_target, (*bright, 90), halo_rect, max(2, width // 3))
        tail = [_pt((support_top[0] - width * 0.4, support_top[1] + width * 0.5)), _pt((support_top[0] + width * 1.0, support_top[1] + width * 1.4)), _pt((support_top[0], support_top[1] + width * 2.0))]
        outer_crescent = pygame.Rect(int(orb_center[0] + width * 1.3), int(orb_center[1] - width * 1.2), int(width * 2.6), int(width * 1.6))
        pygame.draw.polygon(back_target, (*dark, 165), tail)
        pygame.draw.arc(back_target, (*bright, 170), outer_crescent, 4.1, 1.9, max(2, width // 3))
        skeleton['weapon_tip_anchor'] = orb_center
    else:
        _capsule(back_target, origin, tip, width, (*shaft, 255))
        if family == 'spear':
            head = [_pt(tip), _pt((tip[0] - width * 2.1, tip[1] + width * 1.2)), _pt((tip[0], tip[1] + width * 3.6)), _pt((tip[0] + width * 1.2, tip[1] + width * 1.3))]
            wing = [_pt((tip[0] + width * 0.8, tip[1] + width * 0.4)), _pt((tip[0] + width * 3.0, tip[1] + width * 0.9)), _pt((tip[0] + width * 1.1, tip[1] + width * 1.9))]
            pygame.draw.polygon(back_target, (*bright, 250), head)
            pygame.draw.polygon(back_target, (*bright, 205), wing)
        elif family == 'sword':
            pygame.draw.line(back_target, (*bright, 255), _pt((origin[0] - width * 1.4, origin[1] - width)), _pt((origin[0] + width * 1.4, origin[1] - width)), max(2, width // 2))
            blade = [_pt((origin[0] - width * 0.4, origin[1])), _pt((origin[0] + width * 0.4, origin[1])), _pt((tip[0] + width * 0.18, tip[1] + width * 0.8)), _pt((tip[0] - width * 0.18, tip[1] + width * 0.8))]
            pygame.draw.polygon(back_target, (*bright, 244), blade)


def compose_character_subject(surface_size: tuple[int, int], semantic: dict, palette, rng: random.Random) -> dict[str, object]:
    del rng
    skeleton = build_figure_skeleton(surface_size, semantic)
    skeleton['surface_size'] = surface_size
    skeleton['shape_profile'] = resolve_shape_language(str(skeleton['archetype']))
    template = skeleton['template']
    weapon = resolve_weapon_template(semantic, template)
    skeleton = bind_weapon_pose(skeleton, weapon)
    volumes = build_body_volumes(skeleton)
    tones = build_material_tones(palette, str(skeleton['archetype']), skeleton['shape_profile'])
    skeleton['material_tones'] = tones
    base_color = tones['cloth'][:3]
    silhouette, merge_metrics = merge_body_volumes(surface_size, volumes, str(skeleton['archetype']), (*base_color, 255))

    subject_mask = pygame.Surface(surface_size, pygame.SRCALPHA)
    subject_detail = pygame.Surface(surface_size, pygame.SRCALPHA)
    weapon_back_layer = pygame.Surface(surface_size, pygame.SRCALPHA)
    weapon_front_layer = pygame.Surface(surface_size, pygame.SRCALPHA)
    subject_mask.blit(silhouette, (0, 0))
    _blit_mask_tint(subject_mask, silhouette, base_color, 1.0)
    archetype = str(skeleton['archetype'])
    _render_subject_detail(subject_detail, skeleton, archetype, palette, tones)
    render_structure_pass(subject_detail, skeleton, archetype, palette, tones, skeleton['shape_profile'])
    render_costume_detail_pass(subject_detail, skeleton, archetype, palette, tones, skeleton['shape_profile'])
    _attenuate_central_subject_detail(subject_detail, skeleton, archetype)
    _render_weapon_layers(weapon_back_layer, weapon_front_layer, skeleton, weapon, palette, tones)
    _clear_weapon_from_subject_core(weapon_back_layer, weapon_front_layer, subject_mask, skeleton, str(weapon.get('family', 'staff')))

    subject_rect = subject_mask.get_bounding_rect(min_alpha=12)
    torso = skeleton['torso_anchor']
    core_w = max(18, int(subject_rect.width * 0.32))
    core_h = max(18, int(subject_rect.height * 0.28))
    subject_core_rect = pygame.Rect(int(torso[0] - core_w / 2), int(torso[1] - core_h * 0.10), core_w, core_h).clip(pygame.Rect((0, 0), surface_size))

    layout = dict(skeleton)
    layout.update(
        {
            'rect': subject_rect,
            'subject_core_rect': subject_core_rect,
            'pose_family': str(skeleton['pose_id']).lower(),
            'template_id': str(template.get('template_id', 'solar_warrior_base')),
            'weapon_template_id': str(weapon.get('weapon_id', 'staff')),
            'silhouette_integrity': float(merge_metrics['silhouette_integrity']),
            'limb_connection_score': float(merge_metrics['limb_connection_score']),
            'frontal_block_score': float(merge_metrics.get('frontal_block_score', 1.0)),
        }
    )

    return {
        'subject_mask': subject_mask,
        'subject_detail': subject_detail,
        'weapon_back_layer': weapon_back_layer,
        'weapon_front_layer': weapon_front_layer,
        'layout': layout,
        'template': template,
        'weapon': weapon,
    }

