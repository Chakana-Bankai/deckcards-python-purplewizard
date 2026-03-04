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


def build_combat_layout(w: int, h: int) -> CombatLayout:
    pad = max(12, int(min(w, h) * 0.02))
    top_h = max(74, int(h * 0.09))
    enemy_h = max(240, int(h * 0.30))
    voices_h = max(100, int(h * 0.13))
    lower_h = max(220, int(h * 0.24))
    actions_h = max(110, int(h * 0.14))

    topbar_full = pygame.Rect(0, 0, w, top_h)
    left_w = int(topbar_full.w * 0.22)
    right_w = int(topbar_full.w * 0.22)
    center_w = topbar_full.w - left_w - right_w
    topbar_left = pygame.Rect(topbar_full.x, topbar_full.y, left_w, topbar_full.h)
    topbar_center = pygame.Rect(topbar_left.right, topbar_full.y, center_w, topbar_full.h)
    topbar_right = pygame.Rect(topbar_center.right, topbar_full.y, right_w, topbar_full.h)

    enemy_strip = pygame.Rect(pad, topbar_full.bottom + pad, w - 2 * pad, enemy_h)
    voices_panel = pygame.Rect(pad, enemy_strip.bottom + pad, w - 2 * pad, voices_h)

    bottom_y = h - pad - actions_h
    hand_w = int((w - 3 * pad) * 0.66)
    hand_area = pygame.Rect(pad, bottom_y - pad - lower_h, hand_w, lower_h)
    player_hud = pygame.Rect(hand_area.right + pad, hand_area.y, w - (hand_area.right + pad) - pad, lower_h)
    actions_panel = pygame.Rect(pad, bottom_y, w - 2 * pad, actions_h)

    card_detail = pygame.Rect(
        player_hud.x,
        player_hud.bottom + 10,
        player_hud.w,
        max(110, actions_panel.y - player_hud.bottom - 16),
    )

    return CombatLayout(
        topbar_left=topbar_left,
        topbar_center=topbar_center,
        topbar_right=topbar_right,
        enemy_strip=enemy_strip,
        voices_panel=voices_panel,
        hand_area=hand_area,
        actions_panel=actions_panel,
        player_hud=player_hud,
        card_detail=card_detail,
    )
