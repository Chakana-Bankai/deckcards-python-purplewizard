from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import pygame

from game.art.environment_library import resolve_environment_preset
from game.art.fx_layer import draw_fx
from game.art.palette_system import resolve_civilization_palette
from game.art.reference_sampler import ReferenceSampler, ReferenceChoice
from game.art.scene_engine import (
    semantic_from_prompt,
    _resolve_explicit_refs,
    _categories_for_prompt,
    _keywords_from_semantic,
    _prioritize_refs,
    _palette_from_refs,
    _strong_foreground_palette,
    _draw_background,
    _apply_contrast,
)
from game.art.silhouette_builder import draw_focus_object, draw_subject

PIPELINE_ORDER = [
    'scene_spec',
    'environment_preset',
    'silhouette',
    'secondary_object',
    'symbol',
    'fx',
    'palette',
    'readability_validation',
]


@dataclass(slots=True)
class AssemblyMetrics:
    occ_subject: float
    occ_object: float
    occ_fx: float
    readability_ok: bool


@dataclass(slots=True)
class AssemblyResult:
    card_id: str
    path: str
    pipeline_order: list[str]
    scene_type: str
    environment_preset: str
    palette_id: str
    references_used: list[str]
    metrics: AssemblyMetrics


def _occ_ratio(layer: pygame.Surface) -> float:
    mask = pygame.mask.from_surface(layer)
    return round(mask.count() / max(1, layer.get_width() * layer.get_height()), 4)


def _draw_symbol(layer: pygame.Surface, semantic: dict, palette, rng: random.Random):
    symbol = str(semantic.get('symbol', '') or '').lower()
    if not symbol:
        return
    w, h = layer.get_size()
    cx = w // 2
    cy = int(h * 0.34)
    accent = palette[3]
    soft = (*accent, 88)
    if 'chakana' in symbol:
        size = int(min(w, h) * 0.10)
        pygame.draw.line(layer, soft, (cx - size, cy), (cx + size, cy), 2)
        pygame.draw.line(layer, soft, (cx, cy - size), (cx, cy + size), 2)
        pygame.draw.rect(layer, soft, (cx - size // 2, cy - size // 2, size, size), 1)
    elif 'seal' in symbol or 'sigil' in symbol:
        r = int(min(w, h) * 0.08)
        pygame.draw.circle(layer, soft, (cx, cy), r, 2)
        pygame.draw.line(layer, soft, (cx - r, cy), (cx + r, cy), 2)
    elif 'solar' in symbol:
        r = int(min(w, h) * 0.07)
        pygame.draw.circle(layer, soft, (cx, cy), r, 2)
        for dx, dy in ((0, -r-8), (r+8, 0), (0, r+8), (-r-8, 0)):
            pygame.draw.line(layer, soft, (cx, cy), (cx + dx, cy + dy), 2)


def validate_readability(subject_layer: pygame.Surface, object_layer: pygame.Surface, fx_layer: pygame.Surface) -> AssemblyMetrics:
    occ_subject = _occ_ratio(subject_layer)
    occ_object = _occ_ratio(object_layer)
    occ_fx = _occ_ratio(fx_layer)
    readability_ok = occ_subject >= 0.20 and occ_object >= 0.035 and occ_fx <= 0.15
    return AssemblyMetrics(occ_subject=occ_subject, occ_object=occ_object, occ_fx=occ_fx, readability_ok=readability_ok)


def assembly_pipeline_summary() -> dict[str, object]:
    return {
        'pipeline_order': list(PIPELINE_ORDER),
        'readability_thresholds': {
            'occ_subject_min': 0.20,
            'occ_object_min': 0.035,
            'occ_fx_max': 0.15,
        },
    }


def assemble_scene_art(card_id: str, prompt: str, seed: int, out_path: Path) -> AssemblyResult:
    rng = random.Random(seed)
    semantic = semantic_from_prompt(prompt)
    sampler = ReferenceSampler()
    explicit_refs = _resolve_explicit_refs(sampler, semantic)
    sampled_refs = sampler.pick(_categories_for_prompt(prompt), _keywords_from_semantic(semantic), seed)
    refs: list[ReferenceChoice] = []
    seen: set[str] = set()
    source_refs = explicit_refs if explicit_refs else _prioritize_refs(sampled_refs, semantic)
    max_refs = 3 if explicit_refs else 6
    for ref in source_refs:
        key = str(ref.path).lower()
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)
        if len(refs) >= max_refs:
            break
    if not explicit_refs:
        refs = _prioritize_refs(refs, semantic)

    civ = resolve_civilization_palette(semantic)
    palette = _palette_from_refs(refs, semantic)
    fg_palette = _strong_foreground_palette(palette, semantic.get('subject_kind', ''), semantic.get('object_kind', ''))
    env_preset = resolve_environment_preset(semantic.get('scene_type', ''), semantic.get('environment_kind', ''), semantic.get('environment', ''))

    work = pygame.Surface((768, 768), pygame.SRCALPHA, 32)
    _draw_background(work, semantic, palette, rng)

    subject_layer = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    object_layer = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    symbol_layer = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    fx_layer = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    shadow_layer = pygame.Surface(work.get_size(), pygame.SRCALPHA)

    pygame.draw.ellipse(shadow_layer, (0, 0, 0, 132), (int(work.get_width() * 0.12), int(work.get_height() * 0.63), int(work.get_width() * 0.76), int(work.get_height() * 0.18)))
    draw_subject(subject_layer, semantic, refs, fg_palette, rng)
    draw_focus_object(object_layer, semantic, fg_palette, rng)
    _draw_symbol(symbol_layer, semantic, fg_palette, rng)
    draw_fx(fx_layer, semantic, palette, rng)

    for layer in (shadow_layer, subject_layer, object_layer, symbol_layer, fx_layer):
        work.blit(layer, (0, 0))

    _apply_contrast(work)
    final = pygame.transform.smoothscale(work, (320, 220)).convert_alpha()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(final, str(out_path))

    metrics = validate_readability(subject_layer, object_layer, fx_layer)
    return AssemblyResult(
        card_id=card_id,
        path=str(out_path),
        pipeline_order=list(PIPELINE_ORDER),
        scene_type=str(semantic.get('scene_type', '') or ''),
        environment_preset=env_preset.preset_id,
        palette_id=civ.palette_id,
        references_used=[r.path.name for r in refs[:4]],
        metrics=metrics,
    )
