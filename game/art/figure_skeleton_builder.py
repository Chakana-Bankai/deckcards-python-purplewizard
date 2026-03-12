from __future__ import annotations

import pygame

from game.art.character_templates import resolve_character_template

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
        'left_shoulder': (0.36, 0.24),
        'right_shoulder': (0.64, 0.22),
        'left_elbow': (0.33, 0.42),
        'right_elbow': (0.71, 0.38),
        'left_hand': (0.31, 0.58),
        'right_hand': (0.78, 0.34),
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

JOINT_KEYS = {
    'HEAD': 'head_anchor',
    'NECK': 'neck_anchor',
    'LEFT_SHOULDER': 'left_shoulder_anchor',
    'RIGHT_SHOULDER': 'right_shoulder_anchor',
    'LEFT_ELBOW': 'left_elbow_anchor',
    'RIGHT_ELBOW': 'right_elbow_anchor',
    'LEFT_HAND': 'left_hand_anchor',
    'RIGHT_HAND': 'right_hand_anchor',
    'PELVIS': 'pelvis_anchor',
    'LEFT_KNEE': 'left_knee_anchor',
    'RIGHT_KNEE': 'right_knee_anchor',
    'LEFT_FOOT': 'left_foot_anchor',
    'RIGHT_FOOT': 'right_foot_anchor',
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
    scale_boost = float(semantic.get('subject_scale_boost', 0.0) or 0.0)
    width_ratio = _clamp(float(template.get('width_ratio', 0.62)) + scale_boost * 0.50, 0.56, 0.76)
    height_ratio = _clamp(float(template.get('height_ratio', 0.68)) + scale_boost * 0.35, 0.60, 0.80)
    rect = pygame.Rect(0, 0, int(width * width_ratio), int(height * height_ratio))
    center_shift = float(semantic.get('subject_center_shift', 0.0) or 0.0)
    rect.center = (int(width * (0.50 + center_shift)), int(height * 0.54))
    rect.clamp_ip(pygame.Rect(0, 0, width, height))
    return rect


def _rel(rect: pygame.Rect, point: tuple[float, float]) -> tuple[float, float]:
    return (rect.left + rect.width * point[0], rect.top + rect.height * point[1])


def build_figure_skeleton(size: tuple[int, int], semantic: dict) -> dict[str, object]:
    template = resolve_character_template(semantic)
    archetype = str(template.get('archetype', 'solar_warrior'))
    pose = _pose_from_semantic(semantic, archetype)
    rect = _subject_box(size, template, semantic)
    skeleton = {
        'rect': rect,
        'archetype': archetype,
        'pose_id': str(pose['pose_id']),
        'weapon_orientation': str(pose['weapon_orientation']),
        'head_size': max(12, int(rect.height * 0.12)),
        'template': template,
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
    skeleton['symbol_center_anchor'] = (rect.centerx, rect.top + rect.height * 0.07)
    skeleton['halo_anchor'] = (rect.centerx, rect.top + rect.height * 0.15)
    skeleton['fx_spawn_anchor'] = (rect.centerx, rect.top + rect.height * 0.24)
    if skeleton['weapon_orientation'] == 'diagonal':
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.03, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0] + rect.height * 0.58, skeleton['weapon_origin_anchor'][1] - rect.height * 0.36)
    elif skeleton['weapon_orientation'] == 'support':
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.06, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0] + rect.width * 0.02, skeleton['weapon_origin_anchor'][1] - rect.height * 0.30)
    else:
        skeleton['weapon_origin_anchor'] = (skeleton['right_hand_anchor'][0] + rect.width * 0.07, skeleton['right_hand_anchor'][1] - rect.height * 0.01)
        tip = (skeleton['weapon_origin_anchor'][0], skeleton['weapon_origin_anchor'][1] - rect.height * 0.38)
    skeleton['weapon_tip_anchor'] = tip
    return skeleton
