from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path
import pygame
from game.art.art_reference_catalog import iter_category_entries
from game.art.secondary_object_library import resolve_secondary_object
from game.core.paths import art_reference_dir


def _ref_stem(value: str) -> str:
    return str(value or '').strip().lower().replace('.png', '').replace('.jpg', '').replace('.jpeg', '')


def _outline_mask(surface: pygame.Surface, color, passes: int = 1):
    mask = pygame.mask.from_surface(surface)
    if mask.count() <= 0:
        return
    outline = mask.outline()
    if len(outline) <= 1:
        return
    spread = max(1, passes)
    for radius in range(1, spread + 1):
        width = max(1, spread - radius + 1)
        for ox, oy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius), (-radius, -radius), (radius, -radius), (-radius, radius), (radius, radius)):
            shifted = [(x + ox, y + oy) for x, y in outline]
            pygame.draw.lines(surface, color, True, shifted, width)


def _blocky_line(surface: pygame.Surface, color, a, b, width: int = 3):
    pygame.draw.line(surface, color, a, b, width)


def _scaled(surface: pygame.Surface, value: int) -> int:
    base = max(surface.get_width() / 1920.0, surface.get_height() / 1080.0)
    return max(1, int(value * base))


def _rgba(color, alpha: int):
    return (int(color[0]), int(color[1]), int(color[2]), max(0, min(255, int(alpha))))


@lru_cache(maxsize=128)
def _reference_path_lookup(category: str, needle: str) -> str:
    root = Path(art_reference_dir())
    needle_low = str(needle or '').strip().lower()
    if not needle_low:
        return ''
    for entry in iter_category_entries(root, category):
        name = entry.path.name.lower()
        stem = entry.path.stem.lower()
        if needle_low == name or needle_low == stem:
            return str(entry.path)
    for entry in iter_category_entries(root, category):
        name = entry.path.name.lower()
        stem = entry.path.stem.lower()
        if needle_low in name or needle_low in stem:
            return str(entry.path)
    return ''


def _pick_subject_reference(refs: list, semantic: dict) -> Path | None:
    explicit = _ref_stem(semantic.get('subject_ref', ''))
    for candidate in (explicit,):
        if candidate:
            for category in ('subjects', 'creatures', 'enemies'):
                found = _reference_path_lookup(category, candidate)
                if found:
                    return Path(found)
    for ref in refs:
        category = str(getattr(ref, 'category', '') or '').lower()
        if category in {'subjects', 'creatures', 'enemies'}:
            return Path(ref.path)
    subject = str(semantic.get('subject', '') or '').lower().replace(',', ' ')
    for token in subject.split():
        if len(token) < 4:
            continue
        for category in ('subjects', 'creatures', 'enemies'):
            found = _reference_path_lookup(category, token)
            if found:
                return Path(found)
    return None


def _pick_object_reference(semantic: dict, refs: list) -> Path | None:
    explicit = _ref_stem(semantic.get('object_ref', ''))
    if explicit:
        found = _reference_path_lookup('weapons', explicit)
        if found:
            return Path(found)
    for ref in refs:
        category = str(getattr(ref, 'category', '') or '').lower()
        if category == 'weapons':
            return Path(ref.path)
    obj = str(semantic.get('object', '') or '').lower().replace(',', ' ')
    for token in obj.split():
        if len(token) < 4:
            continue
        found = _reference_path_lookup('weapons', token)
        if found:
            return Path(found)
    kind = str(semantic.get('object_kind', '') or '').lower().replace(' ', '_')
    for token in (kind,):
        if token:
            found = _reference_path_lookup('weapons', token)
            if found:
                return Path(found)
    return None


def _corner_avg(surf: pygame.Surface) -> tuple[int, int, int]:
    w, h = surf.get_size()
    pts = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2),
    ]
    rs = gs = bs = 0
    for x, y in pts:
        c = surf.get_at((max(0, min(w - 1, x)), max(0, min(h - 1, y))))
        rs += int(c.r)
        gs += int(c.g)
        bs += int(c.b)
    n = len(pts)
    return (rs // n, gs // n, bs // n)


def _make_reference_cutout(path: Path, target_size: tuple[int, int], palette_main, palette_accent) -> pygame.Surface | None:
    try:
        src = pygame.image.load(str(path)).convert_alpha()
    except Exception:
        return None
    w, h = src.get_size()
    if w <= 8 or h <= 8:
        return None
    bg = _corner_avg(src)
    matte = pygame.Surface((w, h), pygame.SRCALPHA)
    kept = 0
    min_x = w
    min_y = h
    max_x = 0
    max_y = 0
    for x in range(w):
        for y in range(h):
            c = src.get_at((x, y))
            dist = abs(int(c.r) - bg[0]) + abs(int(c.g) - bg[1]) + abs(int(c.b) - bg[2])
            lum = (int(c.r) + int(c.g) + int(c.b)) // 3
            alpha = 0
            if dist > 54:
                alpha = min(255, max(0, int((dist - 42) * 2.0)))
            elif lum < 120 and dist > 24:
                alpha = min(210, int((dist - 18) * 1.8))
            if alpha > 10:
                matte.set_at((x, y), (c.r, c.g, c.b, alpha))
                kept += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if kept <= (w * h) * 0.025 or max_x <= min_x or max_y <= min_y:
        return None
    pad_x = max(4, (max_x - min_x) // 18)
    pad_y = max(4, (max_y - min_y) // 18)
    crop = pygame.Rect(max(0, min_x - pad_x), max(0, min_y - pad_y), min(w - max(0, min_x - pad_x), (max_x - min_x) + pad_x * 2 + 1), min(h - max(0, min_y - pad_y), (max_y - min_y) + pad_y * 2 + 1))
    cropped = pygame.Surface(crop.size, pygame.SRCALPHA)
    cropped.blit(matte, (0, 0), crop)
    tw, th = target_size
    scale = min((tw * 0.92) / max(1, crop.w), (th * 0.92) / max(1, crop.h))
    scaled = pygame.transform.smoothscale(cropped, (max(1, int(crop.w * scale)), max(1, int(crop.h * scale)))).convert_alpha()
    out = pygame.Surface(target_size, pygame.SRCALPHA)
    ox = (tw - scaled.get_width()) // 2
    oy = th - scaled.get_height() - max(0, th // 20)
    shadow = pygame.Surface(target_size, pygame.SRCALPHA)
    shadow.blit(scaled, (ox + max(4, tw // 80), oy + max(4, th // 80)))
    shadow.fill((0, 0, 0, 90), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(shadow, (0, 0))
    tinted = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
    sw, sh = scaled.get_size()
    for sx in range(sw):
        for sy in range(sh):
            c = scaled.get_at((sx, sy))
            if c.a <= 8:
                continue
            lum = (int(c.r) + int(c.g) + int(c.b)) // 3
            mix = lum / 255.0
            rr = int(palette_main[0] * (0.72 + mix * 0.16))
            gg = int(palette_main[1] * (0.72 + mix * 0.16))
            bb = int(palette_main[2] * (0.72 + mix * 0.16))
            aa = min(255, max(38, int(c.a * 0.92)))
            tinted.set_at((sx, sy), (rr, gg, bb, aa))
    accent_pass = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    accent_pass.fill((palette_accent[0], palette_accent[1], palette_accent[2], 16))
    tinted.blit(accent_pass, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    out.blit(tinted, (ox, oy))
    _outline_mask(out, (18, 14, 22, 255), max(2, min(target_size) // 180))
    return out


def _blit_reference_subject(surface: pygame.Surface, rect: pygame.Rect, ref_path: Path | None, palette, semantic: dict) -> bool:
    if not ref_path:
        return False
    cutout = _make_reference_cutout(ref_path, (rect.w, rect.h), palette[2], palette[3])
    if cutout is None:
        return False
    frame = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    frame.blit(cutout, rect.topleft)
    surface.blit(frame, (0, 0))
    return True


def _blit_reference_object(surface: pygame.Surface, rect: pygame.Rect, ref_path: Path | None, palette) -> bool:
    if not ref_path:
        return False
    cutout = _make_reference_cutout(ref_path, (rect.w, rect.h), palette[1], palette[3])
    if cutout is None:
        return False
    frame = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    frame.blit(cutout, rect.topleft)
    surface.blit(frame, (0, 0))
    return True


def _draw_stage_shadow(surface: pygame.Surface, rect: pygame.Rect, alpha: int = 112):
    shadow = pygame.Rect(rect.x + rect.w // 8, rect.bottom - rect.h // 10, rect.w * 3 // 4, max(_scaled(surface, 26), rect.h // 8))
    pygame.draw.ellipse(surface, (0, 0, 0, alpha), shadow)


def _draw_subject_staging(surface: pygame.Surface, rect: pygame.Rect, accent, semantic: dict):
    scene = str(semantic.get('scene_type', '') or '').lower()
    env = str(semantic.get('environment', '') or '').lower()
    halo = rect.inflate(rect.w // 4, rect.h // 5)
    halo.y -= rect.h // 16
    pygame.draw.ellipse(surface, _rgba(accent, 26), halo)
    if any(k in scene for k in ('ritual', 'duel', 'defense')):
        band = pygame.Rect(rect.centerx - rect.w // 3, rect.bottom - rect.h // 8, rect.w * 2 // 3, max(_scaled(surface, 32), rect.h // 12))
        pygame.draw.rect(surface, _rgba(accent, 64), band, border_radius=max(6, _scaled(surface, 12)))
    if any(k in env for k in ('throne', 'citadel', 'temple', 'sanctuary', 'altar')):
        backplate = pygame.Rect(rect.centerx - rect.w // 5, rect.y + rect.h // 10, rect.w * 2 // 5, rect.h * 3 // 5)
        pygame.draw.rect(surface, _rgba(accent, 34), backplate, border_radius=max(8, _scaled(surface, 14)))


def _draw_humanoid_details(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    cx = rect.centerx
    chest = pygame.Rect(cx - rect.w // 10, rect.y + rect.h // 3, rect.w // 5, rect.h // 5)
    belt = pygame.Rect(cx - rect.w // 8, rect.y + rect.h // 2, rect.w // 4, max(_scaled(surface, 16), rect.h // 18))
    pygame.draw.rect(surface, accent, chest, border_radius=max(4, _scaled(surface, 8)))
    pygame.draw.rect(surface, color, chest.inflate(-max(4, chest.w // 5), -max(4, chest.h // 5)), border_radius=max(3, _scaled(surface, 6)))
    pygame.draw.rect(surface, accent, belt, border_radius=max(4, _scaled(surface, 8)))
    pygame.draw.line(surface, accent, (cx, rect.y + rect.h // 5), (cx, rect.bottom - rect.h // 6), max(2, _scaled(surface, 6)))


def _draw_object_staging(surface: pygame.Surface, rect: pygame.Rect, glow, semantic: dict):
    band = pygame.Rect(rect.x - rect.w // 10, rect.centery - rect.h // 6, rect.w + rect.w // 5, rect.h // 2)
    pygame.draw.ellipse(surface, _rgba(glow, 28), band)
    if any(k in str(semantic.get('scene_type', '') or '').lower() for k in ('ritual', 'defense')):
        base = pygame.Rect(rect.centerx - rect.w // 3, rect.bottom - rect.h // 10, rect.w * 2 // 3, max(_scaled(surface, 20), rect.h // 10))
        pygame.draw.rect(surface, _rgba(glow, 48), base, border_radius=max(6, _scaled(surface, 10)))


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
    gate = pygame.Rect(base.centerx - rect.w // 10, base.bottom - rect.h // 4, rect.w // 5, rect.h // 4)
    pygame.draw.rect(surface, accent, gate, border_radius=3)


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
    else:
        pygame.draw.rect(surface, accent, (cx - rect.w // 14, torso.y + rect.h // 8, rect.w // 7, rect.h // 7), border_radius=3)


def _draw_beast(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    body = pygame.Rect(rect.x + rect.w // 5, rect.y + rect.h // 3, rect.w // 2, rect.h // 4)
    pygame.draw.rect(surface, color, body)
    head = pygame.Rect(body.right - rect.w // 12, body.y - rect.h // 10, rect.w // 5, rect.h // 6)
    pygame.draw.rect(surface, color, head)
    pygame.draw.rect(surface, accent, (head.x + 2, head.y + 2, max(2, head.w // 3), max(2, head.h // 4)))
    for lx in (body.x + rect.w // 16, body.x + rect.w // 5, body.right - rect.w // 6, body.right - rect.w // 12):
        _blocky_line(surface, color, (lx, body.bottom), (lx - 2, rect.bottom - rect.h // 10), 4)
    _blocky_line(surface, color, (body.x, body.y + rect.h // 10), (rect.x + rect.w // 12, rect.y + rect.h // 5), 3)


def _draw_oracle_totem(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    spine = pygame.Rect(rect.centerx - rect.w // 12, rect.y + rect.h // 8, rect.w // 6, rect.h * 3 // 4)
    pygame.draw.rect(surface, color, spine, border_radius=6)
    pygame.draw.circle(surface, accent, (rect.centerx, rect.y + rect.h // 4), rect.w // 8)
    pygame.draw.circle(surface, color, (rect.centerx, rect.y + rect.h // 4), rect.w // 12)
    pygame.draw.rect(surface, accent, (rect.centerx - rect.w // 5, rect.centery, rect.w * 2 // 5, rect.h // 10), border_radius=4)
    pygame.draw.rect(surface, accent, (rect.centerx - rect.w // 4, rect.bottom - rect.h // 5, rect.w // 2, rect.h // 10), border_radius=4)


def _draw_weapon_bearer(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    _draw_humanoid(surface, rect, color, accent, crown=False)
    cx = rect.centerx
    top = rect.y + rect.h // 8
    torso_y = top + rect.h // 5
    _blocky_line(surface, accent, (cx - rect.w // 10, torso_y + rect.h // 6), (cx + rect.w // 3, rect.y + rect.h // 2), 10)
    _blocky_line(surface, accent, (cx + rect.w // 3, rect.y + rect.h // 2), (cx + rect.w // 3, rect.y + rect.h // 8), 5)
    pygame.draw.polygon(surface, accent, [
        (cx + rect.w // 3, rect.y + rect.h // 8 - 10),
        (cx + rect.w // 3 + 10, rect.y + rect.h // 8 + 2),
        (cx + rect.w // 3 - 10, rect.y + rect.h // 8 + 2),
    ])


def _draw_hyperborean_champion(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    _draw_weapon_bearer(surface, rect, color, accent)
    cx = rect.centerx
    pygame.draw.rect(surface, accent, (cx - rect.w // 5, rect.y + rect.h // 4, rect.w * 2 // 5, rect.h // 10), border_radius=4)
    pygame.draw.rect(surface, accent, (cx - rect.w // 12, rect.y + rect.h // 10, rect.w // 6, rect.h // 10), border_radius=4)


def _draw_guardian_bearer(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    _draw_humanoid(surface, rect, color, accent, crown=False)
    shield = pygame.Rect(rect.centerx + rect.w // 14, rect.centery - rect.h // 12, rect.w // 3, rect.h // 2)
    pts = [
        (shield.centerx, shield.top),
        (shield.right, shield.top + shield.h // 3),
        (shield.right - shield.w // 7, shield.bottom),
        (shield.left + shield.w // 7, shield.bottom),
        (shield.left, shield.top + shield.h // 3),
    ]
    pygame.draw.polygon(surface, accent, pts)
    pygame.draw.polygon(surface, color, pts, 3)


def _draw_archon_throne(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    throne = pygame.Rect(rect.x + rect.w // 6, rect.y + rect.h // 3, rect.w * 2 // 3, rect.h // 2)
    pygame.draw.rect(surface, color, throne, border_radius=6)
    pygame.draw.rect(surface, accent, (throne.x + throne.w // 3, throne.y - rect.h // 7, throne.w // 3, rect.h // 7), border_radius=4)
    pygame.draw.rect(surface, accent, (throne.x + throne.w // 6, throne.bottom - rect.h // 8, throne.w * 2 // 3, rect.h // 8), border_radius=4)
    _draw_humanoid(surface, pygame.Rect(rect.x + rect.w // 6, rect.y + rect.h // 6, rect.w * 2 // 3, rect.h * 4 // 5), color, accent, crown=True)
    pygame.draw.circle(surface, accent, (rect.centerx, rect.y + rect.h // 5), rect.w // 8, 4)
    pygame.draw.rect(surface, accent, (rect.centerx - rect.w // 7, rect.centery + rect.h // 8, rect.w // 3, rect.h // 10), border_radius=5)


def _draw_warrior_foreground(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    body = pygame.Rect(rect.centerx - rect.w // 7, rect.y + rect.h // 8, rect.w // 3, rect.h * 11 // 18)
    pygame.draw.rect(surface, color, body, border_radius=10)
    pygame.draw.circle(surface, color, (rect.centerx, rect.y + rect.h // 7), rect.w // 9)
    shoulder = pygame.Rect(rect.centerx - rect.w // 5, rect.y + rect.h // 5, rect.w * 2 // 5, rect.h // 10)
    pygame.draw.rect(surface, accent, shoulder, border_radius=5)
    cloak = [
        (body.left + 4, body.y + rect.h // 10),
        (rect.centerx - rect.w // 3, rect.bottom - rect.h // 7),
        (rect.centerx + rect.w // 3, rect.bottom - rect.h // 7),
        (body.right - 4, body.y + rect.h // 10),
    ]
    pygame.draw.polygon(surface, (*accent[:3], 210) if len(accent) == 4 else accent, cloak)
    _blocky_line(surface, color, (body.left + 10, body.y + rect.h // 5), (rect.centerx - rect.w // 4, rect.centery), 10)
    _blocky_line(surface, color, (body.right - 10, body.y + rect.h // 5), (rect.centerx + rect.w // 6, rect.centery), 10)
    _blocky_line(surface, color, (rect.centerx - rect.w // 16, body.bottom), (rect.centerx - rect.w // 10, rect.bottom - rect.h // 14), 10)
    _blocky_line(surface, color, (rect.centerx + rect.w // 16, body.bottom), (rect.centerx + rect.w // 10, rect.bottom - rect.h // 14), 10)
    blade_start = (rect.centerx - rect.w // 5, rect.bottom - rect.h // 5)
    blade_end = (rect.centerx + rect.w // 3, rect.y + rect.h // 5)
    if variant == 'guardian_03':
        body = pygame.Rect(rect.centerx - rect.w // 6, rect.y + rect.h // 7, rect.w // 3, rect.h * 5 // 8)
        pygame.draw.rect(surface, color, body, border_radius=12)
        helm = [(rect.centerx - rect.w // 10, rect.y + rect.h // 8), (rect.centerx, rect.y + rect.h // 16), (rect.centerx + rect.w // 10, rect.y + rect.h // 8)]
        pygame.draw.polygon(surface, accent, helm)
        blade_start = (rect.centerx - rect.w // 4, rect.bottom - rect.h // 6)
        blade_end = (rect.centerx + rect.w // 3, rect.y + rect.h // 4)
    elif variant == 'guardian_02':
        blade_start = (rect.centerx - rect.w // 6, rect.bottom - rect.h // 4)
        blade_end = (rect.centerx + rect.w // 4, rect.y + rect.h // 4)
    _blocky_line(surface, accent, blade_start, blade_end, 20)
    _blocky_line(surface, color, (blade_start[0] + 10, blade_start[1] - 10), (blade_end[0] - 8, blade_end[1] + 8), 4)
    pygame.draw.polygon(surface, accent, [
        (blade_end[0], blade_end[1] - 18),
        (blade_end[0] + 16, blade_end[1] + 6),
        (blade_end[0] - 16, blade_end[1] + 6),
    ])


def _draw_hyperborean_foreground(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    _draw_warrior_foreground(surface, rect, color, accent, variant=variant or 'guardian_02')
    pygame.draw.rect(surface, accent, (rect.centerx - rect.w // 5, rect.y + rect.h // 5, rect.w * 2 // 5, rect.h // 10), border_radius=4)
    pygame.draw.rect(surface, accent, (rect.centerx - rect.w // 14, rect.y + rect.h // 9, rect.w // 7, rect.h // 11), border_radius=4)
    haft_start = (rect.centerx + rect.w // 18, rect.bottom - rect.h // 5)
    haft_end = (rect.centerx + rect.w // 3, rect.y + rect.h // 5)
    _blocky_line(surface, accent, haft_start, haft_end, 18)
    pygame.draw.polygon(surface, accent, [
        (haft_end[0], haft_end[1]),
        (haft_end[0] + 28, haft_end[1] - 18),
        (haft_end[0] + 18, haft_end[1] + 4),
    ])
    pygame.draw.polygon(surface, accent, [
        (haft_end[0], haft_end[1]),
        (haft_end[0] + 28, haft_end[1] + 18),
        (haft_end[0] + 18, haft_end[1] - 4),
    ])


def _draw_archon_foreground(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    throne = pygame.Rect(rect.x + rect.w // 10, rect.y + rect.h // 3, rect.w * 4 // 5, rect.h // 2)
    pygame.draw.rect(surface, color, throne, border_radius=8)
    pygame.draw.rect(surface, accent, (throne.x + throne.w // 3, throne.y - rect.h // 8, throne.w // 3, rect.h // 8), border_radius=4)
    body = pygame.Rect(rect.centerx - rect.w // 9, rect.y + rect.h // 8, rect.w // 3, rect.h * 11 // 18)
    pygame.draw.rect(surface, color, body, border_radius=10)
    pygame.draw.circle(surface, color, (rect.centerx, rect.y + rect.h // 7), rect.w // 9)
    pygame.draw.polygon(surface, accent, [
        (rect.centerx - rect.w // 11, rect.y + rect.h // 10),
        (rect.centerx, rect.y + rect.h // 16),
        (rect.centerx + rect.w // 11, rect.y + rect.h // 10),
    ])
    cloak = [
        (body.left + 6, body.y + rect.h // 10),
        (rect.centerx - rect.w // 4, rect.bottom - rect.h // 7),
        (rect.centerx + rect.w // 4, rect.bottom - rect.h // 7),
        (body.right - 6, body.y + rect.h // 10),
    ]
    pygame.draw.polygon(surface, (*accent[:3], 210) if len(accent) == 4 else accent, cloak)
    _blocky_line(surface, color, (body.left + 8, body.y + rect.h // 5), (rect.centerx - rect.w // 4, rect.centery), 10)
    _blocky_line(surface, color, (body.right - 8, body.y + rect.h // 6), (rect.centerx + rect.w // 4, rect.y + rect.h // 3), 10)
    tablet = pygame.Rect(rect.centerx + rect.w // 10, rect.centery - rect.h // 12, rect.w // 4, rect.h // 3)
    if variant == 'arconte_04':
        body = pygame.Rect(rect.centerx - rect.w // 8, rect.y + rect.h // 7, rect.w // 3, rect.h * 11 // 18)
        pygame.draw.rect(surface, color, body, border_radius=12)
        crown = [(rect.centerx - rect.w // 8, rect.y + rect.h // 9), (rect.centerx - rect.w // 16, rect.y + rect.h // 18), (rect.centerx, rect.y + rect.h // 10), (rect.centerx + rect.w // 16, rect.y + rect.h // 18), (rect.centerx + rect.w // 8, rect.y + rect.h // 9)]
        pygame.draw.polygon(surface, accent, crown)
        tablet = pygame.Rect(rect.centerx + rect.w // 9, rect.centery - rect.h // 10, rect.w // 3, rect.h // 3)
    pygame.draw.rect(surface, accent, tablet, border_radius=6)
    pygame.draw.circle(surface, accent, (rect.centerx, rect.y + rect.h // 5), rect.w // 8, 4)
    pygame.draw.line(surface, color, (tablet.centerx, tablet.y + 8), (tablet.centerx, tablet.bottom - 8), 4)



SUBJECT_SILHOUETTE_LIBRARY = {
    'mage': ('oracle_totem',),
    'warrior': ('weapon_bearer', 'warrior_foreground', 'hyperborean_foreground'),
    'archon': ('archon_throne', 'archon_foreground', 'archon_beast'),
    'guardian': ('guardian_bearer', 'weapon_bearer', 'warrior_foreground'),
    'animal': ('condor', 'beast', 'tree'),
    'temple': ('castle',),
}

OBJECT_SILHOUETTE_LIBRARY = {
    'relic': ('codex', 'seal_tablet', 'altar', 'seal', 'crown'),
    'weapon': ('weapon', 'greatsword', 'solar_axe'),
    'shield': ('shield',),
}

SUBJECT_KIND_TO_TEMPLATE = {
    'oracle_totem': 'mage',
    'weapon_bearer': 'warrior',
    'warrior_foreground': 'warrior',
    'hyperborean_champion': 'warrior',
    'hyperborean_foreground': 'warrior',
    'guardian_bearer': 'guardian',
    'archon_throne': 'archon',
    'archon_foreground': 'archon',
    'archon_beast': 'archon',
}

OBJECT_KIND_TO_TEMPLATE = {
    'weapon': 'weapon',
    'greatsword': 'weapon',
    'solar_axe': 'weapon',
    'codex': 'relic',
    'altar': 'relic',
    'seal': 'relic',
    'seal_tablet': 'relic',
    'crown': 'relic',
    'shield': 'shield',
}


def silhouette_library_summary() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        'subject_categories': SUBJECT_SILHOUETTE_LIBRARY,
        'object_categories': OBJECT_SILHOUETTE_LIBRARY,
    }

def _subject_variant(semantic: dict) -> str:
    return _ref_stem(semantic.get('subject_ref', ''))


def _object_variant(semantic: dict) -> str:
    return _ref_stem(semantic.get('object_ref', ''))



def draw_subject(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random):
    kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    variant = _subject_variant(semantic)
    subject = ' '.join([
        str(semantic.get('subject', '') or ''),
        str(semantic.get('environment', '') or ''),
        ' '.join(getattr(r, 'cue', '') for r in refs[:3]),
    ]).lower()
    template_family = SUBJECT_KIND_TO_TEMPLATE.get(kind, '')
    main = (max(18, int(palette[2][0] * 0.88)), max(18, int(palette[2][1] * 0.88)), max(18, int(palette[2][2] * 0.88)))
    accent = palette[3]
    scene_type = str(semantic.get('scene_type', '') or '').lower()
    camera = str(semantic.get('camera', '') or '').lower()
    width_ratio = 0.60 if 'wide' in camera else 0.54 if 'close' in camera else 0.57
    height_ratio = 0.90 if 'duel' in scene_type or 'ritual' in scene_type else 0.94
    if template_family == 'animal' or any(k in subject for k in ('condor', 'bird', 'ave', 'beast', 'puma', 'wolf')):
        width_ratio = max(width_ratio, 0.64)
    rect = pygame.Rect(
        int(surface.get_width() * 0.5 - surface.get_width() * width_ratio / 2),
        int(surface.get_height() * 0.06),
        int(surface.get_width() * width_ratio),
        int(surface.get_height() * height_ratio),
    )
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    _draw_stage_shadow(layer, rect, alpha=124)
    _draw_subject_staging(layer, rect, accent, semantic)
    ref_path = _pick_subject_reference(refs, semantic)
    if kind == 'hyperborean_champion':
        _draw_hyperborean_champion(layer, rect, main, accent)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'hyperborean_foreground':
        _draw_hyperborean_foreground(layer, rect, main, accent, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'archon_beast':
        _draw_beast(layer, rect, main, accent)
        pygame.draw.circle(layer, accent, (rect.centerx + rect.w // 6, rect.centery - rect.h // 10), max(8, _scaled(surface, 10)))
    elif kind == 'archon_foreground':
        _draw_archon_foreground(layer, rect, main, accent, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'guardian_bearer':
        _draw_guardian_bearer(layer, rect, main, accent)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'warrior_foreground':
        _draw_warrior_foreground(layer, rect, main, accent, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif any(k in subject for k in ('tree', 'gaia', 'arbol')):
        _draw_tree(layer, rect, main, accent)
    elif template_family == 'animal' or any(k in subject for k in ('condor', 'bird', 'ave')):
        _draw_condor(layer, rect, main, accent)
    elif template_family == 'temple' or any(k in subject for k in ('castle', 'temple', 'sanctuary', 'ruins', 'throne', 'city')):
        _draw_castle(layer, rect, main, accent)
    elif template_family == 'archon' or any(k in subject for k in ('archon', 'arconte', 'throne-realm')):
        _draw_archon_throne(layer, rect, main, accent)
        _draw_humanoid_details(layer, rect, main, accent)
    elif template_family == 'mage' or any(k in subject for k in ('oracle', 'visionary', 'seer')):
        _draw_oracle_totem(layer, rect, main, accent)
    elif template_family in {'guardian', 'warrior'} or any(k in subject for k in ('guardian', 'warrior', 'champion')):
        _draw_weapon_bearer(layer, rect, main, accent)
        _draw_humanoid_details(layer, rect, main, accent)
    elif any(k in subject for k in ('mage', 'figure', 'herald')):
        _draw_humanoid(layer, rect, main, accent, crown=False)
        _draw_humanoid_details(layer, rect, main, accent)
    elif any(k in subject for k in ('beast', 'puma', 'wolf', 'larva', 'sabueso')):
        _draw_beast(layer, rect, main, accent)
    else:
        _draw_humanoid(layer, rect, main, accent, crown=False)
        _draw_humanoid_details(layer, rect, main, accent)
    has_ref_subject = _blit_reference_subject(layer, rect, ref_path, palette, semantic)
    if has_ref_subject:
        glaze = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(glaze, (*accent, 18), rect, border_radius=max(10, _scaled(surface, 12)))
        layer.blit(glaze, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    _outline_mask(layer, (18, 14, 22, 255), max(2, _scaled(surface, 4)))
    surface.blit(layer, (0, 0))


def draw_focus_object(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random):
    kind = str(semantic.get('object_kind', '') or '').lower().replace(' ', '_')
    variant = _object_variant(semantic)
    obj = str(semantic.get('object', '') or '').lower()
    preset = resolve_secondary_object(kind, obj)
    template_family = OBJECT_KIND_TO_TEMPLATE.get(kind, '') or preset.family
    color = palette[1]
    glow = palette[3]
    ratio = max(0.22, min(0.40, float(preset.frame_ratio)))
    rect_w = int(surface.get_width() * max(0.30, ratio * 1.20))
    rect_h = int(surface.get_height() * max(0.40, ratio * 1.34))
    if template_family == 'weapon' or kind in {'greatsword', 'solar_axe'} or any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        rect_w = int(rect_w * 1.62)
        rect_h = int(rect_h * 1.24)
    rect = pygame.Rect(
        int(surface.get_width() * 0.60 - rect_w * 0.5),
        int(surface.get_height() * 0.54 - rect_h * 0.4),
        rect_w,
        rect_h,
    )
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    _draw_object_staging(layer, rect, glow, semantic)
    ref_path = _pick_object_reference(semantic, refs)
    if template_family == 'weapon' or kind in {'greatsword', 'solar_axe'} or any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        shaft_a = (rect.left + rect.w // 5, rect.bottom - rect.h // 9)
        shaft_b = (rect.right - rect.w // 4, rect.top + rect.h // 8)
        _blocky_line(layer, _rgba(glow, 92), shaft_a, shaft_b, max(26, _scaled(surface, 42)))
        _blocky_line(layer, color, shaft_a, shaft_b, max(18, _scaled(surface, 28)))
        pygame.draw.line(layer, glow, (rect.centerx - rect.w // 9, rect.centery + rect.h // 10), (rect.centerx + rect.w // 12, rect.centery + rect.h // 10), max(4, _scaled(surface, 8)))
        pygame.draw.line(layer, glow, (shaft_b[0], shaft_b[1] + _scaled(surface, 8)), (shaft_b[0], shaft_b[1] - rect.h // 10), max(3, _scaled(surface, 6)))
        if kind == 'solar_axe' or variant == 'espada_03':
            head = (shaft_b[0], shaft_b[1] + _scaled(surface, 8))
            left_blade = [
                (head[0], head[1]),
                (head[0] + rect.w // 4, head[1] - rect.h // 10),
                (head[0] + rect.w // 5, head[1] + rect.h // 20),
                (head[0] + rect.w // 10, head[1] + rect.h // 6),
            ]
            right_blade = [
                (head[0], head[1]),
                (head[0] + rect.w // 4, head[1] + rect.h // 10),
                (head[0] + rect.w // 5, head[1] - rect.h // 20),
                (head[0] + rect.w // 10, head[1] - rect.h // 6),
            ]
            pygame.draw.polygon(layer, glow, left_blade)
            pygame.draw.polygon(layer, glow, right_blade)
            pygame.draw.circle(layer, glow, head, max(8, _scaled(surface, 12)))
        if kind == 'greatsword' or variant == 'espada_02':
            blade_poly = [
                (shaft_b[0], shaft_b[1] - rect.h // 10),
                (shaft_b[0] + rect.w // 8, shaft_b[1] + rect.h // 16),
                (shaft_a[0] + rect.w // 5, shaft_a[1] - rect.h // 8),
                (shaft_a[0] - rect.w // 18, shaft_a[1] - rect.h // 4),
            ]
            pygame.draw.polygon(layer, glow, blade_poly)
            pommel = (shaft_a[0] + rect.w // 20, shaft_a[1] - rect.h // 12)
            pygame.draw.circle(layer, glow, pommel, max(10, _scaled(surface, 16)), max(3, _scaled(surface, 4)))
            pygame.draw.line(layer, glow, (pommel[0], pommel[1] - rect.h // 18), (pommel[0], pommel[1] + rect.h // 10), max(3, _scaled(surface, 4)))
    elif kind == 'codex' or any(k in obj for k in ('codex', 'book', 'tablet')):
        pygame.draw.rect(layer, color, rect, border_radius=max(8, _scaled(surface, 10)))
        pygame.draw.rect(layer, glow, rect.inflate(-max(12, _scaled(surface, 18)), -max(12, _scaled(surface, 18))), max(2, _scaled(surface, 4)), border_radius=max(6, _scaled(surface, 8)))
        pygame.draw.line(layer, glow, (rect.centerx, rect.y + rect.h // 6), (rect.centerx, rect.bottom - rect.h // 6), max(2, _scaled(surface, 4)))
    elif kind == 'seal_tablet':
        tab = rect.inflate(-max(20, _scaled(surface, 24)), -max(12, _scaled(surface, 14)))
        pygame.draw.rect(layer, color, tab, border_radius=max(8, _scaled(surface, 12)))
        pygame.draw.rect(layer, glow, tab, max(2, _scaled(surface, 4)), border_radius=max(8, _scaled(surface, 12)))
        pygame.draw.circle(layer, glow, (tab.centerx, tab.y + tab.h // 4), max(14, tab.w // 6), max(2, _scaled(surface, 4)))
        pygame.draw.line(layer, glow, (tab.centerx, tab.y + tab.h // 4 + _scaled(surface, 12)), (tab.centerx, tab.bottom - _scaled(surface, 16)), max(3, _scaled(surface, 5)))
        if variant == 'sellos_03':
            pygame.draw.circle(layer, glow, tab.center, max(18, tab.w // 5), max(2, _scaled(surface, 4)))
            pygame.draw.line(layer, glow, (tab.centerx - tab.w // 4, tab.centery), (tab.centerx + tab.w // 4, tab.centery), max(3, _scaled(surface, 4)))
    elif kind == 'shield' or any(k in obj for k in ('shield', 'ward')):
        pts = [(rect.centerx, rect.top), (rect.right, rect.top + rect.h // 3), (rect.right - rect.w // 6, rect.bottom), (rect.left + rect.w // 6, rect.bottom), (rect.left, rect.top + rect.h // 3)]
        pygame.draw.polygon(layer, color, pts)
        pygame.draw.polygon(layer, glow, pts, max(2, _scaled(surface, 4)))
        pygame.draw.line(layer, glow, (rect.centerx, rect.top + rect.h // 6), (rect.centerx, rect.bottom - rect.h // 7), max(2, _scaled(surface, 4)))
    elif kind == 'crown' or any(k in obj for k in ('crown', 'corona')):
        base = pygame.Rect(rect.left + _scaled(surface, 8), rect.centery, rect.w - _scaled(surface, 16), rect.h // 3)
        pygame.draw.rect(layer, color, base)
        peaks = [(base.left, base.top), (base.left + base.w // 4, base.top - _scaled(surface, 18)), (base.centerx, base.top - _scaled(surface, 6)), (base.right - base.w // 4, base.top - _scaled(surface, 18)), (base.right, base.top)]
        pygame.draw.lines(layer, glow, False, peaks, max(2, _scaled(surface, 4)))
    elif kind in {'altar', 'seal'} or any(k in obj for k in ('altar', 'brazier', 'relic', 'prism', 'anchor', 'seal')):
        body = rect.inflate(-max(16, _scaled(surface, 20)), -max(16, _scaled(surface, 20)))
        pygame.draw.rect(layer, color, body, border_radius=max(8, _scaled(surface, 10)))
        pygame.draw.rect(layer, glow, body, max(2, _scaled(surface, 4)), border_radius=max(8, _scaled(surface, 10)))
        pygame.draw.rect(layer, glow, (body.centerx - _scaled(surface, 8), body.top + _scaled(surface, 8), _scaled(surface, 16), body.h - _scaled(surface, 20)), 0, border_radius=max(4, _scaled(surface, 6)))
    else:
        pygame.draw.circle(layer, color, rect.center, max(14, rect.w // 4))
        pygame.draw.circle(layer, glow, rect.center, max(16, rect.w // 4), max(2, _scaled(surface, 4)))
    has_ref_object = _blit_reference_object(layer, rect, ref_path, palette)
    if has_ref_object:
        glow_pass = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(glow_pass, (*glow, 16), rect.inflate(max(8, _scaled(surface, 10)), max(8, _scaled(surface, 10))), border_radius=max(12, _scaled(surface, 14)))
        layer.blit(glow_pass, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    _outline_mask(layer, (18, 14, 22, 255), max(2, _scaled(surface, 4)))
    surface.blit(layer, (0, 0))
