from __future__ import annotations

from pathlib import Path
import random

import pygame

from game.art.environment_library import resolve_environment_preset
from game.art.fx_layer import draw_fx
from game.art.palette_system import resolve_civilization_palette
from game.art.reference_sampler import ReferenceSampler, ReferenceChoice
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
        'subject': _extract_field(p, 'subject ', ('object', 'environment', 'scene type', 'subject pose', 'secondary object', 'camera', 'mood', 'subject kind', 'object kind', 'environment kind', 'subject ref', 'object ref', 'environment ref', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'object': _extract_field(p, 'object ', ('environment', 'scene type', 'subject pose', 'secondary object', 'camera', 'mood', 'subject kind', 'object kind', 'environment kind', 'subject ref', 'object ref', 'environment ref', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'environment': _extract_field(p, 'environment ', ('scene type', 'subject pose', 'secondary object', 'camera', 'mood', 'subject kind', 'object kind', 'environment kind', 'subject ref', 'object ref', 'environment ref', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
        'subject_kind': _extract_field(p, 'subject kind ', ('object kind', 'environment kind', 'subject ref', 'object ref', 'environment ref', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'object_kind': _extract_field(p, 'object kind ', ('environment kind', 'subject ref', 'object ref', 'environment ref', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'environment_kind': _extract_field(p, 'environment kind ', ('subject ref', 'object ref', 'environment ref', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'subject_ref': _extract_field(p, 'subject ref ', ('object ref', 'environment ref', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'object_ref': _extract_field(p, 'object ref ', ('environment ref', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'environment_ref': _extract_field(p, 'environment ref ', ('effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'scene_type': _extract_field(p, 'scene type ', ('subject pose', 'secondary object', 'camera', 'mood', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'subject_pose': _extract_field(p, 'subject pose ', ('secondary object', 'camera', 'mood', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'secondary_object': _extract_field(p, 'secondary object ', ('camera', 'mood', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'camera': _extract_field(p, 'camera ', ('mood', 'effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'mood': _extract_field(p, 'mood ', ('effect signature', 'effects', 'energy pattern', 'lore tokens')),
        'effects': _extract_field(p, 'effects ', ('energy pattern', 'lore tokens')),
        'effects_desc': _extract_field(p, 'effect signature ', ('effects', 'energy pattern', 'lore tokens')),
        'energy': _extract_field(p, 'energy pattern ', ('lore tokens',)),
        'rarity': _extract_field(p, 'rarity ', ('sacred geometry', 'motif', 'subject', 'object', 'environment', 'effects', 'effect signature', 'energy pattern', 'lore tokens')),
    }



def _resolve_explicit_refs(sampler: ReferenceSampler, semantic: dict) -> list[ReferenceChoice]:
    wanted: list[ReferenceChoice] = []
    names = [
        str(semantic.get('subject_ref', '') or '').strip(),
        str(semantic.get('object_ref', '') or '').strip(),
        str(semantic.get('environment_ref', '') or '').strip(),
    ]
    seen = set()
    for category in (
        'characters_subjects',
        'weapons_relics',
        'ancient_architecture',
        'fantasy_landscapes',
        'andean_mythology',
        'biblical_archetypes',
        'chakana_symbols',
        'sacred_geometry',
    ):
        for p in sampler._files_for(category):
            low = p.name.lower()
            if low in seen:
                continue
            for target in names:
                if target and low == target.lower():
                    seen.add(low)
                    wanted.append(ReferenceChoice(path=p, category=category, cue=p.stem.replace('_', ' '), avg_color=sampler._avg_color(p)))
                    break
    return wanted

def _blend_color(a, b, weight: float):
    return (
        int(a[0] * (1.0 - weight) + b[0] * weight),
        int(a[1] * (1.0 - weight) + b[1] * weight),
        int(a[2] * (1.0 - weight) + b[2] * weight),
    )


def _palette_from_refs(choices, semantic):
    civ = resolve_civilization_palette(semantic)
    top = civ.shadow
    mid = civ.primary
    low = civ.secondary
    accent = civ.glow
    if choices:
        cols = [c.avg_color for c in choices]
        r = sum(c[0] for c in cols) // len(cols)
        g = sum(c[1] for c in cols) // len(cols)
        b = sum(c[2] for c in cols) // len(cols)
        ref_mid = (max(18, int(r * 0.55)), max(18, int(g * 0.55)), max(18, int(b * 0.55)))
        ref_low = (min(255, int(r * 0.92)), min(255, int(g * 0.92)), min(255, int(b * 0.92)))
        ref_acc = (min(255, r + 60), min(255, g + 60), min(255, b + 50))
        mid = _blend_color(mid, ref_mid, 0.28)
        low = _blend_color(low, ref_low, 0.22)
        accent = _blend_color(accent, ref_acc, 0.18)
    return (top, mid, low, accent)


def _strong_foreground_palette(palette, subject_kind: str, object_kind: str):
    top, mid, low, acc = palette
    subject_kind = str(subject_kind or '').lower()
    object_kind = str(object_kind or '').lower()
    fg_main = (
        max(18, int(top[0] * 1.35)),
        max(18, int(top[1] * 1.35)),
        max(18, int(top[2] * 1.35)),
    )
    fg_fill = (
        max(32, int(mid[0] * 0.62)),
        max(32, int(mid[1] * 0.62)),
        max(32, int(mid[2] * 0.62)),
    )
    fg_accent = (
        min(255, max(acc[0], low[0] + 60)),
        min(255, max(acc[1], low[1] + 60)),
        min(255, max(acc[2], low[2] + 50)),
    )
    if subject_kind in {'archon_foreground', 'archon_throne', 'archon_beast'}:
        fg_fill = (34, 20, 34)
        fg_accent = (238, 110, 158)
    elif subject_kind in {'hyperborean_foreground', 'hyperborean_champion'}:
        fg_fill = (62, 62, 92)
        fg_accent = (240, 232, 162)
    elif subject_kind in {'warrior_foreground', 'weapon_bearer'}:
        fg_fill = (54, 48, 62)
        fg_accent = (246, 222, 138)
    if object_kind in {'greatsword', 'solar_axe', 'seal_tablet'}:
        fg_accent = (
            min(255, fg_accent[0] + 12),
            min(255, fg_accent[1] + 12),
            min(255, fg_accent[2] + 12),
        )
    return (fg_main, fg_fill, low, fg_accent)


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
        'warrior_foreground': ['guardian_01', 'espada_01'],
        'guardian_bearer': ['guardian_01'],
        'oracle_totem': ['mago_01'],
        'hyperborean_champion': ['guardian_01', 'mago_01'],
        'hyperborean_foreground': ['guardian_01', 'espada_01', 'templos_escalonados_01'],
        'archon_throne': ['arconte_01', 'heraldos_01'],
        'archon_foreground': ['arconte_01', 'heraldos_01', 'sellos_01'],
        'archon_beast': ['arconte_01', 'puma_01'],
    }
    object_aliases = {
        'weapon': ['espada_01'],
        'greatsword': ['espada_01'],
        'solar_axe': ['espada_01'],
        'codex': ['codice_01'],
        'altar': ['altar_01'],
        'seal': ['sellos_01'],
        'seal_tablet': ['sellos_01', 'altar_01'],
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
    env_ref = str(semantic.get('environment_ref', '') or '').lower()
    preset = resolve_environment_preset(semantic.get('scene_type', ''), semantic.get('environment_kind', ''), env)
    for y in range(h):
        t = y / max(1, h - 1)
        split = max(0.45, min(0.72, float(preset.horizon_ratio) - 0.08))
        if t < split:
            q = t / max(0.001, split)
            col = (int(top[0] * (1 - q) + mid[0] * q), int(top[1] * (1 - q) + mid[1] * q), int(top[2] * (1 - q) + mid[2] * q))
        else:
            q = (t - split) / max(0.001, 1.0 - split)
            col = (int(mid[0] * (1 - q) + low[0] * q), int(mid[1] * (1 - q) + low[1] * q), int(mid[2] * (1 - q) + low[2] * q))
        pygame.draw.line(surface, col, (0, y), (w, y))
    horizon = int(h * preset.horizon_ratio)
    ground = (max(8, low[0] // 2), max(8, low[1] // 2), max(8, low[2] // 2))
    pygame.draw.rect(surface, ground, (0, horizon, w, h - horizon))
    mist = pygame.Surface((w, h), pygame.SRCALPHA)
    mist_alpha = 24 if preset.atmospheric_color in {'silver_haze', 'sacred_haze'} else 18
    for _ in range(2):
        mw = rng.randint(w // 4, w // 2)
        mh = rng.randint(h // 10, h // 6)
        mx = rng.randint(-40, w - mw + 40)
        my = rng.randint(horizon - h // 8, horizon + h // 10)
        pygame.draw.ellipse(mist, (255, 255, 255, mist_alpha), (mx, my, mw, mh))
    surface.blit(mist, (0, 0))

    preset_id = preset.preset_id
    if preset.ground_treatment in {'plateau_lines', 'altar_platform', 'frozen_temple_steps'} or any(k in env for k in ('sea', 'mar', 'ocean', 'helado')):
        step = 8 if preset.ground_treatment != 'altar_platform' else 10
        for y in range(horizon, h, step):
            pygame.draw.line(surface, (*acc, 120), (0, y), (w, y), 2)
    elif preset_id == 'sacred_forest' or any(k in env for k in ('jungle', 'forest', 'selva')):
        for _ in range(7):
            x = rng.randint(0, w - 1)
            th = rng.randint(h // 5, h // 3)
            pygame.draw.rect(surface, (top[0], top[1], top[2]), (x, horizon - th, 8, th))
            pygame.draw.circle(surface, (mid[0], mid[1], mid[2]), (x + 4, horizon - th), rng.randint(16, 28))
    elif preset_id in {'hyperborea_temple', 'archon_cathedral', 'ritual_altar'} or any(k in env for k in ('temple', 'sanctuary', 'ruins', 'city', 'architecture', 'throne', 'citadel', 'observatory')):
        far = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(2 if any(k in env_ref for k in ('observatorios','chakana_limpia','heraldos')) else 3):
            bw = rng.randint(w // 10, w // 6)
            bh = rng.randint(h // 7, h // 4)
            bx = rng.randint(0, max(0, w - bw - 1))
            by = horizon - bh - rng.randint(0, 22)
            pygame.draw.rect(far, (mid[0], mid[1], mid[2], 180), (bx, by, bw, bh), border_radius=3)
            pygame.draw.rect(far, (acc[0], acc[1], acc[2], 190), (bx + bw // 4, by - 10, bw // 2, 10), border_radius=2)
        surface.blit(far, (0, 0))
        mid_layer = pygame.Surface((w, h), pygame.SRCALPHA)
        keep = pygame.Rect(int(w * 0.12), int(h * 0.04), int(w * 0.76), int(h * 0.78))
        for _ in range(1 if any(k in env_ref for k in ('observatorios','chakana_limpia','heraldos')) else 2):
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

    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    veil_alpha = 40 if preset.atmospheric_color in {'corruption_fog', 'void_smoke'} else 34
    pygame.draw.rect(veil, (0, 0, 0, veil_alpha), (0, 0, w, h))
    pygame.draw.ellipse(veil, (255, 255, 255, 5), (int(w * 0.26), int(h * 0.18), int(w * 0.48), int(h * 0.40)))
    surface.blit(veil, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)


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
        'warrior_foreground': ['guardian_01.png', 'espada_01.png'],
        'guardian_bearer': ['guardian_01.png'],
        'oracle_totem': ['mago_01.png'],
        'hyperborean_champion': ['guardian_01.png', 'mago_01.png'],
        'hyperborean_foreground': ['guardian_01.png', 'espada_01.png', 'templos_escalonados_01.jpg', 'templos_escalonados_01.png'],
        'archon_throne': ['arconte_01.png', 'heraldos_01.jpg', 'heraldos_01.png'],
        'archon_foreground': ['arconte_01.png', 'sellos_01.png', 'heraldos_01.jpg', 'heraldos_01.png'],
        'archon_beast': ['arconte_01.png', 'puma_01.png'],
        'weapon': ['espada_01.png'],
        'greatsword': ['espada_01.png'],
        'solar_axe': ['espada_01.png'],
        'codex': ['codice_01.png'],
        'altar': ['altar_01.png'],
        'seal': ['sellos_01.png'],
        'seal_tablet': ['sellos_01.png', 'altar_01.png'],
        'crown': ['coronas_01.png'],
        'citadel': ['templos_escalonados_01.jpg', 'templos_escalonados_01.png', 'puentes_antiguos_01.jpg', 'puentes_antiguos_01.png'],
        'throne_realm': ['arconte_01.png', 'heraldos_01.jpg', 'heraldos_01.png'],
        'gaia_sanctuary': ['condor_01.png', 'puma_01.png', 'textiles_andinos_01.jpg', 'textiles_andinos_01.png'],
        'sanctuary': ['guardian_01.png', 'mago_01.png'],
    }
    wanted = preferred.get(subject_kind, []) + preferred.get(object_kind, []) + preferred.get(environment_kind, [])
    explicit = [
        str(semantic.get('subject_ref', '') or '').strip(),
        str(semantic.get('object_ref', '') or '').strip(),
        str(semantic.get('environment_ref', '') or '').strip(),
    ]
    explicit_set = {e.lower() for e in explicit if e}
    wanted_set = {w.lower() for w in wanted}
    if not wanted_set and not explicit_set:
        return refs
    return sorted(refs, key=lambda r: (0 if r.path.name.lower() in explicit_set else 1 if r.path.name.lower() in wanted_set else 2, r.path.name.lower()))


def generate_scene_art(card_id: str, prompt: str, seed: int, out_path: Path) -> dict:
    from game.art.assembly_pipeline import assemble_scene_art
    semantic = semantic_from_prompt(prompt)
    result = assemble_scene_art(card_id, prompt, seed, out_path)
    return {
        'card_id': card_id,
        'path': result.path,
        'generator_used': 'assembly_pipeline_v1',
        'references_used': list(result.references_used),
        'palette_seeded': [result.palette_id],
        'semantic_subject': str(semantic.get('subject', '') or ''),
        'semantic_object': str(semantic.get('object', '') or ''),
        'semantic_environment': str(semantic.get('environment', '') or ''),
        'scene_type': result.scene_type,
        'environment_preset': result.environment_preset,
        'pipeline_order': list(result.pipeline_order),
        'readability_ok': result.metrics.readability_ok,
        'occ_subject': result.metrics.occ_subject,
        'occ_object': result.metrics.occ_object,
        'occ_fx': result.metrics.occ_fx,
    }
