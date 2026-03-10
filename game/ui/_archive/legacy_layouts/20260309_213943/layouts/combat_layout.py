"""DEPRECATED: legacy combat layout module.

This file is kept for backward compatibility during UI system migration.
Active combat layout source of truth is `game.ui.layout.combat_layout`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class CombatLayout:
    topbar_rect: pygame.Rect
    enemy_strip_rect: pygame.Rect
    voices_rect: pygame.Rect
    hand_rect: pygame.Rect
    playerhud_rect: pygame.Rect
    actions_rect: pygame.Rect

    @classmethod
    def from_size(cls, screen_w: int, screen_h: int) -> "CombatLayout":
        pad = max(12, int(min(screen_w, screen_h) * 0.02))
        top_h = max(74, int(screen_h * 0.09))
        enemy_h = max(240, int(screen_h * 0.30))
        voices_h = max(100, int(screen_h * 0.13))
        lower_h = max(220, int(screen_h * 0.24))
        actions_h = max(110, int(screen_h * 0.14))

        topbar = pygame.Rect(0, 0, screen_w, top_h)
        enemy_strip = pygame.Rect(pad, topbar.bottom + pad, screen_w - 2 * pad, enemy_h)
        voices = pygame.Rect(pad, enemy_strip.bottom + pad, screen_w - 2 * pad, voices_h)

        bottom_y = screen_h - pad - actions_h
        hand_w = int((screen_w - 3 * pad) * 0.66)
        hand = pygame.Rect(pad, bottom_y - pad - lower_h, hand_w, lower_h)
        playerhud = pygame.Rect(hand.right + pad, hand.y, screen_w - (hand.right + pad) - pad, lower_h)
        actions = pygame.Rect(pad, bottom_y, screen_w - 2 * pad, actions_h)
        return cls(topbar, enemy_strip, voices, hand, playerhud, actions)
