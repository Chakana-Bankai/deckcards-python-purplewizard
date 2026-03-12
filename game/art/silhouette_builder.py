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

def _subject_directives(semantic: dict) -> dict[str, str]:
    parts = {
        'shape_language': str(semantic.get('shape_language', '') or 'balanced_fantasy').lower(),
        'pose_type': str(semantic.get('pose_type', '') or 'heroic_guard').lower(),
        'symbol_choice': str(semantic.get('symbol_choice', '') or 'none').lower(),
        'lighting_direction': str(semantic.get('lighting_direction', '') or 'left_soft').lower(),
        'aura_type': str(semantic.get('aura_type', '') or 'none').lower(),
        'environment_choice': str(semantic.get('environment_choice', '') or '').lower(),
    }


def _shape_adjust(parts: dict[str, object], rect: pygame.Rect, directives: dict[str, str]) -> dict[str, object]:
    pose = directives.get('pose_type', '')
    shape = directives.get('shape_language', '')
    cx = parts['cx']
    if shape == 'vertical_oppressive':
        parts['weapon_anchor'] = (cx + rect.w * 0.28, rect.y + rect.h * 0.42)
        parts['symbol_anchor'] = (cx, rect.y + rect.h * 0.14)
    elif shape == 'triangular_heroic':
        parts['weapon_anchor'] = (cx + rect.w * 0.20, rect.y + rect.h * 0.40)
        parts['symbol_anchor'] = (cx, rect.y + rect.h * 0.12)
    elif shape == 'calm_vertical':
        parts['weapon_anchor'] = (cx + rect.w * 0.16, rect.y + rect.h * 0.48)
        parts['symbol_anchor'] = (cx, rect.y + rect.h * 0.24)
    if pose == 'attack_ready':
        parts['weapon_anchor'] = (parts['weapon_anchor'][0] + rect.w * 0.06, parts['weapon_anchor'][1] - rect.h * 0.06)
    elif pose in {'ritual_invocation', 'calm_channeling'}:
        parts['symbol_anchor'] = (parts['symbol_anchor'][0], parts['symbol_anchor'][1] + rect.h * 0.04)
    return parts


def _lighting_glaze(surface: pygame.Surface, rect: pygame.Rect, directives: dict[str, str], accent):
    glaze = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    mode = directives.get('lighting_direction', 'left_soft')
    if mode == 'left_dawn':
        pts = [(rect.left - rect.w // 8, rect.top), (rect.centerx, rect.top), (rect.centerx - rect.w // 10, rect.bottom), (rect.left - rect.w // 10, rect.bottom)]
        _poly(glaze, _rgba(accent, 42), pts)
    elif mode == 'top_void':
        band = pygame.Rect(rect.centerx - rect.w // 6, rect.top - rect.h // 20, rect.w // 3, rect.h // 3)
        pygame.draw.ellipse(glaze, _rgba(accent, 30), band)
    elif mode == 'front_soft':
        panel = rect.inflate(-rect.w // 5, -rect.h // 6)
        pygame.draw.ellipse(glaze, _rgba(accent, 24), panel)
    else:
        pts = [(rect.left, rect.top), (rect.centerx, rect.top), (rect.centerx - rect.w // 12, rect.bottom), (rect.left + rect.w // 10, rect.bottom)]
        _poly(glaze, _rgba(accent, 26), pts)
    surface.blit(glaze, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def _draw_symbol_marker(surface: pygame.Surface, anchor, rect: pygame.Rect, directives: dict[str, str], accent):
    choice = directives.get('symbol_choice', 'none')
    if choice == 'none':
        return
    ax = int(anchor[0])
    ay = int(anchor[1])
    if choice == 'chakana_gate':
        size = max(18, rect.w // 10)
        pygame.draw.line(surface, accent, (ax - size, ay), (ax + size, ay), max(2, _scaled(surface, 4)))
        pygame.draw.line(surface, accent, (ax, ay - size), (ax, ay + size), max(2, _scaled(surface, 4)))
        pygame.draw.rect(surface, accent, (ax - size // 2, ay - size // 2, size, size), max(2, _scaled(surface, 3)))
    elif choice == 'solar_disc':
        pygame.draw.circle(surface, accent, (ax, ay), max(14, rect.w // 12), max(2, _scaled(surface, 4)))
    elif choice == 'ritual_seal':
        pygame.draw.circle(surface, accent, (ax, ay), max(16, rect.w // 11), max(2, _scaled(surface, 4)))
        pygame.draw.line(surface, accent, (ax - rect.w // 14, ay), (ax + rect.w // 14, ay), max(2, _scaled(surface, 3)))


def _draw_aura_marker(surface: pygame.Surface, rect: pygame.Rect, directives: dict[str, str], accent):
    aura = directives.get('aura_type', 'none')
    if aura == 'none':
        return
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    halo = rect.inflate(rect.w // 4, rect.h // 5)
    if aura == 'corruption_aura':
        pygame.draw.ellipse(layer, _rgba((accent[0], max(0, accent[1] // 2), accent[2]), 18), halo, max(2, _scaled(surface, 5)))
    elif aura == 'solar_aura':
        pygame.draw.ellipse(layer, _rgba((min(255, accent[0] + 24), min(255, accent[1] + 18), accent[2]), 22), halo, max(2, _scaled(surface, 5)))
    elif aura == 'mystic_aura':
        pygame.draw.ellipse(layer, _rgba(accent, 18), halo.inflate(-rect.w // 10, -rect.h // 10), max(2, _scaled(surface, 4)))
    surface.blit(layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


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
    return False


def _blit_reference_object(surface: pygame.Surface, rect: pygame.Rect, ref_path: Path | None, palette) -> bool:
    return False


def _draw_stage_shadow(surface: pygame.Surface, rect: pygame.Rect, alpha: int = 112):
    shadow = pygame.Rect(rect.x + rect.w // 8, rect.bottom - rect.h // 10, rect.w * 3 // 4, max(_scaled(surface, 26), rect.h // 8))
    pygame.draw.ellipse(surface, (0, 0, 0, alpha), shadow)


def _draw_subject_staging(surface: pygame.Surface, rect: pygame.Rect, accent, semantic: dict):
    scene = str(semantic.get('scene_type', '') or '').lower()
    env = str(semantic.get('environment', '') or '').lower()
    halo = rect.inflate(rect.w // 5, rect.h // 6)
    halo.y -= rect.h // 18
    core = halo.inflate(-max(20, rect.w // 7), -max(18, rect.h // 8))
    pygame.draw.ellipse(surface, (8, 6, 14, 64), halo)
    pygame.draw.ellipse(surface, _rgba(accent, 14), core)
    pygame.draw.ellipse(surface, _rgba(accent, 22), halo, max(2, _scaled(surface, 6)))
    if any(k in scene for k in ('ritual', 'duel', 'defense')):
        band = pygame.Rect(rect.centerx - rect.w // 3, rect.bottom - rect.h // 10, rect.w * 2 // 3, max(_scaled(surface, 28), rect.h // 13))
        pygame.draw.rect(surface, _rgba(accent, 34), band, border_radius=max(6, _scaled(surface, 12)))
    if any(k in env for k in ('throne', 'citadel', 'temple', 'sanctuary', 'altar')):
        backplate = pygame.Rect(rect.centerx - rect.w // 4, rect.y + rect.h // 7, rect.w // 2, rect.h * 3 // 5)
        pygame.draw.rect(surface, (10, 8, 18, 84), backplate, border_radius=max(8, _scaled(surface, 14)))
        pygame.draw.rect(surface, _rgba(accent, 24), backplate, max(2, _scaled(surface, 4)), border_radius=max(8, _scaled(surface, 14)))


def _draw_humanoid_details(surface: pygame.Surface, rect: pygame.Rect, color, accent):
    cx = rect.centerx
    chest = pygame.Rect(cx - rect.w // 10, rect.y + rect.h // 3, rect.w // 5, rect.h // 5)
    belt = pygame.Rect(cx - rect.w // 8, rect.y + rect.h // 2, rect.w // 4, max(_scaled(surface, 16), rect.h // 18))
    pygame.draw.rect(surface, accent, chest, border_radius=max(4, _scaled(surface, 8)))
    pygame.draw.rect(surface, color, chest.inflate(-max(4, chest.w // 5), -max(4, chest.h // 5)), border_radius=max(3, _scaled(surface, 6)))
    pygame.draw.rect(surface, accent, belt, border_radius=max(4, _scaled(surface, 8)))
    pygame.draw.line(surface, accent, (cx, rect.y + rect.h // 5), (cx, rect.bottom - rect.h // 6), max(2, _scaled(surface, 6)))


def _draw_object_staging(surface: pygame.Surface, rect: pygame.Rect, glow, semantic: dict):
    band = pygame.Rect(rect.x - rect.w // 14, rect.centery - rect.h // 7, rect.w + rect.w // 7, rect.h // 3)
    pygame.draw.ellipse(surface, _rgba(glow, 16), band)
    if any(k in str(semantic.get('scene_type', '') or '').lower() for k in ('ritual', 'defense')):
        base = pygame.Rect(rect.centerx - rect.w // 4, rect.bottom - rect.h // 12, rect.w // 2, max(_scaled(surface, 16), rect.h // 12))
        pygame.draw.rect(surface, _rgba(glow, 28), base, border_radius=max(6, _scaled(surface, 10)))


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


def _poly(surface: pygame.Surface, color, points):
    pygame.draw.polygon(surface, color, [(int(x), int(y)) for x, y in points])


def _line(surface: pygame.Surface, color, a, b, width: int):
    pygame.draw.line(surface, color, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), max(1, int(width)))


def _build_humanoid_parts(rect: pygame.Rect, archetype: str = 'humanoid', directives: dict[str, str] | None = None) -> dict[str, object]:
    cx = rect.centerx
    top = rect.top
    bottom = rect.bottom
    directives = directives or {}
    if archetype == 'archon':
        head = pygame.Rect(cx - rect.w // 9, top + rect.h // 12, rect.w // 4, rect.h // 7)
        torso = [
            (cx - rect.w * 0.18, top + rect.h * 0.22),
            (cx + rect.w * 0.18, top + rect.h * 0.22),
            (cx + rect.w * 0.24, top + rect.h * 0.52),
            (cx + rect.w * 0.12, top + rect.h * 0.80),
            (cx - rect.w * 0.12, top + rect.h * 0.80),
            (cx - rect.w * 0.24, top + rect.h * 0.52),
        ]
        cloak = [
            (cx - rect.w * 0.28, top + rect.h * 0.20),
            (cx - rect.w * 0.36, top + rect.h * 0.54),
            (cx - rect.w * 0.24, bottom - rect.h * 0.05),
            (cx + rect.w * 0.24, bottom - rect.h * 0.05),
            (cx + rect.w * 0.36, top + rect.h * 0.54),
            (cx + rect.w * 0.28, top + rect.h * 0.20),
        ]
        lead_arm = [
            (cx + rect.w * 0.12, top + rect.h * 0.32),
            (cx + rect.w * 0.34, top + rect.h * 0.48),
            (cx + rect.w * 0.26, top + rect.h * 0.60),
            (cx + rect.w * 0.08, top + rect.h * 0.44),
        ]
        support_arm = [
            (cx - rect.w * 0.12, top + rect.h * 0.32),
            (cx - rect.w * 0.30, top + rect.h * 0.46),
            (cx - rect.w * 0.24, top + rect.h * 0.58),
            (cx - rect.w * 0.08, top + rect.h * 0.44),
        ]
        lower = [
            (cx - rect.w * 0.15, top + rect.h * 0.78),
            (cx - rect.w * 0.08, bottom),
            (cx + rect.w * 0.08, bottom),
            (cx + rect.w * 0.15, top + rect.h * 0.78),
        ]
        weapon_anchor = (cx + rect.w * 0.24, top + rect.h * 0.46)
        symbol_anchor = (cx, top + rect.h * 0.18)
    elif archetype == 'solar_warrior':
        head = pygame.Rect(cx - rect.w // 10, top + rect.h // 14, rect.w // 5, rect.h // 8)
        torso = [
            (cx - rect.w * 0.12, top + rect.h * 0.20),
            (cx + rect.w * 0.12, top + rect.h * 0.20),
            (cx + rect.w * 0.22, top + rect.h * 0.56),
            (cx + rect.w * 0.10, top + rect.h * 0.82),
            (cx - rect.w * 0.10, top + rect.h * 0.82),
            (cx - rect.w * 0.22, top + rect.h * 0.56),
        ]
        cloak = [
            (cx - rect.w * 0.20, top + rect.h * 0.22),
            (cx - rect.w * 0.42, top + rect.h * 0.74),
            (cx, bottom - rect.h * 0.02),
            (cx + rect.w * 0.34, top + rect.h * 0.84),
            (cx + rect.w * 0.24, top + rect.h * 0.24),
        ]
        lead_arm = [
            (cx + rect.w * 0.08, top + rect.h * 0.30),
            (cx + rect.w * 0.30, top + rect.h * 0.44),
            (cx + rect.w * 0.20, top + rect.h * 0.54),
            (cx + rect.w * 0.02, top + rect.h * 0.38),
        ]
        support_arm = [
            (cx - rect.w * 0.08, top + rect.h * 0.32),
            (cx - rect.w * 0.26, top + rect.h * 0.52),
            (cx - rect.w * 0.16, top + rect.h * 0.60),
            (cx - rect.w * 0.02, top + rect.h * 0.40),
        ]
        lower = [
            (cx - rect.w * 0.18, top + rect.h * 0.78),
            (cx - rect.w * 0.02, bottom),
            (cx + rect.w * 0.18, bottom - rect.h * 0.04),
            (cx + rect.w * 0.10, top + rect.h * 0.78),
        ]
        weapon_anchor = (cx + rect.w * 0.18, top + rect.h * 0.42)
        symbol_anchor = (cx, top + rect.h * 0.16)
    elif archetype == 'guide_mage':
        head = pygame.Rect(cx - rect.w // 10, top + rect.h // 12, rect.w // 5, rect.h // 8)
        torso = [
            (cx - rect.w * 0.10, top + rect.h * 0.20),
            (cx + rect.w * 0.10, top + rect.h * 0.20),
            (cx + rect.w * 0.16, top + rect.h * 0.50),
            (cx + rect.w * 0.12, top + rect.h * 0.78),
            (cx - rect.w * 0.12, top + rect.h * 0.78),
            (cx - rect.w * 0.16, top + rect.h * 0.50),
        ]
        cloak = [
            (cx - rect.w * 0.18, top + rect.h * 0.22),
            (cx - rect.w * 0.30, top + rect.h * 0.72),
            (cx - rect.w * 0.18, bottom - rect.h * 0.02),
            (cx + rect.w * 0.18, bottom - rect.h * 0.02),
            (cx + rect.w * 0.30, top + rect.h * 0.72),
            (cx + rect.w * 0.18, top + rect.h * 0.22),
        ]
        lead_arm = [
            (cx + rect.w * 0.08, top + rect.h * 0.30),
            (cx + rect.w * 0.24, top + rect.h * 0.54),
            (cx + rect.w * 0.14, top + rect.h * 0.60),
            (cx + rect.w * 0.00, top + rect.h * 0.38),
        ]
        support_arm = [
            (cx - rect.w * 0.08, top + rect.h * 0.30),
            (cx - rect.w * 0.24, top + rect.h * 0.44),
            (cx - rect.w * 0.16, top + rect.h * 0.54),
            (cx - rect.w * 0.02, top + rect.h * 0.38),
        ]
        lower = [
            (cx - rect.w * 0.12, top + rect.h * 0.78),
            (cx - rect.w * 0.08, bottom),
            (cx + rect.w * 0.08, bottom),
            (cx + rect.w * 0.12, top + rect.h * 0.78),
        ]
        weapon_anchor = (cx + rect.w * 0.20, top + rect.h * 0.48)
        symbol_anchor = (cx, top + rect.h * 0.26)
    else:
        head = pygame.Rect(cx - rect.w // 10, top + rect.h // 10, rect.w // 5, rect.h // 8)
        torso = [
            (cx - rect.w * 0.12, top + rect.h * 0.24),
            (cx + rect.w * 0.12, top + rect.h * 0.24),
            (cx + rect.w * 0.18, top + rect.h * 0.56),
            (cx + rect.w * 0.12, top + rect.h * 0.82),
            (cx - rect.w * 0.12, top + rect.h * 0.82),
            (cx - rect.w * 0.18, top + rect.h * 0.56),
        ]
        cloak = [
            (cx - rect.w * 0.18, top + rect.h * 0.24),
            (cx - rect.w * 0.28, bottom - rect.h * 0.08),
            (cx + rect.w * 0.28, bottom - rect.h * 0.08),
            (cx + rect.w * 0.18, top + rect.h * 0.24),
        ]
        lead_arm = [
            (cx + rect.w * 0.08, top + rect.h * 0.32),
            (cx + rect.w * 0.24, top + rect.h * 0.50),
            (cx + rect.w * 0.14, top + rect.h * 0.58),
            (cx + rect.w * 0.00, top + rect.h * 0.40),
        ]
        support_arm = [
            (cx - rect.w * 0.08, top + rect.h * 0.32),
            (cx - rect.w * 0.24, top + rect.h * 0.50),
            (cx - rect.w * 0.14, top + rect.h * 0.58),
            (cx - rect.w * 0.00, top + rect.h * 0.40),
        ]
        lower = [
            (cx - rect.w * 0.12, top + rect.h * 0.80),
            (cx - rect.w * 0.08, bottom),
            (cx + rect.w * 0.08, bottom),
            (cx + rect.w * 0.12, top + rect.h * 0.80),
        ]
        weapon_anchor = (cx + rect.w * 0.22, top + rect.h * 0.48)
        symbol_anchor = (cx, top + rect.h * 0.18)
    parts = {
        'head': head,
        'torso': torso,
        'cloak': cloak,
        'lead_arm': lead_arm,
        'support_arm': support_arm,
        'lower': lower,
        'weapon_anchor': weapon_anchor,
        'symbol_anchor': symbol_anchor,
        'cx': cx,
        'top': top,
        'bottom': bottom,
    }
    return _shape_adjust(parts, rect, directives)


def _paint_parts(surface: pygame.Surface, parts: dict[str, object], color):
    _poly(surface, color, parts['cloak'])
    _poly(surface, color, parts['support_arm'])
    _poly(surface, color, parts['lead_arm'])
    _poly(surface, color, parts['torso'])
    _poly(surface, color, parts['lower'])
    pygame.draw.ellipse(surface, color, parts['head'])


def generate_humanoid_silhouette(surface: pygame.Surface, rect: pygame.Rect, color):
    parts = _build_humanoid_parts(rect, 'humanoid', _subject_directives({}))
    _paint_parts(surface, parts, color)


def generate_archon_silhouette(surface: pygame.Surface, rect: pygame.Rect, color):
    parts = _build_humanoid_parts(rect, 'archon', _subject_directives({}))
    throne = [
        (rect.x + rect.w * 0.12, rect.y + rect.h * 0.32),
        (rect.x + rect.w * 0.22, rect.y + rect.h * 0.20),
        (rect.x + rect.w * 0.28, rect.y + rect.h * 0.76),
        (rect.x + rect.w * 0.16, rect.bottom - rect.h * 0.04),
        (rect.x + rect.w * 0.84, rect.bottom - rect.h * 0.04),
        (rect.x + rect.w * 0.72, rect.y + rect.h * 0.76),
        (rect.x + rect.w * 0.78, rect.y + rect.h * 0.20),
        (rect.x + rect.w * 0.88, rect.y + rect.h * 0.32),
        (rect.x + rect.w * 0.74, rect.y + rect.h * 0.36),
        (rect.x + rect.w * 0.66, rect.y + rect.h * 0.10),
        (rect.centerx, rect.y + rect.h * 0.04),
        (rect.x + rect.w * 0.34, rect.y + rect.h * 0.10),
        (rect.x + rect.w * 0.26, rect.y + rect.h * 0.36),
    ]
    _poly(surface, color, throne)
    _paint_parts(surface, parts, color)


def generate_solar_warrior_silhouette(surface: pygame.Surface, rect: pygame.Rect, color):
    parts = _build_humanoid_parts(rect, 'solar_warrior', _subject_directives({}))
    _paint_parts(surface, parts, color)
    crest = [
        (parts['cx'], rect.y + rect.h * 0.02),
        (parts['cx'] + rect.w * 0.10, rect.y + rect.h * 0.12),
        (parts['cx'], rect.y + rect.h * 0.10),
        (parts['cx'] - rect.w * 0.10, rect.y + rect.h * 0.12),
    ]
    _poly(surface, color, crest)


def generate_guide_mage_silhouette(surface: pygame.Surface, rect: pygame.Rect, color):
    parts = _build_humanoid_parts(rect, 'guide_mage', _subject_directives({}))
    _paint_parts(surface, parts, color)
    hood = [
        (parts['cx'] - rect.w * 0.16, rect.y + rect.h * 0.18),
        (parts['cx'], rect.y + rect.h * 0.04),
        (parts['cx'] + rect.w * 0.16, rect.y + rect.h * 0.18),
        (parts['cx'] + rect.w * 0.10, rect.y + rect.h * 0.28),
        (parts['cx'] - rect.w * 0.10, rect.y + rect.h * 0.28),
    ]
    _poly(surface, color, hood)


def _draw_archon_character(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    parts = _build_humanoid_parts(rect, 'archon', _subject_directives({}))
    throne_back = pygame.Rect(rect.x + rect.w // 5, rect.y + rect.h // 10, rect.w * 3 // 5, rect.h * 3 // 5)
    pygame.draw.rect(surface, (*accent[:3], 80), throne_back, border_radius=max(8, _scaled(surface, 14)))
    _poly(surface, color, parts['cloak'])
    _poly(surface, accent, parts['torso'])
    inner = pygame.Rect(parts['head'].x + parts['head'].w // 6, parts['head'].y + parts['head'].h // 6, parts['head'].w * 2 // 3, parts['head'].h * 2 // 3)
    pygame.draw.ellipse(surface, color, inner)
    _poly(surface, color, parts['support_arm'])
    _poly(surface, color, parts['lead_arm'])
    _poly(surface, color, parts['lower'])
    pygame.draw.ellipse(surface, accent, parts['head'])
    crown = [
        (parts['cx'] - rect.w * 0.12, rect.y + rect.h * 0.16),
        (parts['cx'] - rect.w * 0.05, rect.y + rect.h * 0.08),
        (parts['cx'], rect.y + rect.h * 0.14),
        (parts['cx'] + rect.w * 0.05, rect.y + rect.h * 0.08),
        (parts['cx'] + rect.w * 0.12, rect.y + rect.h * 0.16),
    ]
    _line(surface, accent, (parts['cx'], rect.y + rect.h * 0.18), (parts['cx'], rect.y + rect.h * 0.78), max(3, _scaled(surface, 6)))
    _poly(surface, accent, crown)
    tablet = pygame.Rect(int(parts['weapon_anchor'][0]), int(rect.y + rect.h * 0.44), rect.w // 5, rect.h // 4)
    if variant == 'arconte_04':
        tablet = pygame.Rect(int(parts['weapon_anchor'][0] - rect.w * 0.02), int(rect.y + rect.h * 0.40), rect.w // 4, rect.h // 4)
    pygame.draw.rect(surface, accent, tablet, border_radius=max(6, _scaled(surface, 10)))
    pygame.draw.rect(surface, color, tablet.inflate(-max(10, tablet.w // 6), -max(10, tablet.h // 6)), border_radius=max(4, _scaled(surface, 6)))
    _draw_symbol_marker(surface, parts['symbol_anchor'], rect, directives, accent)
    _lighting_glaze(surface, rect, directives, accent)
    _draw_aura_marker(surface, rect, directives, accent)


def _draw_solar_warrior_character(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    parts = _build_humanoid_parts(rect, 'solar_warrior', _subject_directives({}))
    _poly(surface, accent, parts['cloak'])
    _poly(surface, color, parts['torso'])
    _poly(surface, color, parts['support_arm'])
    _poly(surface, color, parts['lead_arm'])
    _poly(surface, color, parts['lower'])
    pygame.draw.ellipse(surface, color, parts['head'])
    chest = [
        (parts['cx'] - rect.w * 0.10, rect.y + rect.h * 0.28),
        (parts['cx'], rect.y + rect.h * 0.22),
        (parts['cx'] + rect.w * 0.10, rect.y + rect.h * 0.28),
        (parts['cx'] + rect.w * 0.06, rect.y + rect.h * 0.46),
        (parts['cx'] - rect.w * 0.06, rect.y + rect.h * 0.46),
    ]
    _poly(surface, accent, chest)
    blade_start = (parts['weapon_anchor'][0] - rect.w * 0.06, rect.bottom - rect.h * 0.22)
    blade_end = (parts['weapon_anchor'][0] + rect.w * 0.24, rect.y + rect.h * 0.24)
    if variant == 'guardian_02':
        blade_end = (parts['weapon_anchor'][0] + rect.w * 0.20, rect.y + rect.h * 0.30)
    _line(surface, accent, blade_start, blade_end, max(10, _scaled(surface, 16)))
    blade = [
        (blade_end[0], blade_end[1] - rect.h * 0.04),
        (blade_end[0] + rect.w * 0.08, blade_end[1] + rect.h * 0.03),
        (blade_start[0] + rect.w * 0.12, blade_start[1] - rect.h * 0.04),
        (blade_start[0], blade_start[1] - rect.h * 0.10),
    ]
    _poly(surface, color, blade)
    sun_mark = [
        (parts['cx'] - rect.w * 0.10, rect.y + rect.h * 0.12),
        (parts['cx'], rect.y + rect.h * 0.04),
        (parts['cx'] + rect.w * 0.10, rect.y + rect.h * 0.12),
        (parts['cx'], rect.y + rect.h * 0.16),
    ]
    _poly(surface, accent, sun_mark)
    _draw_symbol_marker(surface, parts['symbol_anchor'], rect, directives, accent)
    _lighting_glaze(surface, rect, directives, accent)
    _draw_aura_marker(surface, rect, directives, accent)


def _draw_guide_mage_character(surface: pygame.Surface, rect: pygame.Rect, color, accent, variant: str = ''):
    parts = _build_humanoid_parts(rect, 'guide_mage', _subject_directives({}))
    _poly(surface, accent, parts['cloak'])
    _poly(surface, color, parts['torso'])
    _poly(surface, color, parts['support_arm'])
    _poly(surface, color, parts['lead_arm'])
    _poly(surface, color, parts['lower'])
    hood = [
        (parts['cx'] - rect.w * 0.16, rect.y + rect.h * 0.18),
        (parts['cx'], rect.y + rect.h * 0.06),
        (parts['cx'] + rect.w * 0.16, rect.y + rect.h * 0.18),
        (parts['cx'] + rect.w * 0.10, rect.y + rect.h * 0.28),
        (parts['cx'] - rect.w * 0.10, rect.y + rect.h * 0.28),
    ]
    _poly(surface, color, hood)
    face = pygame.Rect(parts['head'].x + parts['head'].w // 5, parts['head'].y + parts['head'].h // 4, parts['head'].w * 3 // 5, parts['head'].h * 2 // 3)
    pygame.draw.ellipse(surface, accent, face)
    staff_a = (parts['weapon_anchor'][0] - rect.w * 0.02, rect.bottom - rect.h * 0.12)
    staff_b = (parts['weapon_anchor'][0] + rect.w * 0.10, rect.y + rect.h * 0.22)
    _line(surface, accent, staff_a, staff_b, max(8, _scaled(surface, 12)))
    orb_center = (int(staff_b[0]), int(staff_b[1] - rect.h * 0.04))
    pygame.draw.circle(surface, accent, orb_center, max(10, rect.w // 12), max(2, _scaled(surface, 4)))
    rune = pygame.Rect(int(parts['symbol_anchor'][0] - rect.w * 0.08), int(parts['symbol_anchor'][1]), rect.w // 6, rect.h // 10)
    pygame.draw.rect(surface, accent, rune, max(2, _scaled(surface, 4)), border_radius=max(4, _scaled(surface, 6)))
    _line(surface, accent, (rune.centerx, rune.top), (rune.centerx, rune.bottom), max(2, _scaled(surface, 4)))
    _draw_symbol_marker(surface, parts['symbol_anchor'], rect, directives, accent)
    _lighting_glaze(surface, rect, directives, accent)
    _draw_aura_marker(surface, rect, directives, accent)


def _subject_rect(surface: pygame.Surface, semantic: dict, template_family: str, subject: str) -> pygame.Rect:
    camera = str(semantic.get('camera', '') or '').lower()
    scene_type = str(semantic.get('scene_type', '') or '').lower()
    kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    width_ratio = 0.46 if 'close' in camera else 0.50
    height_ratio = 0.76 if 'duel' in scene_type or 'ritual' in scene_type else 0.72
    top_ratio = 0.06
    if kind in {'archon_foreground', 'archon_throne', 'archon_beast'} or template_family == 'archon':
        width_ratio = 0.50
        height_ratio = 0.76
        top_ratio = 0.05
    elif kind in {'warrior_foreground', 'hyperborean_champion', 'hyperborean_foreground', 'guardian_bearer', 'weapon_bearer'} or template_family in {'guardian', 'warrior'}:
        width_ratio = 0.50
        height_ratio = 0.78
        top_ratio = 0.04
    elif kind in {'oracle_totem'} or template_family == 'mage':
        width_ratio = 0.46
        height_ratio = 0.76
        top_ratio = 0.05
    if template_family == 'animal' or any(k in subject for k in ('condor', 'bird', 'ave', 'beast', 'puma', 'wolf')):
        width_ratio = 0.52
        height_ratio = 0.56
        top_ratio = 0.16
    width = int(surface.get_width() * width_ratio)
    height = int(surface.get_height() * height_ratio)
    cx = surface.get_width() // 2
    left = max(0, min(surface.get_width() - width, cx - width // 2))
    top = int(surface.get_height() * top_ratio)
    return pygame.Rect(left, top, width, height)


def draw_subject_silhouette(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random) -> pygame.Rect:
    kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    subject = ' '.join([
        str(semantic.get('subject', '') or ''),
        str(semantic.get('environment', '') or ''),
        ' '.join(getattr(r, 'cue', '') for r in refs[:3]),
    ]).lower()
    template_family = SUBJECT_KIND_TO_TEMPLATE.get(kind, '')
    rect = _subject_rect(surface, semantic, template_family, subject)
    silhouette_color = (28, 24, 34, 255)
    if kind in {'archon_foreground', 'archon_throne', 'archon_beast'} or template_family == 'archon':
        generate_archon_silhouette(surface, rect, silhouette_color)
    elif kind in {'warrior_foreground', 'hyperborean_champion', 'hyperborean_foreground', 'guardian_bearer', 'weapon_bearer'} or template_family in {'guardian', 'warrior'}:
        generate_solar_warrior_silhouette(surface, rect, silhouette_color)
    elif kind in {'oracle_totem'} or template_family == 'mage':
        generate_guide_mage_silhouette(surface, rect, silhouette_color)
    else:
        generate_humanoid_silhouette(surface, rect, silhouette_color)
    _outline_mask(surface, (10, 8, 16, 255), max(2, _scaled(surface, 4)))
    return rect



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
    parts = {
        'subject_categories': SUBJECT_SILHOUETTE_LIBRARY,
        'object_categories': OBJECT_SILHOUETTE_LIBRARY,
    }

def _subject_variant(semantic: dict) -> str:
    return _ref_stem(semantic.get('subject_ref', ''))


def _object_variant(semantic: dict) -> str:
    return _ref_stem(semantic.get('object_ref', ''))



def draw_subject(surface: pygame.Surface, semantic: dict, refs: list, palette, rng: random.Random, silhouette_rect: pygame.Rect | None = None):
    kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    variant = _subject_variant(semantic)
    subject = ' '.join([
        str(semantic.get('subject', '') or ''),
        str(semantic.get('environment', '') or ''),
        ' '.join(getattr(r, 'cue', '') for r in refs[:3]),
    ]).lower()
    template_family = SUBJECT_KIND_TO_TEMPLATE.get(kind, '')
    main = (max(18, int(palette[0][0] * 1.18)), max(18, int(palette[0][1] * 1.18)), max(18, int(palette[0][2] * 1.18)))
    accent = tuple(max(32, min(255, int(c * 0.88))) for c in palette[3])
    rect = silhouette_rect or _subject_rect(surface, semantic, template_family, subject)
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    _draw_stage_shadow(layer, rect, alpha=124)
    _draw_subject_staging(layer, rect, accent, semantic)
    ref_path = _pick_subject_reference(refs, semantic)
    directives = _subject_directives(semantic)
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
        _draw_archon_character(layer, rect, main, accent, directives, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'guardian_bearer':
        _draw_guardian_bearer(layer, rect, main, accent)
        _draw_humanoid_details(layer, rect, main, accent)
    elif kind == 'warrior_foreground':
        _draw_solar_warrior_character(layer, rect, main, accent, directives, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif any(k in subject for k in ('tree', 'gaia', 'arbol')):
        _draw_tree(layer, rect, main, accent)
    elif template_family == 'animal' or any(k in subject for k in ('condor', 'bird', 'ave')):
        _draw_condor(layer, rect, main, accent)
    elif template_family == 'temple' or any(k in subject for k in ('castle', 'temple', 'sanctuary', 'ruins', 'throne', 'city')):
        _draw_castle(layer, rect, main, accent)
    elif template_family == 'archon' or any(k in subject for k in ('archon', 'arconte', 'throne-realm')):
        _draw_archon_character(layer, rect, main, accent, directives, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif template_family == 'mage' or any(k in subject for k in ('oracle', 'visionary', 'seer')):
        _draw_guide_mage_character(layer, rect, main, accent, directives, variant=variant)
        _draw_humanoid_details(layer, rect, main, accent)
    elif template_family in {'guardian', 'warrior'} or any(k in subject for k in ('guardian', 'warrior', 'champion')):
        _draw_solar_warrior_character(layer, rect, main, accent, directives, variant=variant)
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
    ratio = max(0.28, min(0.42, float(preset.frame_ratio) * 1.22))
    rect_w = int(surface.get_width() * max(0.18, ratio * 1.04))
    rect_h = int(surface.get_height() * max(0.28, ratio * 1.12))
    if template_family == 'weapon' or kind in {'greatsword', 'solar_axe'} or any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        rect_w = int(rect_w * 1.42)
        rect_h = int(rect_h * 1.24)
    rect = pygame.Rect(
        int(surface.get_width() * 0.59 - rect_w * 0.5),
        int(surface.get_height() * 0.54 - rect_h * 0.42),
        rect_w,
        rect_h,
    )
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    _draw_object_staging(layer, rect, glow, semantic)
    ref_path = _pick_object_reference(semantic, refs)
    if template_family == 'weapon' or kind in {'greatsword', 'solar_axe'} or any(k in obj for k in ('sword', 'blade', 'axe', 'spear', 'weapon')):
        shaft_a = (rect.left + rect.w // 5, rect.bottom - rect.h // 9)
        shaft_b = (rect.right - rect.w // 4, rect.top + rect.h // 8)
        _blocky_line(layer, _rgba(glow, 86), shaft_a, shaft_b, max(22, _scaled(surface, 34)))
        _blocky_line(layer, color, shaft_a, shaft_b, max(14, _scaled(surface, 22)))
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
