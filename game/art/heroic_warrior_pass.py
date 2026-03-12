from __future__ import annotations

import pygame


def apply_heroic_warrior_reconstruction(subject_mask: pygame.Surface, subject_detail: pygame.Surface, weapon_back: pygame.Surface, weapon_front: pygame.Surface, skeleton: dict[str, object], tones: dict[str, tuple[int, int, int, int]]):
    rect: pygame.Rect = skeleton['rect']
    torso = skeleton['torso_anchor']
    pelvis = skeleton['pelvis_anchor']
    sl = skeleton['left_shoulder_anchor']
    sr = skeleton['right_shoulder_anchor']
    rha = skeleton['right_hand_anchor']
    tip = skeleton.get('weapon_tip_anchor', rha)

    cloth = tones['cloth'][:3]
    trim = tones['trim'][:3]
    shadow = tones['shadow'][:3]
    metal = tones['metal'][:3]

    # Make the body read more solid and less translucent.
    solid = pygame.Surface(subject_mask.get_size(), pygame.SRCALPHA)
    chest = [
        (int(sl[0] - rect.width * 0.06), int(sl[1] + rect.height * 0.02)),
        (int(sr[0] + rect.width * 0.07), int(sr[1] + rect.height * 0.02)),
        (int(torso[0] + rect.width * 0.12), int(torso[1] + rect.height * 0.22)),
        (int(torso[0]), int(pelvis[1] - rect.height * 0.01)),
        (int(torso[0] - rect.width * 0.12), int(torso[1] + rect.height * 0.22)),
    ]
    waist = pygame.Rect(int(pelvis[0] - rect.width * 0.14), int(pelvis[1] - rect.height * 0.02), int(rect.width * 0.28), int(rect.height * 0.10))
    pygame.draw.polygon(solid, (*cloth, 168), chest)
    pygame.draw.rect(solid, (*trim, 156), waist, border_radius=0)
    subject_mask.blit(solid, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)

    # Harder chest read and internal planes.
    detail = pygame.Surface(subject_detail.get_size(), pygame.SRCALPHA)
    breastplate = [
        (int(sl[0] - rect.width * 0.02), int(sl[1] + rect.height * 0.04)),
        (int(sr[0] + rect.width * 0.02), int(sr[1] + rect.height * 0.04)),
        (int(torso[0] + rect.width * 0.10), int(torso[1] + rect.height * 0.15)),
        (int(torso[0]), int(torso[1] + rect.height * 0.26)),
        (int(torso[0] - rect.width * 0.10), int(torso[1] + rect.height * 0.15)),
    ]
    left_plane = [(breastplate[0][0], breastplate[0][1]), (int(torso[0]), int(torso[1] + rect.height * 0.07)), (int(torso[0] - rect.width * 0.08), int(torso[1] + rect.height * 0.20)), breastplate[4]]
    right_plane = [(int(torso[0]), int(torso[1] + rect.height * 0.07)), breastplate[1], breastplate[2], (int(torso[0] + rect.width * 0.08), int(torso[1] + rect.height * 0.20))]
    fauld = [
        (int(pelvis[0] - rect.width * 0.16), int(pelvis[1] + rect.height * 0.02)),
        (int(pelvis[0] + rect.width * 0.16), int(pelvis[1] + rect.height * 0.02)),
        (int(pelvis[0] + rect.width * 0.11), int(pelvis[1] + rect.height * 0.13)),
        (int(pelvis[0] - rect.width * 0.11), int(pelvis[1] + rect.height * 0.13)),
    ]
    pygame.draw.polygon(detail, (*trim, 120), breastplate)
    pygame.draw.polygon(detail, (*metal, 84), left_plane)
    pygame.draw.polygon(detail, (*shadow, 96), right_plane)
    pygame.draw.polygon(detail, (*trim, 110), fauld)
    pygame.draw.line(detail, (*shadow, 132), (int(torso[0]), int(torso[1] + rect.height * 0.04)), (int(torso[0]), int(pelvis[1] + rect.height * 0.10)), max(1, rect.width // 52))
    subject_detail.blit(detail, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Rebuild spear for a much clearer hero prop read.
    spear_back = pygame.Surface(weapon_back.get_size(), pygame.SRCALPHA)
    spear_front = pygame.Surface(weapon_front.get_size(), pygame.SRCALPHA)
    shaft_w = max(4, rect.width // 30)
    shaft_color = (*metal, 248)
    glow_color = (*trim, 164)
    pygame.draw.line(spear_back, shaft_color, (int(rha[0]), int(rha[1])), (int(tip[0]), int(tip[1])), shaft_w)
    pygame.draw.line(spear_front, (*shadow, 220), (int(rha[0]), int(rha[1])), (int(tip[0]), int(tip[1])), max(1, rect.width // 84))
    head = [
        (int(tip[0]), int(tip[1])),
        (int(tip[0] - rect.width * 0.055), int(tip[1] + rect.height * 0.045)),
        (int(tip[0] - rect.width * 0.008), int(tip[1] + rect.height * 0.115)),
        (int(tip[0] + rect.width * 0.034), int(tip[1] + rect.height * 0.040)),
    ]
    wing_left = [
        (int(tip[0] - rect.width * 0.010), int(tip[1] + rect.height * 0.040)),
        (int(tip[0] - rect.width * 0.090), int(tip[1] + rect.height * 0.075)),
        (int(tip[0] - rect.width * 0.020), int(tip[1] + rect.height * 0.090)),
    ]
    banner = [
        (int(rha[0] + rect.width * 0.015), int(rha[1] - rect.height * 0.010)),
        (int(rha[0] + rect.width * 0.22), int(rha[1] + rect.height * 0.045)),
        (int(rha[0] + rect.width * 0.08), int(rha[1] + rect.height * 0.12)),
    ]
    grip = pygame.Rect(int(rha[0] - rect.width * 0.010), int(rha[1] - rect.height * 0.016), int(rect.width * 0.055), int(rect.height * 0.035))
    pygame.draw.polygon(spear_back, (*trim, 252), head)
    pygame.draw.polygon(spear_back, (*trim, 210), wing_left)
    pygame.draw.polygon(spear_back, glow_color, banner)
    pygame.draw.rect(spear_back, (*trim, 190), grip, border_radius=0)
    pygame.draw.polygon(spear_front, (*shadow, 230), head, 1)
    pygame.draw.line(spear_front, (*trim, 110), (int(rha[0]) + 1, int(rha[1]) + 1), (int(tip[0]) - 1, int(tip[1]) + max(1, shaft_w // 2)), 1)
    weapon_back.blit(spear_back, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
    weapon_front.blit(spear_front, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
