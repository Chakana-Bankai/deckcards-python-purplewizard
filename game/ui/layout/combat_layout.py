from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class CombatLayout:
    topbar_left: pygame.Rect
    topbar_center: pygame.Rect
    topbar_right: pygame.Rect
    enemy_strip: pygame.Rect
    voices_panel: pygame.Rect
    hand_area: pygame.Rect
    actions_panel: pygame.Rect
    player_hud: pygame.Rect
    harmony_core: pygame.Rect
    card_detail: pygame.Rect

    @property
    def topbar_rect(self) -> pygame.Rect:
        return self.topbar_center.unionall([self.topbar_left, self.topbar_right])

    @property
    def enemy_strip_rect(self) -> pygame.Rect:
        return self.enemy_strip

    @property
    def voices_rect(self) -> pygame.Rect:
        return self.voices_panel

    @property
    def hand_rect(self) -> pygame.Rect:
        return self.hand_area

    @property
    def actions_rect(self) -> pygame.Rect:
        return self.actions_panel

    @property
    def playerhud_rect(self) -> pygame.Rect:
        return self.player_hud

    @property
    def harmony_rect(self) -> pygame.Rect:
        return self.harmony_core


def build_combat_layout(w: int, h: int) -> CombatLayout:
    pad = max(12, int(min(w, h) * 0.02))
    top_h = max(64, int(h * 0.07))

    topbar_full = pygame.Rect(0, 0, w, top_h)
    left_w = int(topbar_full.w * 0.22)
    right_w = int(topbar_full.w * 0.22)
    center_w = topbar_full.w - left_w - right_w
    topbar_left = pygame.Rect(topbar_full.x, topbar_full.y, left_w, topbar_full.h)
    topbar_center = pygame.Rect(topbar_left.right, topbar_full.y, center_w, topbar_full.h)
    topbar_right = pygame.Rect(topbar_center.right, topbar_full.y, right_w, topbar_full.h)

    combat_area = pygame.Rect(pad, topbar_full.bottom + pad, w - 2 * pad, h - (topbar_full.bottom + pad) - pad)
    enemy_h = max(178, int(combat_area.h * 0.30))
    center_h = max(92, int(combat_area.h * 0.20))
    bottom_h = max(220, combat_area.h - enemy_h - center_h - 2 * pad)

    enemy_strip = pygame.Rect(combat_area.x, combat_area.y, combat_area.w, enemy_h)

    center_y = enemy_strip.bottom + pad
    voices_w = int((combat_area.w - pad) * 0.46)
    voices_panel = pygame.Rect(combat_area.x, center_y, voices_w, center_h)
    card_detail = pygame.Rect(voices_panel.right + pad, center_y, combat_area.right - (voices_panel.right + pad), center_h)

    bottom_y = center_y + center_h + pad
    hand_h = max(188, int(bottom_h * 0.56))
    status_h = max(140, bottom_h - hand_h - pad)
    status_y = bottom_y
    hand_y = status_y + status_h + pad
    hand_area = pygame.Rect(combat_area.x, hand_y, combat_area.w, max(172, bottom_h - status_h - pad))

    total_w = combat_area.w
    player_w = int(total_w * 0.38)
    harmony_w = int(total_w * 0.24)
    action_w = total_w - player_w - harmony_w - 2 * pad

    player_hud = pygame.Rect(combat_area.x, status_y, player_w, status_h)
    harmony_core = pygame.Rect(player_hud.right + pad, status_y, harmony_w, status_h)
    actions_panel = pygame.Rect(harmony_core.right + pad, status_y, action_w, status_h)

    return CombatLayout(
        topbar_left=topbar_left,
        topbar_center=topbar_center,
        topbar_right=topbar_right,
        enemy_strip=enemy_strip,
        voices_panel=voices_panel,
        hand_area=hand_area,
        actions_panel=actions_panel,
        player_hud=player_hud,
        harmony_core=harmony_core,
        card_detail=card_detail,
    )
