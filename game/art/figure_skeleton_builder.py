from __future__ import annotations

import pygame

from game.art.character_templates import resolve_character_template
from game.art.shape_grammar_registry import resolve_entity_shape_grammar, resolve_humanoid_subgrammar

POSE_PRESETS = {
    'ARCHON_RITUAL': {
        'pose_id': 'ARCHON_RITUAL',
        'weapon_orientation': 'vertical',
        'head': (0.46, 0.10),
        'neck': (0.47, 0.17),
        'left_shoulder': (0.39, 0.24),
        'right_shoulder': (0.61, 0.24),
        'left_elbow': (0.37, 0.40),
        'right_elbow': (0.56, 0.40),
        'left_hand': (0.36, 0.58),
        'right_hand': (0.55, 0.56),
        'pelvis': (0.50, 0.58),
        'left_knee': (0.44, 0.80),
        'right_knee': (0.56, 0.80),
        'left_foot': (0.43, 0.98),
        'right_foot': (0.57, 0.98),
    },
    'SOLAR_WARRIOR_ATTACK': {
        'pose_id': 'SOLAR_WARRIOR_ATTACK',
        'weapon_orientation': 'diagonal',
        'head': (0.49, 0.11),
        'neck': (0.49, 0.18),
        'left_shoulder': (0.34, 0.23),
        'right_shoulder': (0.66, 0.21),
        'left_elbow': (0.34, 0.40),
        'right_elbow': (0.69, 0.34),
        'left_hand': (0.33, 0.56),
        'right_hand': (0.72, 0.32),
        'pelvis': (0.49, 0.58),
        'left_knee': (0.39, 0.78),
        'right_knee': (0.57, 0.76),
        'left_foot': (0.34, 0.98),
        'right_foot': (0.61, 0.95),
    },
    'GUIDE_MAGE_CALM': {
        'pose_id': 'GUIDE_MAGE_CALM',
        'weapon_orientation': 'support',
        'head': (0.45, 0.10),
        'neck': (0.46, 0.17),
        'left_shoulder': (0.39, 0.25),
        'right_shoulder': (0.60, 0.25),
        'left_elbow': (0.37, 0.42),
        'right_elbow': (0.58, 0.42),
        'left_hand': (0.36, 0.61),
        'right_hand': (0.57, 0.57),
        'pelvis': (0.50, 0.58),
        'left_knee': (0.45, 0.80),
        'right_knee': (0.55, 0.80),
        'left_foot': (0.43, 0.98),
        'right_foot': (0.57, 0.98),
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pose_from_semantic(semantic: dict, archetype: str) -> dict[str, object]:
    text = ' '.join(
        [
            str(semantic.get('subject_pose', '') or ''),
            str(semantic.get('pose_type', '') or ''),
            str(semantic.get('object_kind', '') or ''),
            str(semantic.get('object', '') or ''),
            str(semantic.get('environment', '') or ''),
            ' '.join(semantic.get('tags', []) or []),
        ]
    ).lower()
    if archetype == 'archon' or 'ritual' in text or 'corruption' in text:
        return dict(POSE_PRESETS['ARCHON_RITUAL'])
    if archetype == 'guide_mage' or any(token in text for token in ('wisdom', 'support', 'chakana', 'calm', 'temple')):
        return dict(POSE_PRESETS['GUIDE_MAGE_CALM'])
    return dict(POSE_PRESETS['SOLAR_WARRIOR_ATTACK'])


def _subject_box(size: tuple[int, int], template: dict[str, object], semantic: dict) -> pygame.Rect:
    width, height = size
    safe_zone_ratio = float(semantic.get('safe_art_zone_ratio', 0.70) or 0.70)
    safe_zone_ratio = _clamp(safe_zone_ratio, 0.55, 0.82)
    safe_width = int(width * safe_zone_ratio)
    safe_height = int(height * safe_zone_ratio)
    safe_rect = pygame.Rect((width - safe_width) // 2, (height - safe_height) // 2, safe_width, safe_height)

    scale_boost = float(semantic.get('subject_scale_boost', 0.0) or 0.0)
    width_ratio = _clamp(float(template.get('width_ratio', 0.32)) + scale_boost * 0.08, 0.24, 0.35)
    height_ratio = _clamp(float(template.get('height_ratio', 0.42)) + scale_boost * 0.08, 0.32, 0.45)
    rect = pygame.Rect(0, 0, int(width * width_ratio), int(height * height_ratio))
    rect.width = min(rect.width, int(safe_rect.width * 0.92))
    rect.height = min(rect.height, int(safe_rect.height * 0.96))

    anchor_mode = str(semantic.get('subject_anchor_mode', 'center') or 'center').lower()
    center_shift = float(semantic.get('subject_center_shift', 0.0) or 0.0)
    anchor_x = int(safe_rect.centerx + safe_rect.width * 0.12 * center_shift)
    anchor_map = {
        'center': (anchor_x, int(safe_rect.centery)),
        'lower_center': (anchor_x, int(safe_rect.top + safe_rect.height * 0.60)),
        'golden_ratio': (anchor_x, int(safe_rect.top + safe_rect.height * 0.46)),
    }
    rect.center = anchor_map.get(anchor_mode, anchor_map['center'])
    rect.clamp_ip(safe_rect)
    return rect


def _rel(rect: pygame.Rect, point: tuple[float, float]) -> tuple[float, float]:
    return (rect.left + rect.width * point[0], rect.top + rect.height * point[1])


def build_figure_skeleton(size: tuple[int, int], semantic: dict) -> dict[str, object]:
    template = resolve_character_template(semantic)
    archetype = str(template.get('archetype', 'solar_warrior'))
    entity_grammar = resolve_entity_shape_grammar('HUMANOID')
    subgrammar = resolve_humanoid_subgrammar(archetype)
    pose = _pose_from_semantic(semantic, archetype)
    rect = _subject_box(size, template, semantic)
    subject_height = rect.height
    head_ratio = sum(entity_grammar['allowed_proportions']['head_ratio']) / 2.0
    shoulder_ratio = sum(entity_grammar['allowed_proportions']['shoulder_ratio']) / 2.0
    head_size = max(12, int(subject_height * head_ratio))
    head_width = max(10, int(head_size * 0.74))
    shoulder_span = max(head_width * 1.7, min(rect.width * 0.52, head_width * shoulder_ratio))

    skeleton = {
        'rect': rect,
        'archetype': archetype,
        'entity_type': 'HUMANOID',
        'pose_id': str(pose['pose_id']),
        'weapon_orientation': str(pose['weapon_orientation']),
        'head_size': head_size,
        'head_width': head_width,
        'shoulder_span': shoulder_span,
        'template': template,
        'entity_grammar': entity_grammar,
        'subgrammar': subgrammar,
    }
    skeleton['head_anchor'] = _rel(rect, pose['head'])
    skeleton['neck_anchor'] = _rel(rect, pose['neck'])
    skeleton['left_shoulder_anchor'] = _rel(rect, pose['left_shoulder'])
    skeleton['right_shoulder_anchor'] = _rel(rect, pose['right_shoulder'])
    skeleton['left_elbow_anchor'] = _rel(rect, pose['left_elbow'])
    skeleton['right_elbow_anchor'] = _rel(rect, pose['right_elbow'])
    skeleton['left_hand_anchor'] = _rel(rect, pose['left_hand'])
    skeleton['right_hand_anchor'] = _rel(rect, pose['right_hand'])
    skeleton['pelvis_anchor'] = _rel(rect, pose['pelvis'])
    skeleton['left_knee_anchor'] = _rel(rect, pose['left_knee'])
    skeleton['right_knee_anchor'] = _rel(rect, pose['right_knee'])
    skeleton['left_foot_anchor'] = _rel(rect, pose['left_foot'])
    skeleton['right_foot_anchor'] = _rel(rect, pose['right_foot'])
    skeleton['torso_anchor'] = ((skeleton['left_shoulder_anchor'][0] + skeleton['right_shoulder_anchor'][0]) / 2.0, rect.top + rect.height * 0.34)
    if archetype in {'archon', 'guide_mage'}:
        skeleton['torso_anchor'] = (skeleton['torso_anchor'][0] - rect.width * 0.03, skeleton['torso_anchor'][1])
    skeleton['hip_anchor'] = skeleton['pelvis_anchor']
    skeleton['shoulder_left_anchor'] = skeleton['left_shoulder_anchor']
    skeleton['shoulder_right_anchor'] = skeleton['right_shoulder_anchor']
    skeleton['hand_left_anchor'] = skeleton['left_hand_anchor']
    skeleton['hand_right_anchor'] = skeleton['right_hand_anchor']
    skeleton['foot_left_anchor'] = skeleton['left_foot_anchor']
    skeleton['foot_right_anchor'] = skeleton['right_foot_anchor']
    skeleton['back_anchor'] = (rect.centerx - rect.width * 0.10, rect.top + rect.height * 0.38)
    skeleton['symbol_center_anchor'] = (rect.centerx, rect.top + rect.height * 0.08)
    skeleton['halo_anchor'] = (rect.centerx, rect.top + rect.height * 0.15)
    skeleton['fx_spawn_anchor'] = (rect.centerx, rect.top + rect.height * 0.24)
    skeleton['center_anchor'] = rect.center
    skeleton['lower_center_anchor'] = (rect.centerx, int(rect.top + rect.height * 0.68))
    skeleton['golden_ratio_anchor'] = (rect.centerx, int(rect.top + rect.height * 0.38))
    if skeleton['weapon_orientation'] == 'diagonal':
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.01, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0] + rect.height * 0.52, skeleton['weapon_origin_anchor'][1] - rect.height * 0.32)
    elif skeleton['weapon_orientation'] == 'support':
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.06, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0] + rect.width * 0.02, skeleton['weapon_origin_anchor'][1] - rect.height * 0.30)
    else:
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.07, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0], skeleton['weapon_origin_anchor'][1] - rect.height * 0.38)
    skeleton['weapon_tip_anchor'] = tip
    skeleton['grammar_ratios'] = {
        'head_ratio': round(head_size / max(1, subject_height), 4),
        'torso_ratio': round((skeleton['pelvis_anchor'][1] - skeleton['neck_anchor'][1]) / max(1, subject_height), 4),
        'pelvis_ratio': round(head_size * 0.78 / max(1, subject_height), 4),
        'leg_ratio': round((skeleton['left_foot_anchor'][1] - skeleton['pelvis_anchor'][1]) / max(1, subject_height), 4),
        'arm_ratio': round((skeleton['right_hand_anchor'][1] - skeleton['right_shoulder_anchor'][1]) / max(1, subject_height), 4),
        'shoulder_ratio': round(shoulder_span / max(1, head_width), 4),
    }
    return skeleton
