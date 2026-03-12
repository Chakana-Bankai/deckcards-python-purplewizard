from __future__ import annotations

from game.art.symbolic_geometry import add_symbolic_robe_notch, add_symbolic_shoulder_cut


def build_body_volumes(skeleton: dict[str, object]) -> list[dict[str, object]]:
    rect = skeleton['rect']
    archetype = str(skeleton['archetype'])
    head_size = int(skeleton['head_size'])
    sl = skeleton['left_shoulder_anchor']
    sr = skeleton['right_shoulder_anchor']
    pelvis = skeleton['pelvis_anchor']
    torso = skeleton['torso_anchor']
    neck = skeleton['neck_anchor']
    lel = skeleton['left_elbow_anchor']
    rel = skeleton['right_elbow_anchor']
    lha = skeleton['left_hand_anchor']
    rha = skeleton['right_hand_anchor']
    lkn = skeleton['left_knee_anchor']
    rkn = skeleton['right_knee_anchor']
    lft = skeleton['left_foot_anchor']
    rft = skeleton['right_foot_anchor']

    profile = skeleton.get('shape_profile', {})
    shoulder_scale = float(profile.get('shoulder_scale', 1.0))
    arm_taper = float(profile.get('arm_taper', 0.9))
    robe_spread = float(profile.get('robe_spread', 1.0))
    head_roundness = float(profile.get('head_roundness', 1.0))
    torso_split = float(profile.get('torso_split', 0.9))
    core_bridge = float(profile.get('core_bridge', 1.0))
    plane_break_strength = float(profile.get('plane_break_strength', 0.88))

    volumes = [
        {'kind': 'head', 'shape': 'ellipse', 'center': skeleton['head_anchor'], 'radius': (head_size * 0.55 * head_roundness, head_size * 0.68 * head_roundness)},
    ]

    if archetype == 'archon':
        chest_left = [(sl[0] - head_size * 0.70, sl[1] + head_size * 0.10), (torso[0] - head_size * 0.58, torso[1] - head_size * 0.04), (torso[0] - head_size * 0.32 * torso_split, torso[1] + head_size * 0.98), (pelvis[0] - head_size * 0.78, pelvis[1] + head_size * 0.18)]
        chest_right = [(torso[0] + head_size * 0.12 * torso_split, torso[1] - head_size * 0.06), (sr[0] + head_size * 0.66, sr[1] + head_size * 0.08), (pelvis[0] + head_size * 0.68, pelvis[1] + head_size * 0.22), (torso[0] + head_size * 0.24 * torso_split, torso[1] + head_size * 0.90)]
        chest_left = add_symbolic_shoulder_cut(chest_left, head_size * 0.16 * plane_break_strength, head_size * 0.06)
        chest_right = add_symbolic_shoulder_cut(chest_right, head_size * 0.14 * plane_break_strength, head_size * 0.06)
        sternum = [(neck[0] - head_size * 0.14, neck[1] + head_size * 0.10), (neck[0] + head_size * 0.04, neck[1] + head_size * 0.10), (torso[0] + head_size * 0.02, torso[1] + head_size * 0.44), (torso[0] - head_size * 0.18, torso[1] + head_size * 0.44)]
        pelvis_poly = [(pelvis[0] - head_size * 0.84, pelvis[1] - head_size * 0.10), (pelvis[0] + head_size * 0.62, pelvis[1] - head_size * 0.12), (pelvis[0] + head_size * 0.50, pelvis[1] + head_size * 0.62), (pelvis[0] - head_size * 0.70, pelvis[1] + head_size * 0.62)]
        outer_left = [(sl[0] - head_size * 1.10 * robe_spread, sl[1]), (torso[0] - head_size * 0.98, torso[1] + head_size * 0.26), (pelvis[0] - rect.width * 0.20, pelvis[1] + head_size * 1.30), (lft[0] - head_size * 0.76, lft[1]), (pelvis[0] - head_size * 0.46, pelvis[1] + head_size * 0.10)]
        outer_right = [(sr[0] + head_size * 0.90 * robe_spread, sr[1]), (torso[0] + head_size * 0.72, torso[1] + head_size * 0.22), (pelvis[0] + rect.width * 0.15, pelvis[1] + head_size * 1.20), (rft[0] + head_size * 0.62, rft[1]), (pelvis[0] + head_size * 0.30, pelvis[1] + head_size * 0.10)]
        outer_left = add_symbolic_robe_notch(outer_left, head_size * 0.28 * plane_break_strength)
        outer_right = add_symbolic_robe_notch(outer_right, head_size * 0.22 * plane_break_strength)
        volumes.extend([
            {'kind': 'neck', 'shape': 'capsule', 'a': neck, 'b': (torso[0] - head_size * 0.06, torso[1] - head_size * 0.10), 'width': max(3, int(head_size * 0.24))},
            {'kind': 'shoulder_left', 'shape': 'ellipse', 'center': sl, 'radius': (head_size * 0.54 * shoulder_scale, head_size * 0.42 * shoulder_scale)},
            {'kind': 'shoulder_right', 'shape': 'ellipse', 'center': sr, 'radius': (head_size * 0.50 * shoulder_scale, head_size * 0.40 * shoulder_scale)},
            {'kind': 'chest_left', 'shape': 'polygon', 'points': chest_left},
            {'kind': 'chest_right', 'shape': 'polygon', 'points': chest_right},
            {'kind': 'sternum', 'shape': 'polygon', 'points': sternum},
            {'kind': 'pelvis', 'shape': 'polygon', 'points': pelvis_poly},
            {'kind': 'core_bridge', 'shape': 'capsule', 'a': (torso[0] - head_size * 0.05, torso[1] + head_size * 0.10), 'b': (pelvis[0] - head_size * 0.02, pelvis[1] + head_size * 0.10), 'width': max(4, int(head_size * 0.26 * core_bridge))},
        ])
    elif archetype == 'guide_mage':
        chest_left = [(sl[0] - head_size * 0.66, sl[1] + head_size * 0.14), (torso[0] - head_size * 0.50, torso[1] - head_size * 0.03), (torso[0] - head_size * 0.20 * torso_split, torso[1] + head_size * 0.92), (pelvis[0] - head_size * 0.74, pelvis[1] + head_size * 0.22)]
        chest_right = [(torso[0] + head_size * 0.12 * torso_split, torso[1] - head_size * 0.01), (sr[0] + head_size * 0.62, sr[1] + head_size * 0.12), (pelvis[0] + head_size * 0.64, pelvis[1] + head_size * 0.24), (torso[0] + head_size * 0.22 * torso_split, torso[1] + head_size * 0.88)]
        chest_left = add_symbolic_shoulder_cut(chest_left, head_size * 0.10 * plane_break_strength, head_size * 0.04)
        chest_right = add_symbolic_shoulder_cut(chest_right, head_size * 0.10 * plane_break_strength, head_size * 0.04)
        sternum = [(neck[0] - head_size * 0.12, neck[1] + head_size * 0.08), (neck[0] + head_size * 0.02, neck[1] + head_size * 0.08), (torso[0] + head_size * 0.02, torso[1] + head_size * 0.40), (torso[0] - head_size * 0.14, torso[1] + head_size * 0.40)]
        pelvis_poly = [(pelvis[0] - head_size * 0.78, pelvis[1] - head_size * 0.08), (pelvis[0] + head_size * 0.62, pelvis[1] - head_size * 0.10), (pelvis[0] + head_size * 0.52, pelvis[1] + head_size * 0.64), (pelvis[0] - head_size * 0.68, pelvis[1] + head_size * 0.64)]
        outer_left = [(sl[0] - head_size * 0.96 * robe_spread, sl[1] + head_size * 0.08), (torso[0] - head_size * 0.92, torso[1] + head_size * 0.30), (pelvis[0] - rect.width * 0.20, pelvis[1] + head_size * 1.18), (lft[0] - head_size * 0.64, lft[1]), (pelvis[0] - head_size * 0.40, pelvis[1] + head_size * 0.10)]
        outer_right = [(sr[0] + head_size * 0.82 * robe_spread, sr[1] + head_size * 0.08), (torso[0] + head_size * 0.68, torso[1] + head_size * 0.30), (pelvis[0] + rect.width * 0.15, pelvis[1] + head_size * 1.08), (rft[0] + head_size * 0.50, rft[1]), (pelvis[0] + head_size * 0.28, pelvis[1] + head_size * 0.10)]
        outer_left = add_symbolic_robe_notch(outer_left, head_size * 0.20 * plane_break_strength)
        outer_right = add_symbolic_robe_notch(outer_right, head_size * 0.18 * plane_break_strength)
        volumes.extend([
            {'kind': 'neck', 'shape': 'capsule', 'a': neck, 'b': (torso[0] - head_size * 0.05, torso[1] - head_size * 0.10), 'width': max(3, int(head_size * 0.22))},
            {'kind': 'shoulder_left', 'shape': 'ellipse', 'center': sl, 'radius': (head_size * 0.48 * shoulder_scale, head_size * 0.40 * shoulder_scale)},
            {'kind': 'shoulder_right', 'shape': 'ellipse', 'center': sr, 'radius': (head_size * 0.46 * shoulder_scale, head_size * 0.38 * shoulder_scale)},
            {'kind': 'chest_left', 'shape': 'polygon', 'points': chest_left},
            {'kind': 'chest_right', 'shape': 'polygon', 'points': chest_right},
            {'kind': 'sternum', 'shape': 'polygon', 'points': sternum},
            {'kind': 'pelvis', 'shape': 'polygon', 'points': pelvis_poly},
            {'kind': 'mid_bridge', 'shape': 'capsule', 'a': (torso[0], torso[1] + head_size * 0.18), 'b': (pelvis[0], pelvis[1] + head_size * 0.02), 'width': max(4, int(head_size * 0.30 * core_bridge))},
        ])
    else:
        chest_left = [(sl[0] - head_size * 0.85, sl[1] + head_size * 0.04), (torso[0] - head_size * 0.28, torso[1] - head_size * 0.08), (torso[0] - head_size * 0.18, torso[1] + head_size * 0.88), (pelvis[0] - head_size * 0.65, pelvis[1] + head_size * 0.24)]
        chest_right = [(torso[0] + head_size * 0.28, torso[1] - head_size * 0.08), (sr[0] + head_size * 0.95, sr[1] + head_size * 0.04), (pelvis[0] + head_size * 0.72, pelvis[1] + head_size * 0.24), (torso[0] + head_size * 0.18, torso[1] + head_size * 0.88)]
        chest_left = add_symbolic_shoulder_cut(chest_left, head_size * 0.12 * plane_break_strength, head_size * 0.05)
        chest_right = add_symbolic_shoulder_cut(chest_right, head_size * 0.12 * plane_break_strength, head_size * 0.05)
        pelvis_poly = [(pelvis[0] - head_size * 0.86, pelvis[1] - head_size * 0.08), (pelvis[0] + head_size * 0.86, pelvis[1] - head_size * 0.08), (pelvis[0] + head_size * 0.66, pelvis[1] + head_size * 0.66), (pelvis[0] - head_size * 0.66, pelvis[1] + head_size * 0.66)]
        outer_left = [(sl[0] - head_size * 1.00 * robe_spread, sl[1]), (torso[0] - head_size * 0.76, torso[1] + head_size * 0.32), (pelvis[0] - rect.width * 0.14, pelvis[1] + head_size * 0.88), (lft[0] - head_size * 0.34, lft[1]), (pelvis[0] - head_size * 0.34, pelvis[1] + head_size * 0.16)]
        outer_right = [(sr[0] + head_size * 1.05 * robe_spread, sr[1]), (torso[0] + head_size * 0.92, torso[1] + head_size * 0.32), (pelvis[0] + rect.width * 0.17, pelvis[1] + head_size * 0.92), (rft[0] + head_size * 0.38, rft[1]), (pelvis[0] + head_size * 0.38, pelvis[1] + head_size * 0.18)]
        outer_left = add_symbolic_robe_notch(outer_left, head_size * 0.14 * plane_break_strength)
        outer_right = add_symbolic_robe_notch(outer_right, head_size * 0.14 * plane_break_strength)
        volumes.extend([
            {'kind': 'neck', 'shape': 'capsule', 'a': neck, 'b': torso, 'width': max(4, int(head_size * 0.34))},
            {'kind': 'shoulder_left', 'shape': 'ellipse', 'center': sl, 'radius': (head_size * 0.52 * shoulder_scale, head_size * 0.42 * shoulder_scale)},
            {'kind': 'shoulder_right', 'shape': 'ellipse', 'center': sr, 'radius': (head_size * 0.56 * shoulder_scale, head_size * 0.44 * shoulder_scale)},
            {'kind': 'chest_left', 'shape': 'polygon', 'points': chest_left},
            {'kind': 'chest_right', 'shape': 'polygon', 'points': chest_right},
            {'kind': 'pelvis', 'shape': 'polygon', 'points': pelvis_poly},
            {'kind': 'sternum', 'shape': 'capsule', 'a': (torso[0] - head_size * 0.04, torso[1] - head_size * 0.10), 'b': (pelvis[0], pelvis[1] + head_size * 0.10), 'width': max(4, int(head_size * 0.26 * core_bridge))},
        ])

    volumes.extend([
        {'kind': 'left_upper_arm', 'shape': 'capsule', 'a': sl, 'b': lel, 'width': max(5, int(head_size * 0.48 * arm_taper))},
        {'kind': 'left_forearm', 'shape': 'capsule', 'a': lel, 'b': lha, 'width': max(4, int(head_size * 0.40 * arm_taper))},
        {'kind': 'right_upper_arm', 'shape': 'capsule', 'a': sr, 'b': rel, 'width': max(5, int(head_size * 0.54 * arm_taper))},
        {'kind': 'right_forearm', 'shape': 'capsule', 'a': rel, 'b': rha, 'width': max(4, int(head_size * 0.44 * arm_taper))},
        {'kind': 'left_upper_leg', 'shape': 'capsule', 'a': pelvis, 'b': lkn, 'width': max(6, int(head_size * 0.56))},
        {'kind': 'left_lower_leg', 'shape': 'capsule', 'a': lkn, 'b': lft, 'width': max(5, int(head_size * 0.48))},
        {'kind': 'right_upper_leg', 'shape': 'capsule', 'a': pelvis, 'b': rkn, 'width': max(6, int(head_size * 0.58))},
        {'kind': 'right_lower_leg', 'shape': 'capsule', 'a': rkn, 'b': rft, 'width': max(5, int(head_size * 0.50))},
        {'kind': 'outer_left', 'shape': 'polygon', 'points': outer_left},
        {'kind': 'outer_right', 'shape': 'polygon', 'points': outer_right},
    ])
    return volumes
