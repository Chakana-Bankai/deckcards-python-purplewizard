from __future__ import annotations

import pygame


def _pt(point) -> tuple[int, int]:
    return (int(point[0]), int(point[1]))


def render_costume_detail_pass(target: pygame.Surface, skeleton: dict[str, object], archetype: str, palette, tones, shape_profile):
    rect: pygame.Rect = skeleton['rect']
    torso = _pt(skeleton['torso_anchor'])
    pelvis = _pt(skeleton['pelvis_anchor'])
    sl = _pt(skeleton['left_shoulder_anchor'])
    sr = _pt(skeleton['right_shoulder_anchor'])
    rel = _pt(skeleton['right_elbow_anchor'])
    rha = _pt(skeleton['right_hand_anchor'])
    lkn = _pt(skeleton['left_knee_anchor'])
    rkn = _pt(skeleton['right_knee_anchor'])

    trim = (*tones['trim'][:3], 78)
    shade = (*tones['shadow'][:3], 82)
    cloth = (*tones['cloth'][:3], 68)
    metal = (*tones['metal'][:3], 86)
    line_w = max(2, rect.width // 38)

    if archetype == 'archon':
        mantle = [(sl[0] - rect.width // 12, sl[1] + rect.height // 32), (torso[0] - rect.width // 8, torso[1] + rect.height // 14), (pelvis[0] - rect.width // 12, pelvis[1] + rect.height // 12), (pelvis[0] - rect.width // 7, pelvis[1] + rect.height // 4)]
        stole = pygame.Rect(int(torso[0] - rect.width * 0.06), int(torso[1] + rect.height * 0.02), int(rect.width * 0.12), int(rect.height * 0.30))
        hem_left = [(pelvis[0] - rect.width // 8, pelvis[1] + rect.height // 10), (lkn[0] - rect.width // 14, lkn[1]), (pelvis[0] - rect.width // 20, rect.bottom - rect.height // 10)]
        hem_right = [(pelvis[0] + rect.width // 10, pelvis[1] + rect.height // 10), (rkn[0] + rect.width // 18, rkn[1]), (pelvis[0] + rect.width // 18, rect.bottom - rect.height // 10)]
        clasp = pygame.Rect(int(torso[0] - rect.width * 0.045), int(torso[1] + rect.height * 0.12), int(rect.width * 0.09), int(rect.height * 0.06))
        pygame.draw.polygon(target, cloth, mantle)
        pygame.draw.rect(target, trim, stole, border_radius=max(4, rect.width // 34))
        pygame.draw.rect(target, metal, clasp, border_radius=max(3, rect.width // 40))
        pygame.draw.polygon(target, shade, hem_left)
        pygame.draw.polygon(target, shade, hem_right)
    elif archetype == 'guide_mage':
        sash = [(sl[0] - rect.width // 18, sl[1] + rect.height // 24), (torso[0] - rect.width // 12, torso[1] + rect.height // 10), (torso[0] + rect.width // 9, torso[1] + rect.height // 8), (sr[0] + rect.width // 14, sr[1] + rect.height // 20), (torso[0] + rect.width // 10, torso[1] + rect.height // 5), (torso[0] - rect.width // 14, torso[1] + rect.height // 4)]
        apron = [(torso[0] - rect.width // 12, torso[1] + rect.height // 4), (torso[0] + rect.width // 10, torso[1] + rect.height // 4), (pelvis[0] + rect.width // 12, pelvis[1] + rect.height // 8), (pelvis[0] - rect.width // 10, pelvis[1] + rect.height // 10)]
        sleeve = pygame.Rect(int(rel[0] - rect.width * 0.05), int(rel[1] - rect.height * 0.03), int(rect.width * 0.10), int(rect.height * 0.08))
        belt = pygame.Rect(int(pelvis[0] - rect.width * 0.14), int(pelvis[1] - rect.height * 0.02), int(rect.width * 0.28), int(rect.height * 0.06))
        pygame.draw.polygon(target, cloth, sash)
        pygame.draw.polygon(target, trim, apron)
        pygame.draw.rect(target, metal, sleeve, border_radius=max(4, rect.width // 34))
        pygame.draw.rect(target, trim, belt, border_radius=max(4, rect.width // 36))
    else:
        breast = [(sl[0] - rect.width // 16, sl[1] + rect.height // 28), (torso[0] - rect.width // 11, torso[1] + rect.height // 16), (torso[0] + rect.width // 9, torso[1] + rect.height // 18), (sr[0] + rect.width // 16, sr[1] + rect.height // 24), (torso[0] + rect.width // 12, torso[1] + rect.height // 4), (torso[0] - rect.width // 14, torso[1] + rect.height // 4)]
        fauld = pygame.Rect(int(pelvis[0] - rect.width * 0.16), int(pelvis[1] - rect.height * 0.02), int(rect.width * 0.32), int(rect.height * 0.08))
        buckle = pygame.Rect(int(pelvis[0] - rect.width * 0.05), int(pelvis[1]), int(rect.width * 0.10), int(rect.height * 0.05))
        pygame.draw.polygon(target, trim, breast)
        pygame.draw.rect(target, cloth, fauld, border_radius=max(4, rect.width // 32))
        pygame.draw.rect(target, metal, buckle, border_radius=max(3, rect.width // 38))

    pygame.draw.line(target, shade, (torso[0] - rect.width // 16, torso[1] + rect.height // 12), (pelvis[0] - rect.width // 14, pelvis[1] + rect.height // 9), line_w)
    pygame.draw.line(target, shade, (torso[0] + rect.width // 18, torso[1] + rect.height // 12), (pelvis[0] + rect.width // 14, pelvis[1] + rect.height // 9), line_w)
    pygame.draw.line(target, shade, rel, rha, max(2, line_w - 1))
