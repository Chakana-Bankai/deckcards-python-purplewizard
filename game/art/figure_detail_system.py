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


def _pt(point) -> tuple[int, int]:
    return (int(point[0]), int(point[1]))


def render_structure_pass(target: pygame.Surface, skeleton: dict[str, object], archetype: str, palette, tones, shape_profile):
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
    lkn = _pt(skeleton['left_knee_anchor'])
    rkn = _pt(skeleton['right_knee_anchor'])

    plane = tones['cloth'][:3]
    bright = tones['trim'][:3]
    dark = tones['shadow'][:3]
    seam_w = max(2, rect.width // 34)

    collar = [(head[0] - rect.width // 18, head[1] + rect.height // 18), (head[0] + rect.width // 18, head[1] + rect.height // 18), (torso[0] + rect.width // 10, torso[1] - rect.height // 28), (torso[0] - rect.width // 10, torso[1] - rect.height // 28)]
    pygame.draw.polygon(target, (*bright, 78), collar)

    if archetype == 'archon':
        left_plane = [(sl[0] - rect.width // 12, sl[1] + rect.height // 40), (torso[0] - rect.width // 10, torso[1] + rect.height // 22), (pelvis[0] - rect.width // 10, pelvis[1] + rect.height // 18), (pelvis[0] - rect.width // 7, pelvis[1] + rect.height // 5)]
        right_plane = [(sr[0] + rect.width // 16, sr[1] + rect.height // 40), (torso[0] + rect.width // 11, torso[1] + rect.height // 22), (pelvis[0] + rect.width // 10, pelvis[1] + rect.height // 18), (pelvis[0] + rect.width // 8, pelvis[1] + rect.height // 5)]
        waist = pygame.Rect(int(torso[0] - rect.width * 0.12), int(pelvis[1] - rect.height * 0.02), int(rect.width * 0.24), int(rect.height * 0.06))
        pygame.draw.polygon(target, (*plane, 82), left_plane)
        pygame.draw.polygon(target, (*plane, 70), right_plane)
        pygame.draw.rect(target, (*bright, 84), waist, border_radius=max(3, int(rect.width // (34 - float(shape_profile.get('angularity', 0.5)) * 8))))
    elif archetype == 'guide_mage':
        shawl = [(sl[0] - rect.width // 16, sl[1] + rect.height // 36), (torso[0] - rect.width // 14, torso[1] + rect.height // 12), (torso[0] + rect.width // 9, torso[1] + rect.height // 10), (sr[0] + rect.width // 16, sr[1] + rect.height // 36), (torso[0] + rect.width // 13, torso[1] + rect.height // 4), (torso[0] - rect.width // 10, torso[1] + rect.height // 4)]
        skirt_left = [(torso[0] - rect.width // 14, torso[1] + rect.height // 4), (pelvis[0] - rect.width // 10, pelvis[1]), (lkn[0] - rect.width // 18, lkn[1] + rect.height // 18)]
        skirt_right = [(torso[0] + rect.width // 14, torso[1] + rect.height // 4), (pelvis[0] + rect.width // 10, pelvis[1]), (rkn[0] + rect.width // 18, rkn[1] + rect.height // 18)]
        cuff = pygame.Rect(int(rel[0] - rect.width * 0.04), int(rel[1] - rect.height * 0.02), int(rect.width * 0.08), int(rect.height * 0.05))
        pygame.draw.polygon(target, (*plane, 78), shawl)
        pygame.draw.polygon(target, (*bright, 70), skirt_left)
        pygame.draw.polygon(target, (*bright, 70), skirt_right)
        pygame.draw.rect(target, (*bright, 92), cuff, border_radius=max(4, int(rect.width // (38 - float(shape_profile.get('curve_bias', 0.5)) * 10))))
    else:
        chest = [(sl[0] - rect.width // 18, sl[1] + rect.height // 32), (torso[0] - rect.width // 10, torso[1] + rect.height // 18), (torso[0] + rect.width // 8, torso[1] + rect.height // 20), (sr[0] + rect.width // 16, sr[1] + rect.height // 28), (torso[0] + rect.width // 12, torso[1] + rect.height // 4), (torso[0] - rect.width // 14, torso[1] + rect.height // 4)]
        pelvis_plate = pygame.Rect(int(pelvis[0] - rect.width * 0.12), int(pelvis[1] - rect.height * 0.03), int(rect.width * 0.24), int(rect.height * 0.08))
        pygame.draw.polygon(target, (*plane, 76), chest)
        pygame.draw.rect(target, (*bright, 88), pelvis_plate, border_radius=max(3, int(rect.width // (32 - float(shape_profile.get('angularity', 0.5)) * 8))))

    pygame.draw.line(target, (*dark, 88), (torso[0], torso[1] - rect.height // 24), (pelvis[0], pelvis[1] + rect.height // 10), seam_w)
    pygame.draw.line(target, (*dark, 74), lel, lha, max(2, seam_w - 1))
    pygame.draw.line(target, (*dark, 84), rel, rha, seam_w)
