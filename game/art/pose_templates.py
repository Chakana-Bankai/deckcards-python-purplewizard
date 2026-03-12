from __future__ import annotations

POSE_TEMPLATES = {
    "idle": {
        "pose_id": "idle",
        "hand_left_offset": (-0.10, 0.46),
        "hand_right_offset": (0.10, 0.46),
        "foot_left_offset": (-0.08, 0.98),
        "foot_right_offset": (0.08, 0.98),
        "shoulder_left_offset": (-0.16, 0.28),
        "shoulder_right_offset": (0.16, 0.28),
        "hip_offset": (0.0, 0.62),
        "weapon_orientation": "vertical",
    },
    "attack": {
        "pose_id": "attack",
        "hand_left_offset": (-0.14, 0.44),
        "hand_right_offset": (0.28, 0.42),
        "foot_left_offset": (-0.14, 0.98),
        "foot_right_offset": (0.06, 0.96),
        "shoulder_left_offset": (-0.18, 0.30),
        "shoulder_right_offset": (0.18, 0.26),
        "hip_offset": (0.0, 0.62),
        "weapon_orientation": "diagonal",
    },
    "cast": {
        "pose_id": "cast",
        "hand_left_offset": (-0.10, 0.42),
        "hand_right_offset": (0.10, 0.42),
        "foot_left_offset": (-0.06, 0.98),
        "foot_right_offset": (0.06, 0.98),
        "shoulder_left_offset": (-0.14, 0.30),
        "shoulder_right_offset": (0.14, 0.30),
        "hip_offset": (0.0, 0.62),
        "weapon_orientation": "vertical",
    },
    "guard": {
        "pose_id": "guard",
        "hand_left_offset": (-0.18, 0.48),
        "hand_right_offset": (0.12, 0.50),
        "foot_left_offset": (-0.10, 0.98),
        "foot_right_offset": (0.10, 0.98),
        "shoulder_left_offset": (-0.18, 0.30),
        "shoulder_right_offset": (0.14, 0.30),
        "hip_offset": (0.0, 0.62),
        "weapon_orientation": "defensive",
    },
}


def resolve_pose_template(semantic: dict) -> dict[str, object]:
    text = ' '.join([str(semantic.get('subject_pose', '') or ''), str(semantic.get('pose_type', '') or ''), ' '.join(semantic.get('tags', []) or [])]).lower()
    if 'attack' in text:
        return dict(POSE_TEMPLATES['attack'])
    if 'cast' in text or 'ritual' in text or 'channel' in text:
        return dict(POSE_TEMPLATES['cast'])
    if 'guard' in text or 'defense' in text or 'guardian' in text:
        return dict(POSE_TEMPLATES['guard'])
    return dict(POSE_TEMPLATES['idle'])
