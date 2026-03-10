from __future__ import annotations

import random

import pygame


def _blocky_line(surface: pygame.Surface, color, a, b, width: int = 3):
    pygame.draw.line(surface, color, a, b, width)


def _draw_condor(surface: pygame.Surface, rect: pygame.Rect, color):
    cx, cy = rect.center
    wingspan = rect.w // 2
    body_h = rect.h // 3
    pts = [
        (cx - wingspan, cy - body_h // 4),
        (cx - rect.w // 5, cy - body_h),
        (cx, cy - body_h // 3),
        (cx + rect.w // 5, cy - body_h),
        (cx + wingspan, cy - body_h // 4),
        (cx + rect.w // 6, cy + body_h // 5),
        (cx + rect.w // 10, cy + body_h),
        (cx, cy + body_h // 2),
        (cx - rect.w // 10, cy + body_h),
        (cx - rect.w // 6, cy + body_h // 5),
    ]
    pygame.draw.polygon(surface, color, pts)


def _draw_tree(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    trunk = pygame.Rect(rect.centerx - rect.w // 10, rect.centery, rect.w // 5, rect.h // 3)
    pygame.draw.rect(surface, accent, trunk)
    crown_r = rect.w // 4
    for dx, dy in ((0, -rect.h // 5), (-rect.w // 6, -rect.h // 8), (rect.w // 6, -rect.h // 8)):
        pygame.draw.circle(surface, color, (rect.centerx + dx, rect.centery + dy), crown_r)


def _draw_castle(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    base = pygame.Rect(rect.x + rect.w // 8, rect.y + rect.h // 3, rect.w * 3 // 4, rect.h * 2 // 3)
    pygame.draw.rect(surface, color, base)
    tw = rect.w // 5
    for x in (rect.x + rect.w // 10, rect.centerx - tw // 2, rect.right - tw - rect.w // 10):
        tower = pygame.Rect(x, rect.y + rect.h // 5, tw, rect.h * 3 // 5)
        pygame.draw.rect(surface, color, tower)
        for notch in range(3):
            pygame.draw.rect(surface, accent, (tower.x + notch * (tw // 3), tower.y, max(2, tw // 5), rect.h // 12))


def _draw_humanoid(surface: pygame.Surface, rect: pygame.Rect, color, accent, crown: bool = False):
    cx = rect.centerx
    top = rect.y + rect.h // 8
    pygame.draw.circle(surface, color, (cx, top + rect.h // 8), rect.w // 8)
    torso = pygame.Rect(cx - rect.w // 8, top + rect.h // 5, rect.w // 4, rect.h // 3)
    pygame.draw.rect(surface, color, torso)
    _blocky_line(surface, color, (cx - rect.w // 8, torso.y + rect.h // 10), (cx - rect.w // 4, torso.y + rect.h // 3), 4)
    _blocky_line(surface, color, (cx + rect.w // 8, torso.y + rect.h // 10), (cx + rect.w // 4, torso.y + rect.h // 3), 4)
    _blocky_line(surface, color, (cx - rect.w // 12, torso.bottom), (cx - rect.w // 7, rect.bottom - rect.h // 10), 4)
    _blocky_line(surface, color, (cx + rect.w // 12, torso.bottom), (cx + rect.w // 7, rect.bottom - rect.h // 10), 4)
    cape = [(cx - rect.w // 6, torso.y + rect.h // 12), (cx - rect.w // 3, rect.bottom - rect.h // 6), (cx + rect.w // 3, rect.bottom - rect.h // 6), (cx + rect.w // 6, torso.y + rect.h // 12)]
    pygame.draw.polygon(surface, accent, cape, 0)
    if crown:
        points = [(cx - rect.w // 10, top + rect.h // 18), (cx - rect.w // 18, top - 2), (cx, top + rect.h // 20), (cx + rect.w // 18, top - 2), (cx + rect.w // 10, top + rect.h // 18)]
        pygame.draw.lines(surface, accent, False, points, 2)


def _draw_beast(surface: pygame.Surface, rect: pygame.Rect, color):
    body = pygame.Rect(rect.x + rect.w // 5, rect.y + rect.h // 3, rect.w // 2, rect.h // 4)
    pygame.draw.rect(surface, color, body)
    head = pygame.Rect(body.right - rect.w // 12, body.y - rect.h // 10, rect.w // 5, rect.h // 6)
    pygame.draw.rect(surface, color, head)
    for lx in (body.x + rect.w // 16, body.x + rect.w // 5, body.right - rect.w // 6, body.right - rect.w // 12):
        _blocky_line(surface, color, (lx, body.bottom), (lx - 2, rect.bottom - rect.h // 10), 3)
    _blocky_line(surface, color, (body.x, body.y + rect.h // 10), (rect.x + rect.w // 12, rect.y + rect.h // 5), 2)


def draw_subject(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random):
    subject = ' '.join([
        str(semantic.get('subject', '') or ''),
        str(semantic.get('environment', '') or ''),
        ' '.join(getattr(r, 'cue', '') for r in refs[:2]),
    ]).lower()
    main = palette[2]
    accent = palette[3]
    rect = pygame.Rect(int(surface.get_width() * 0.20), int(surface.get_height() * 0.16), int(surface.get_width() * 0.60), int(surface.get_height() * 0.58))
    if any(k in subject for k in ('condor', 'c�ndor', 'bird', 'ave')):
        _draw_condor(surface, rect, main)
    elif any(k in subject for k in ('tree', 'gaia', 'arbol', '�rbol')):
        _draw_tree(surface, rect, main, accent)
    elif any(k in subject for k in ('castle', 'temple', 'sanctuary', 'ruins', 'throne', 'city')):
        _draw_castle(surface, rect, main, accent)
    elif any(k in subject for k in ('archon', 'arconte')):
        _draw_humanoid(surface, rect, main, accent, crown=True)
    elif any(k in subject for k in ('guardian', 'warrior', 'oracle', 'mage', 'figure', 'herald')):
        _draw_humanoid(surface, rect, main, accent, crown=False)
    elif any(k in subject for k in ('beast', 'puma', 'wolf', 'larva', 'sabueso')):
        _draw_beast(surface, rect, main)
    else:
        _draw_humanoid(surface, rect, main, accent, crown=False)


def draw_focus_object(surface: pygame.Surface, semantic: dict, palette, rng: random.Random):
    obj = str(semantic.get('object', '') or '').lower()
    color = palette[1]
    glow = palette[3]
    rect = pygame.Rect(int(surface.get_width() * 0.35), int(surface.get_height() * 0.52), int(surface.get_width() * 0.30), int(surface.get_height() * 0.24))
    if any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        _blocky_line(surface, color, (rect.left + 12, rect.bottom - 6), (rect.right - 10, rect.top + 8), 5)
        pygame.draw.line(surface, glow, (rect.centerx - 8, rect.centery + 10), (rect.centerx + 8, rect.centery + 10), 2)
    elif any(k in obj for k in ('codex', 'book', 'tablet')):
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.rect(surface, glow, rect.inflate(-10, -10), 2, border_radius=4)
    elif any(k in obj for k in ('shield', 'ward')):
        pts = [(rect.centerx, rect.top), (rect.right, rect.top + rect.h // 3), (rect.right - rect.w // 6, rect.bottom), (rect.left + rect.w // 6, rect.bottom), (rect.left, rect.top + rect.h // 3)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, glow, pts, 2)
    elif any(k in obj for k in ('crown', 'corona')):
        base = pygame.Rect(rect.left + 8, rect.centery, rect.w - 16, rect.h // 3)
        pygame.draw.rect(surface, color, base)
        peaks = [(base.left, base.top), (base.left + base.w // 4, base.top - 18), (base.centerx, base.top - 6), (base.right - base.w // 4, base.top - 18), (base.right, base.top)]
        pygame.draw.lines(surface, glow, False, peaks, 2)
    else:
        pygame.draw.circle(surface, color, rect.center, max(10, rect.w // 4))
        pygame.draw.circle(surface, glow, rect.center, max(12, rect.w // 4), 2)
