"""Reusable layout helpers to avoid raw coordinate duplication."""

from __future__ import annotations

import pygame


def inset(rect: pygame.Rect, padding: int) -> pygame.Rect:
    return rect.inflate(-padding * 2, -padding * 2)


def split_horizontal(rect: pygame.Rect, ratio: float) -> tuple[pygame.Rect, pygame.Rect]:
    w_left = int(rect.w * max(0.0, min(1.0, ratio)))
    left = pygame.Rect(rect.x, rect.y, w_left, rect.h)
    right = pygame.Rect(left.right, rect.y, rect.w - w_left, rect.h)
    return left, right


def split_vertical(rect: pygame.Rect, ratio: float) -> tuple[pygame.Rect, pygame.Rect]:
    h_top = int(rect.h * max(0.0, min(1.0, ratio)))
    top = pygame.Rect(rect.x, rect.y, rect.w, h_top)
    bottom = pygame.Rect(rect.x, top.bottom, rect.w, rect.h - h_top)
    return top, bottom


def anchor_bottom_center(container: pygame.Rect, w: int, h: int, margin: int = 0) -> pygame.Rect:
    return pygame.Rect(container.centerx - w // 2, container.bottom - h - margin, w, h)


def anchor_top_right(container: pygame.Rect, w: int, h: int, margin: int = 0) -> pygame.Rect:
    return pygame.Rect(container.right - w - margin, container.y + margin, w, h)


def build_three_column_layout(rect: pygame.Rect, gap: int = 12, ratios=(0.25, 0.5, 0.25)) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
    r0, r1, r2 = ratios
    total = max(0.01, r0 + r1 + r2)
    w0 = int((rect.w - 2 * gap) * (r0 / total))
    w1 = int((rect.w - 2 * gap) * (r1 / total))
    w2 = rect.w - w0 - w1 - 2 * gap
    c0 = pygame.Rect(rect.x, rect.y, w0, rect.h)
    c1 = pygame.Rect(c0.right + gap, rect.y, w1, rect.h)
    c2 = pygame.Rect(c1.right + gap, rect.y, w2, rect.h)
    return c0, c1, c2


def build_modal_preview_layout(rect: pygame.Rect, gap: int = 12) -> tuple[pygame.Rect, pygame.Rect]:
    left, right = split_horizontal(rect, 0.62)
    return inset(left, gap), inset(right, gap)


def safe_area(w: int, h: int, margin: int, bottom_margin: int) -> pygame.Rect:
    return pygame.Rect(margin, margin, w - margin * 2, h - margin - bottom_margin)
