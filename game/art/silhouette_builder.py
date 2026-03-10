from __future__ import annotations

import random
import pygame


def _outline_mask(surface: pygame.Surface, color, passes: int = 1):
    mask = pygame.mask.from_surface(surface)
    if mask.count() <= 0:
        return
    for ox, oy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
        outline = mask.outline()
        if len(outline) > 1:
            shifted = [(x + ox, y + oy) for x, y in outline]
            pygame.draw.lines(surface, color, True, shifted, max(1, passes))


def _blocky_line(surface: pygame.Surface, color, a, b, width: int = 3):
    pygame.draw.line(surface, color, a, b, width)


def _draw_condor(surface: pygame.Surface, rect: pygame.Rect, color, accent):
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
    pygame.draw.line(surface, accent, (cx - rect.w // 5, cy - body_h // 2), (cx + rect.w // 5, cy - body_h // 2), 2)


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
    _blocky_line(surface, color, (cx - rect.w // 8, torso.y + rect.h // 10), (cx - rect.w // 4, torso.y + rect.h // 3), 6)
    _blocky_line(surface, color, (cx + rect.w // 8, torso.y + rect.h // 10), (cx + rect.w // 4, torso.y + rect.h // 3), 6)
    _blocky_line(surface, color, (cx - rect.w // 12, torso.bottom), (cx - rect.w // 7, rect.bottom - rect.h // 10), 6)
    _blocky_line(surface, color, (cx + rect.w // 12, torso.bottom), (cx + rect.w // 7, rect.bottom - rect.h // 10), 6)
    cape = [(cx - rect.w // 6, torso.y + rect.h // 12), (cx - rect.w // 3, rect.bottom - rect.h // 6), (cx + rect.w // 3, rect.bottom - rect.h // 6), (cx + rect.w // 6, torso.y + rect.h // 12)]
    pygame.draw.polygon(surface, (*accent[:3], 220) if len(accent) == 4 else accent, cape, 0)
    if crown:
        points = [(cx - rect.w // 10, top + rect.h // 18), (cx - rect.w // 18, top - 2), (cx, top + rect.h // 20), (cx + rect.w // 18, top - 2), (cx + rect.w // 10, top + rect.h // 18)]
        pygame.draw.lines(surface, accent, False, points, 3)


def _draw_beast(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    body = pygame.Rect(rect.x + rect.w // 5, rect.y + rect.h // 3, rect.w // 2, rect.h // 4)
    pygame.draw.rect(surface, color, body)
    head = pygame.Rect(body.right - rect.w // 12, body.y - rect.h // 10, rect.w // 5, rect.h // 6)
    pygame.draw.rect(surface, color, head)
    pygame.draw.rect(surface, accent, (head.x + 2, head.y + 2, max(2, head.w // 3), max(2, head.h // 4)))
    for lx in (body.x + rect.w // 16, body.x + rect.w // 5, body.right - rect.w // 6, body.right - rect.w // 12):
        _blocky_line(surface, color, (lx, body.bottom), (lx - 2, rect.bottom - rect.h // 10), 4)
    _blocky_line(surface, color, (body.x, body.y + rect.h // 10), (rect.x + rect.w // 12, rect.y + rect.h // 5), 3)


def draw_subject(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random):
    subject = ' '.join([
        str(semantic.get('subject', '') or ''),
        str(semantic.get('environment', '') or ''),
        ' '.join(getattr(r, 'cue', '') for r in refs[:3]),
    ]).lower()
    main = palette[2]
    accent = palette[3]
    rect = pygame.Rect(int(surface.get_width() * 0.18), int(surface.get_height() * 0.12), int(surface.get_width() * 0.64), int(surface.get_height() * 0.62))
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    if any(k in subject for k in ('condor', 'bird', 'ave')):
        _draw_condor(layer, rect, main, accent)
    elif any(k in subject for k in ('tree', 'gaia', 'arbol')):
        _draw_tree(layer, rect, main, accent)
    elif any(k in subject for k in ('castle', 'temple', 'sanctuary', 'ruins', 'throne', 'city')):
        _draw_castle(layer, rect, main, accent)
    elif any(k in subject for k in ('archon', 'arconte')):
        _draw_humanoid(layer, rect, main, accent, crown=True)
    elif any(k in subject for k in ('guardian', 'warrior', 'oracle', 'mage', 'figure', 'herald')):
        _draw_humanoid(layer, rect, main, accent, crown=False)
    elif any(k in subject for k in ('beast', 'puma', 'wolf', 'larva', 'sabueso')):
        _draw_beast(layer, rect, main, accent)
    else:
        _draw_humanoid(layer, rect, main, accent, crown=False)
    _outline_mask(layer, (18, 14, 22, 255), 2)
    surface.blit(layer, (0, 0))


def draw_focus_object(surface: pygame.Surface, semantic: dict, palette, rng: random.Random):
    obj = str(semantic.get('object', '') or '').lower()
    color = palette[1]
    glow = palette[3]
    rect = pygame.Rect(int(surface.get_width() * 0.34), int(surface.get_height() * 0.56), int(surface.get_width() * 0.32), int(surface.get_height() * 0.22))
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    if any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        _blocky_line(layer, color, (rect.left + 18, rect.bottom - 8), (rect.right - 12, rect.top + 8), 8)
        pygame.draw.line(layer, glow, (rect.centerx - 10, rect.centery + 12), (rect.centerx + 10, rect.centery + 12), 3)
    elif any(k in obj for k in ('codex', 'book', 'tablet')):
        pygame.draw.rect(layer, color, rect, border_radius=6)
        pygame.draw.rect(layer, glow, rect.inflate(-14, -14), 3, border_radius=4)
    elif any(k in obj for k in ('shield', 'ward')):
        pts = [(rect.centerx, rect.top), (rect.right, rect.top + rect.h // 3), (rect.right - rect.w // 6, rect.bottom), (rect.left + rect.w // 6, rect.bottom), (rect.left, rect.top + rect.h // 3)]
        pygame.draw.polygon(layer, color, pts)
        pygame.draw.polygon(layer, glow, pts, 3)
    elif any(k in obj for k in ('crown', 'corona')):
        base = pygame.Rect(rect.left + 8, rect.centery, rect.w - 16, rect.h // 3)
        pygame.draw.rect(layer, color, base)
        peaks = [(base.left, base.top), (base.left + base.w // 4, base.top - 18), (base.centerx, base.top - 6), (base.right - base.w // 4, base.top - 18), (base.right, base.top)]
        pygame.draw.lines(layer, glow, False, peaks, 3)
    elif any(k in obj for k in ('altar', 'brazier', 'relic', 'prism', 'anchor')):
        pygame.draw.rect(layer, color, rect.inflate(-20, -20), border_radius=8)
        pygame.draw.rect(layer, glow, (rect.centerx - 10, rect.top + 8, 20, rect.h - 24), 0, border_radius=4)
    else:
        pygame.draw.circle(layer, color, rect.center, max(14, rect.w // 4))
        pygame.draw.circle(layer, glow, rect.center, max(16, rect.w // 4), 3)
    _outline_mask(layer, (18, 14, 22, 255), 2)
    surface.blit(layer, (0, 0))
