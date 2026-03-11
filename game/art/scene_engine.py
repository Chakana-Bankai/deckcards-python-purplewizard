from __future__ import annotations

from pathlib import Path
import random

import pygame

from game.art.fx_layer import draw_fx
from game.art.reference_sampler import ReferenceSampler
from game.art.silhouette_builder import draw_focus_object, draw_subject


def _extract_field(prompt: str, key: str, stop_tokens: tuple[str, ...]) -> str:
    src = str(prompt or '')
    i = src.lower().find(key)
    if i < 0:
        return ''
    start = i + len(key)
    tail = src[start:]
    end = len(tail)
    for st in stop_tokens:
        j = tail.lower().find(st)
        if j >= 0:
            end = min(end, j)
    return tail[:end].strip(' ,:;.')


def semantic_from_prompt(prompt: str) -> dict:
    p = str(prompt or '')
    return {
        'palette': _extract_field(p, 'palette ', ('lighting', 'sacred geometry', 'motif', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern')),
        'motif': _extract_field(p, 'motif ', ('(', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'symbol': _extract_field(p, 'sacred geometry ', ('motif', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern')),
        'subject': _extract_field(p, 'subject ', ('object', 'environment', 'subject kind', 'object kind', 'environment kind', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'object': _extract_field(p, 'object ', ('environment', 'subject kind', 'object kind', 'environment kind', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'environment': _extract_field(p, 'environment ', ('subject kind', 'object kind', 'environment kind', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'subject_kind': _extract_field(p, 'subject kind ', ('object kind', 'environment kind', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'object_kind': _extract_field(p, 'object kind ', ('environment kind', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'environment_kind': _extract_field(p, 'environment kind ', ('effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'effects': _extract_field(p, 'effects ', ('energy pattern', 'lore tokens')),
        'effects_desc': _extract_field(p, 'effect signature ', ('effects', 'energy pattern', 'lore tokens')),
        'energy': _extract_field(p, 'energy pattern ', ('lore tokens',)),
        'rarity': _extract_field(p, 'rarity ', ('sacred geometry', 'motif', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
    }


def _palette_from_refs(choices):
    if not choices:
        return ((20, 16, 28), (72, 68, 96), (148, 138, 166), (232, 204, 132))
    cols = [c.avg_color for c in choices]
    r = sum(c[0] for c in cols) // len(cols)
    g = sum(c[1] for c in cols) // len(cols)
    b = sum(c[2] for c in cols) // len(cols)
    top = (max(8, r // 5), max(8, g // 5), max(8, b // 5))
    mid = (max(18, int(r * 0.55)), max(18, int(g * 0.55)), max(18, int(b * 0.55)))
    low = (min(255, int(r * 0.92)), min(255, int(g * 0.92)), min(255, int(b * 0.92)))
    accent = (min(255, r + 70), min(255, g + 50), min(255, b + 26))
    return (top, mid, low, accent)


def _categories_for_prompt(prompt: str) -> list[str]:
    low = str(prompt or '').lower()
    if 'hiperboria' in low or 'hiperborea' in low or 'hip_' in low:
        return ['characters_subjects', 'weapons_relics', 'fantasy_landscapes', 'ancient_architecture']
    if 'archon' in low or 'arconte' in low or 'void' in low or 'arc_' in low:
        return ['characters_subjects', 'weapons_relics', 'biblical_archetypes', 'ancient_architecture']
    return ['characters_subjects', 'weapons_relics', 'andean_mythology', 'fantasy_landscapes', 'chakana_symbols']


def _keywords_from_semantic(semantic: dict) -> list[str]:
    out = []
    for key in ('subject', 'object', 'environment', 'motif', 'symbol', 'effects'):
        val = str(semantic.get(key, '') or '').replace(',', ' ')
        out.extend(val.split())
    subject_kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    object_kind = str(semantic.get('object_kind', '') or '').lower().replace(' ', '_')
    environment_kind = str(semantic.get('environment_kind', '') or '').lower().replace(' ', '_')

    subject_aliases = {
        'weapon_bearer': ['guardian_01', 'mago_01'],
        'guardian_bearer': ['guardian_01'],
        'oracle_totem': ['mago_01'],
        'hyperborean_champion': ['guardian_01', 'mago_01'],
        'archon_throne': ['arconte_01', 'heraldos_01'],
        'archon_beast': ['arconte_01', 'puma_01'],
    }
    object_aliases = {
        'weapon': ['espada_01'],
        'codex': ['codice_01'],
        'altar': ['altar_01'],
        'seal': ['sellos_01'],
        'crown': ['coronas_01'],
        'shield': ['sellos_01'],
    }
    environment_aliases = {
        'citadel': ['templos_escalonados_01', 'puentes_antiguos_01'],
        'throne_realm': ['heraldos_01', 'presencia_sagrada_u_opresiva_01', 'puentes_antiguos_01'],
        'gaia_sanctuary': ['condor_01', 'puma_01', 'textiles_andinos_01'],
        'sanctuary': ['chakana_limpia_01', 'cruces_escalonadas_01'],
    }

    out.extend(subject_aliases.get(subject_kind, []))
    out.extend(object_aliases.get(object_kind, []))
    out.extend(environment_aliases.get(environment_kind, []))
    return [w for w in out if len(w) > 2][:16]


def _draw_background(surface: pygame.Surface, semantic: dict, palette, rng: random.Random):
    w, h = surface.get_size()
    top, mid, low, acc = palette
    env = str(semantic.get('environment', '') or '').lower()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.58:
            q = t / 0.58
            col = (int(top[0] * (1 - q) + mid[0] * q), int(top[1] * (1 - q) + mid[1] * q), int(top[2] * (1 - q) + mid[2] * q))
        else:
            q = (t - 0.58) / 0.42
            col = (int(mid[0] * (1 - q) + low[0] * q), int(mid[1] * (1 - q) + low[1] * q), int(mid[2] * (1 - q) + low[2] * q))
        pygame.draw.line(surface, col, (0, y), (w, y))
    horizon = int(h * 0.66)
    ground = (max(8, low[0] // 2), max(8, low[1] // 2), max(8, low[2] // 2))
    pygame.draw.rect(surface, ground, (0, horizon, w, h - horizon))
    mist = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(4):
        mw = rng.randint(w // 4, w // 2)
        mh = rng.randint(h // 10, h // 6)
        mx = rng.randint(-40, w - mw + 40)
        my = rng.randint(horizon - h // 8, horizon + h // 10)
        pygame.draw.ellipse(mist, (255, 255, 255, 18), (mx, my, mw, mh))
    surface.blit(mist, (0, 0))
    if any(k in env for k in ('sea', 'mar', 'ocean', 'helado')):
        for y in range(horizon, h, 8):
            pygame.draw.line(surface, (*acc, 120), (0, y), (w, y), 2)
    elif any(k in env for k in ('jungle', 'forest', 'selva')):
        for _ in range(7):
            x = rng.randint(0, w - 1)
            th = rng.randint(h // 5, h // 3)
            pygame.draw.rect(surface, (top[0], top[1], top[2]), (x, horizon - th, 8, th))
            pygame.draw.circle(surface, (mid[0], mid[1], mid[2]), (x + 4, horizon - th), rng.randint(16, 28))
    elif any(k in env for k in ('temple', 'sanctuary', 'ruins', 'city', 'architecture', 'throne', 'citadel', 'observatory')):
        far = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(5):
            bw = rng.randint(w // 10, w // 6)
            bh = rng.randint(h // 7, h // 4)
            bx = rng.randint(0, max(0, w - bw - 1))
            by = horizon - bh - rng.randint(0, 22)
            pygame.draw.rect(far, (mid[0], mid[1], mid[2], 180), (bx, by, bw, bh), border_radius=3)
            pygame.draw.rect(far, (acc[0], acc[1], acc[2], 190), (bx + bw // 4, by - 10, bw // 2, 10), border_radius=2)
        surface.blit(far, (0, 0))
        mid_layer = pygame.Surface((w, h), pygame.SRCALPHA)
        keep = pygame.Rect(int(w * 0.22), int(h * 0.14), int(w * 0.56), int(h * 0.62))
        for _ in range(4):
            bw = rng.randint(w // 8, w // 5)
            bh = rng.randint(h // 6, h // 3)
            bx = rng.randint(0, max(0, w - bw - 1))
            by = horizon - bh - rng.randint(0, 10)
            rect = pygame.Rect(bx, by, bw, bh)
            if rect.colliderect(keep):
                continue
            pygame.draw.rect(mid_layer, (low[0], low[1], low[2], 230), rect, border_radius=4)
            pygame.draw.rect(mid_layer, (acc[0], acc[1], acc[2], 220), (bx + bw // 4, by - 14, bw // 2, 14), border_radius=2)
        surface.blit(mid_layer, (0, 0))
    else:
        points = []
        x = 0
        while x < w:
            points.append((x, horizon - rng.randint(28, 86)))
            x += rng.randint(40, 74)
        points += [(w, horizon), (w, h), (0, h)]
        pygame.draw.polygon(surface, (mid[0], mid[1], mid[2]), points)


def _apply_contrast(surface: pygame.Surface):
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(shade, (0, 0, 0, 24), shade.get_rect(), 0, border_radius=0)
    surface.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    light = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(light, (255, 244, 224, 16), [(0, 0), (int(surface.get_width() * 0.32), 0), (int(surface.get_width() * 0.18), int(surface.get_height() * 0.22)), (0, int(surface.get_height() * 0.28))])
    surface.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def _prioritize_refs(refs, semantic: dict):
    subject_kind = str(semantic.get('subject_kind', '') or '').lower().replace(' ', '_')
    object_kind = str(semantic.get('object_kind', '') or '').lower().replace(' ', '_')
    environment_kind = str(semantic.get('environment_kind', '') or '').lower().replace(' ', '_')
    preferred = {
        'weapon_bearer': ['guardian_01.png', 'mago_01.png'],
        'guardian_bearer': ['guardian_01.png'],
        'oracle_totem': ['mago_01.png'],
        'hyperborean_champion': ['guardian_01.png', 'mago_01.png'],
        'archon_throne': ['arconte_01.png', 'heraldos_01.jpg', 'heraldos_01.png'],
        'archon_beast': ['arconte_01.png', 'puma_01.png'],
        'weapon': ['espada_01.png'],
        'codex': ['codice_01.png'],
        'altar': ['altar_01.png'],
        'seal': ['sellos_01.png'],
        'crown': ['coronas_01.png'],
        'citadel': ['templos_escalonados_01.jpg', 'templos_escalonados_01.png', 'puentes_antiguos_01.jpg', 'puentes_antiguos_01.png'],
        'throne_realm': ['arconte_01.png', 'heraldos_01.jpg', 'heraldos_01.png'],
        'gaia_sanctuary': ['condor_01.png', 'puma_01.png', 'textiles_andinos_01.jpg', 'textiles_andinos_01.png'],
        'sanctuary': ['guardian_01.png', 'mago_01.png'],
    }
    wanted = preferred.get(subject_kind, []) + preferred.get(object_kind, []) + preferred.get(environment_kind, [])
    wanted_set = {w.lower() for w in wanted}
    if not wanted_set:
        return refs
    return sorted(refs, key=lambda r: (0 if r.path.name.lower() in wanted_set else 1, r.path.name.lower()))


def generate_scene_art(card_id: str, prompt: str, seed: int, out_path: Path) -> dict:
    rng = random.Random(seed)
    semantic = semantic_from_prompt(prompt)
    sampler = ReferenceSampler()
    refs = _prioritize_refs(sampler.pick(_categories_for_prompt(prompt), _keywords_from_semantic(semantic), seed), semantic)
    palette = _palette_from_refs(refs)
    work = pygame.Surface((768, 768), pygame.SRCALPHA, 32)
    _draw_background(work, semantic, palette, rng)
    shadow = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 54), (int(work.get_width() * 0.18), int(work.get_height() * 0.58), int(work.get_width() * 0.64), int(work.get_height() * 0.2)))
    work.blit(shadow, (0, 0))
    draw_subject(work, semantic, refs, palette, rng)
    draw_focus_object(work, semantic, palette, rng)
    draw_fx(work, semantic, palette, rng)
    _apply_contrast(work)
    final = pygame.transform.smoothscale(work, (320, 220)).convert_alpha()
    sharpen = pygame.Surface((320, 220), pygame.SRCALPHA)
    for _ in range(18):
        x = rng.randint(0, 319)
        y = rng.randint(0, 219)
        pygame.draw.circle(sharpen, (255, 255, 255, 4), (x, y), 1)
    final.blit(sharpen, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(final, str(out_path))
    return {
        'card_id': card_id,
        'path': str(out_path),
        'generator_used': 'scene_engine_v2',
        'references_used': [r.path.name for r in refs[:4]],
        'palette_seeded': [r.avg_color for r in refs[:3]],
        'semantic_subject': str(semantic.get('subject', '') or ''),
        'semantic_object': str(semantic.get('object', '') or ''),
        'semantic_environment': str(semantic.get('environment', '') or ''),
    }
