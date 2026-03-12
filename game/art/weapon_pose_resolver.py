from __future__ import annotations

import pygame


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def bind_weapon_pose(skeleton: dict[str, object], weapon: dict[str, object]) -> dict[str, object]:
    rect: pygame.Rect = skeleton['rect']
    family = str(weapon.get('family', 'staff'))
    orientation = str(skeleton.get('weapon_orientation', 'vertical'))
    surface_rect = pygame.Rect((0, 0), skeleton.get('surface_size', (rect.right + 1, rect.bottom + 1)))
    profile = skeleton.get('shape_profile', {})
    lane_profile = float(profile.get('lane_offset', 0.10))
    mass_bias = float(profile.get('weapon_mass_bias', 1.0))

    lane_factor = lane_profile if family in {'staff', 'orb'} else max(0.08, lane_profile - 0.01)
    lane_x = int(min(surface_rect.right - 8, rect.right + rect.width * lane_factor))

    shoulder_x, shoulder_y = skeleton['right_shoulder_anchor']
    elbow_x, elbow_y = skeleton['right_elbow_anchor']
    hand_x, hand_y = skeleton['right_hand_anchor']

    if family in {'staff', 'orb'}:
        elbow_x = int(rect.centerx + rect.width * 0.09)
        elbow_y = int(rect.top + rect.height * 0.40)
        hand_x = int(rect.right - rect.width * 0.05)
        hand_y = int(rect.top + rect.height * 0.52)
    elif family == 'spear':
        elbow_x = int(rect.centerx + rect.width * 0.18)
        elbow_y = int(rect.top + rect.height * 0.36)
        hand_x = int(rect.right - rect.width * 0.03)
        hand_y = int(rect.top + rect.height * 0.34)

    skeleton['right_shoulder_anchor'] = (shoulder_x, shoulder_y)
    skeleton['right_elbow_anchor'] = (elbow_x, elbow_y)
    skeleton['right_hand_anchor'] = (hand_x, hand_y)
    skeleton['hand_right_anchor'] = skeleton['right_hand_anchor']

    grip_dx = max(6, int(rect.width * (0.045 if family in {'staff', 'orb'} else 0.03) * max(0.88, mass_bias)))
    origin = (min(lane_x - grip_dx, hand_x + grip_dx), hand_y)
    bridge = ((hand_x + origin[0]) / 2.0, (hand_y + origin[1]) / 2.0)

    if orientation == 'diagonal':
        tip = (min(surface_rect.right - 6, lane_x + int(rect.width * 0.32)), max(4, hand_y - int(rect.height * 0.34)))
    elif family == 'orb':
        tip = (lane_x, max(6, hand_y - int(rect.height * 0.14)))
    else:
        tip = (lane_x, max(6, hand_y - int(rect.height * 0.24)))

    skeleton['weapon_origin_anchor'] = origin
    skeleton['weapon_bridge_anchor'] = bridge
    skeleton['weapon_tip_anchor'] = tip
    skeleton['weapon_lane_anchor'] = (lane_x, rect.centery)
    skeleton['weapon_lane_rect'] = pygame.Rect(max(0, lane_x - max(8, rect.width // 18)), max(0, rect.top - rect.height // 14), min(surface_rect.right, max(14, rect.width // 6)), min(surface_rect.bottom, int(rect.height * 0.76))).clip(surface_rect)
    return skeleton
