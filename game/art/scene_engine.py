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
        'subject': _extract_field(p, 'subject ', ('object', 'environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'object': _extract_field(p, 'object ', ('environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'environment': _extract_field(p, 'environment ', ('effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'effects': _extract_field(p, 'effects ', ('energy pattern', 'lore tokens')),
        'effects_desc': _extract_field(p, 'effect signature ', ('effects', 'energy pattern', 'lore tokens')),
        'energy': _extract_field(p, 'energy pattern ', ('lore tokens',)),
        'rarity': _extract_field(p, 'rarity ', ('sacred geometry', 'motif', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
    }


def _palette_from_refs(choices):
    if not choices:
        return ((26, 20, 36), (72, 64, 92), (132, 124, 156), (222, 190, 118))
    cols = [c.avg_color for c in choices]
    r = sum(c[0] for c in cols) // len(cols)
    g = sum(c[1] for c in cols) // len(cols)
    b = sum(c[2] for c in cols) // len(cols)
    top = (max(8, r // 4), max(8, g // 4), max(8, b // 4))
    mid = (max(16, (r + 40) // 2), max(16, (g + 40) // 2), max(16, (b + 40) // 2))
    low = (min(255, r), min(255, g), min(255, b))
    accent = (min(255, r + 60), min(255, g + 40), min(255, b + 20))
    return (top, mid, low, accent)


def _categories_for_prompt(prompt: str) -> list[str]:
    low = str(prompt or '').lower()
    if 'hiperboria' in low or 'hiperborea' in low or 'hip_' in low:
        return ['fantasy_landscapes', 'ancient_architecture', 'characters_subjects', 'weapons_relics']
    if 'archon' in low or 'arconte' in low or 'void' in low or 'arc_' in low:
        return ['biblical_archetypes', 'characters_subjects', 'weapons_relics', 'ancient_architecture']
    return ['andean_mythology', 'fantasy_landscapes', 'characters_subjects', 'weapons_relics', 'chakana_symbols']


def _keywords_from_semantic(semantic: dict) -> list[str]:
    out = []
    for key in ('subject', 'object', 'environment', 'motif', 'symbol', 'effects'):
        val = str(semantic.get(key, '') or '').replace(',', ' ')
        out.extend(val.split())
    return [w for w in out if len(w) > 2][:16]


def _draw_background(surface: pygame.Surface, semantic: dict, palette, rng: random.Random):
    w, h = surface.get_size()
    top, mid, low, acc = palette
    env = str(semantic.get('environment', '') or '').lower()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.6:
            q = t / 0.6
            col = (int(top[0] * (1 - q) + mid[0] * q), int(top[1] * (1 - q) + mid[1] * q), int(top[2] * (1 - q) + mid[2] * q))
        else:
            q = (t - 0.6) / 0.4
            col = (int(mid[0] * (1 - q) + low[0] * q), int(mid[1] * (1 - q) + low[1] * q), int(mid[2] * (1 - q) + low[2] * q))
        pygame.draw.line(surface, col, (0, y), (w, y))
    horizon = int(h * 0.66)
    pygame.draw.rect(surface, (low[0] // 2, low[1] // 2, low[2] // 2), (0, horizon, w, h - horizon))
    if any(k in env for k in ('sea', 'mar', 'ocean', 'helado')):
        for y in range(horizon, h, 6):
            pygame.draw.line(surface, (*acc, 100), (0, y), (w, y), 2)
    elif any(k in env for k in ('jungle', 'forest', 'selva')):
        for _ in range(10):
            x = rng.randint(0, w - 1)
            th = rng.randint(h // 6, h // 3)
            pygame.draw.rect(surface, (top[0], top[1], top[2]), (x, horizon - th, 6, th))
            pygame.draw.circle(surface, (mid[0], mid[1], mid[2]), (x + 3, horizon - th), rng.randint(10, 18))
    else:
        points = []
        x = 0
        while x < w:
            points.append((x, horizon - rng.randint(20, 70)))
            x += rng.randint(30, 60)
        points += [(w, horizon), (w, h), (0, h)]
        pygame.draw.polygon(surface, (mid[0], mid[1], mid[2]), points)


def generate_scene_art(card_id: str, prompt: str, seed: int, out_path: Path) -> dict:
    rng = random.Random(seed)
    semantic = semantic_from_prompt(prompt)
    sampler = ReferenceSampler()
    refs = sampler.pick(_categories_for_prompt(prompt), _keywords_from_semantic(semantic), seed)
    palette = _palette_from_refs(refs)
    work = pygame.Surface((512, 512), pygame.SRCALPHA, 32)
    _draw_background(work, semantic, palette, rng)
    draw_subject(work, semantic, refs, palette, rng)
    draw_focus_object(work, semantic, palette, rng)
    draw_fx(work, semantic, palette, rng)
    low = pygame.transform.smoothscale(work, (160, 160))
    final = pygame.transform.scale(low, (320, 220)).convert_alpha()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(final, str(out_path))
    return {
        'card_id': card_id,
        'path': str(out_path),
        'generator_used': 'scene_engine_v1',
        'references_used': [r.path.name for r in refs[:4]],
        'palette_seeded': [r.avg_color for r in refs[:3]],
        'semantic_subject': str(semantic.get('subject', '') or ''),
        'semantic_object': str(semantic.get('object', '') or ''),
        'semantic_environment': str(semantic.get('environment', '') or ''),
    }
