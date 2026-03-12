from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
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
from game.art.art_reference_catalog import iter_category_entries
from game.art.silhouette_builder import draw_focus_object, draw_subject
from game.core.paths import art_reference_dir

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

SCENE_WORK_SIZE = (1920, 1080)
SCENE_OUTPUT_SIZE = (1920, 1080)


@dataclass(slots=True)
class LayerSpec:
    layer_id: str
    surface_size: tuple[int, int]
    dest_rect: tuple[int, int, int, int]


LAYER_SPECS = {
    'background': LayerSpec('background', SCENE_WORK_SIZE, (0, 0, 1920, 1080)),
    'subject': LayerSpec('subject', (1600, 900), (160, 70, 1600, 900)),
    'object': LayerSpec('object', (1280, 720), (560, 220, 1280, 720)),
    'symbol': LayerSpec('symbol', (960, 540), (480, 40, 960, 540)),
    'fx': LayerSpec('fx', SCENE_WORK_SIZE, (0, 0, 1920, 1080)),
    'shadow': LayerSpec('shadow', SCENE_WORK_SIZE, (0, 0, 1920, 1080)),
}


@dataclass(slots=True)
class AssemblyMetrics:
    occ_subject: float
    occ_object: float
    occ_fx: float
    contrast_score: float
    focus_balance: float
    readability_ok: bool


@dataclass(slots=True)
class AssemblyResult:
    card_id: str
    path: str
    pipeline_order: list[str]
    scene_type: str
    environment_preset: str
    palette_id: str
    output_resolution: tuple[int, int]
    layer_layout: dict[str, dict[str, object]]
    references_used: list[str]
    metrics: AssemblyMetrics


def _occ_ratio(layer: pygame.Surface) -> float:
    mask = pygame.mask.from_surface(layer)
    return round(mask.count() / max(1, layer.get_width() * layer.get_height()), 4)


def _sample_luma(surface: pygame.Surface, rect: pygame.Rect, step: int = 24) -> float:
    rect = rect.clip(surface.get_rect())
    if rect.width <= 0 or rect.height <= 0:
        return 0.0
    total = 0.0
    count = 0
    for x in range(rect.left, rect.right, max(1, step)):
        for y in range(rect.top, rect.bottom, max(1, step)):
            c = surface.get_at((x, y))
            total += (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0
            count += 1
    return total / max(1, count)


def _contrast_score(subject_layer: pygame.Surface, object_layer: pygame.Surface, final_surface: pygame.Surface) -> float:
    subject_box = subject_layer.get_bounding_rect(min_alpha=12)
    object_box = object_layer.get_bounding_rect(min_alpha=12)
    union = subject_box.union(object_box) if object_box.width and object_box.height else subject_box
    if union.width <= 0 or union.height <= 0:
        union = pygame.Rect(int(final_surface.get_width() * 0.28), int(final_surface.get_height() * 0.14), int(final_surface.get_width() * 0.44), int(final_surface.get_height() * 0.68))
    outer = union.inflate(max(60, union.width // 4), max(60, union.height // 4)).clip(final_surface.get_rect())
    subj_luma = _sample_luma(final_surface, union, max(8, union.width // 20))

    total = 0.0
    count = 0
    step = max(10, outer.width // 26)
    for x in range(outer.left, outer.right, step):
        for y in range(outer.top, outer.bottom, step):
            if union.collidepoint(x, y):
                continue
            c = final_surface.get_at((x, y))
            total += (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0
            count += 1
    if count <= 0:
        bg_luma = _sample_luma(final_surface, outer, step)
    else:
        bg_luma = total / count
    return round(min(1.0, abs(subj_luma - bg_luma) * 4.2), 4)


def _focus_balance(subject_layer: pygame.Surface, object_layer: pygame.Surface, size: tuple[int, int]) -> float:
    w, h = size
    subj = subject_layer.get_bounding_rect(min_alpha=12)
    obj = object_layer.get_bounding_rect(min_alpha=12)
    score = 0.0
    if subj.width > 0 and subj.height > 0:
        subj_cx = subj.centerx / max(1, w)
        subj_cy = subj.centery / max(1, h)
        score += max(0.0, 1.0 - abs(subj_cx - 0.5) * 1.8)
        score += max(0.0, 1.0 - abs(subj_cy - 0.52) * 2.0)
    if obj.width > 0 and obj.height > 0:
        obj_cx = obj.centerx / max(1, w)
        obj_cy = obj.centery / max(1, h)
        score += max(0.0, 1.0 - abs(obj_cx - 0.62) * 2.2)
        score += max(0.0, 1.0 - abs(obj_cy - 0.58) * 2.0)
    return round(score / 4.0, 4)


def _draw_foreground_plane(surface: pygame.Surface, palette, rng: random.Random):
    w, h = surface.get_size()
    low = palette[2]
    accent = palette[3]
    plane = pygame.Surface((w, h), pygame.SRCALPHA)
    horizon = int(h * 0.70)
    pts = [(0, h), (0, horizon), (int(w * 0.18), int(h * 0.67)), (int(w * 0.38), int(h * 0.73)), (int(w * 0.62), int(h * 0.69)), (int(w * 0.84), int(h * 0.74)), (w, int(h * 0.68)), (w, h)]
    pygame.draw.polygon(plane, (max(12, low[0] // 2), max(12, low[1] // 2), max(12, low[2] // 2), 210), pts)
    for _ in range(6):
        x = rng.randint(0, w - 1)
        y = rng.randint(horizon - h // 20, h - 1)
        rw = rng.randint(w // 18, w // 9)
        rh = rng.randint(h // 18, h // 10)
        pygame.draw.ellipse(plane, (accent[0], accent[1], accent[2], 28), (x - rw // 2, y - rh // 2, rw, rh))
    surface.blit(plane, (0, 0))


def _separate_planes(surface: pygame.Surface, subject_layer: pygame.Surface, object_layer: pygame.Surface, palette):
    w, h = surface.get_size()
    focus = subject_layer.get_bounding_rect(min_alpha=12)
    obj = object_layer.get_bounding_rect(min_alpha=12)
    if obj.width > 0 and obj.height > 0:
        focus = focus.union(obj)
    if focus.width <= 0 or focus.height <= 0:
        return
    pad_x = max(60, w // 14)
    pad_y = max(50, h // 12)
    halo = focus.inflate(pad_x * 2, pad_y * 2).clip(surface.get_rect())

    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 34))
    pygame.draw.ellipse(shade, (0, 0, 0, 0), halo)
    surface.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    rim = pygame.Surface((w, h), pygame.SRCALPHA)
    accent = palette[3]
    pygame.draw.ellipse(rim, (accent[0], accent[1], accent[2], 22), halo.inflate(-pad_x // 2, -pad_y // 2), max(2, w // 640))
    surface.blit(rim, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    floor = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(floor, (255, 255, 255, 16), (focus.x, min(h - 1, focus.bottom - focus.h // 8), focus.w, max(20, focus.h // 6)))
    surface.blit(floor, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


@lru_cache(maxsize=128)
def _reference_lookup(category: str, needle: str) -> str:
    root = Path(art_reference_dir())
    target = str(needle or '').strip().lower()
    if not target:
        return ''
    for entry in iter_category_entries(root, category):
        if target in entry.path.name.lower() or target in entry.path.stem.lower():
            return str(entry.path)
    return ''


def _pick_environment_reference(semantic: dict, refs: list[ReferenceChoice]) -> Path | None:
    explicit = str(semantic.get('environment_ref', '') or '').strip().lower()
    if explicit:
        found = _reference_lookup('environments', explicit)
        if found:
            return Path(found)
    for ref in refs:
        if str(ref.category or '').lower() == 'environments':
            return Path(ref.path)
    env = str(semantic.get('environment', '') or '').lower().replace(',', ' ')
    for token in env.split():
        if len(token) < 4:
            continue
        found = _reference_lookup('environments', token)
        if found:
            return Path(found)
    kind = str(semantic.get('environment_kind', '') or '').lower().replace(' ', '_')
    if kind:
        found = _reference_lookup('environments', kind)
        if found:
            return Path(found)
    return None


def _blit_environment_reference(layer: pygame.Surface, ref_path: Path | None, palette) -> bool:
    if not ref_path:
        return False
    try:
        src = pygame.image.load(str(ref_path)).convert()
    except Exception:
        return False
    sw, sh = src.get_size()
    lw, lh = layer.get_size()
    if sw <= 4 or sh <= 4:
        return False
    scale = max(lw / max(1, sw), lh / max(1, sh))
    scaled = pygame.transform.smoothscale(src, (max(1, int(sw * scale)), max(1, int(sh * scale)))).convert()
    crop = pygame.Rect(max(0, (scaled.get_width() - lw) // 2), max(0, (scaled.get_height() - lh) // 2), lw, lh)
    framed = pygame.Surface((lw, lh), pygame.SRCALPHA)
    framed.blit(scaled, (0, 0), crop)
    tint = pygame.Surface((lw, lh), pygame.SRCALPHA)
    top, mid, low, acc = palette
    tint.fill((mid[0], mid[1], mid[2], 54))
    framed.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    glow = pygame.Surface((lw, lh), pygame.SRCALPHA)
    glow.fill((acc[0], acc[1], acc[2], 22))
    framed.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    shade = pygame.Surface((lw, lh), pygame.SRCALPHA)
    pygame.draw.rect(shade, (0, 0, 0, 46), (0, int(lh * 0.58), lw, int(lh * 0.42)))
    framed.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    veil = pygame.Surface((lw, lh), pygame.SRCALPHA)
    veil.fill((255, 255, 255, 34))
    framed.blit(veil, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    layer.blit(framed, (0, 0))
    return True


def _draw_symbol(layer: pygame.Surface, semantic: dict, palette, rng: random.Random):
    symbol = str(semantic.get('symbol', '') or '').lower()
    if not symbol:
        return
    w, h = layer.get_size()
    cx = w // 2
    cy = int(h * 0.34)
    accent = palette[3]
    soft = (*accent, 88)
    line_w = max(2, min(w, h) // 180)
    if 'chakana' in symbol:
        size = int(min(w, h) * 0.10)
        pygame.draw.line(layer, soft, (cx - size, cy), (cx + size, cy), line_w)
        pygame.draw.line(layer, soft, (cx, cy - size), (cx, cy + size), line_w)
        pygame.draw.rect(layer, soft, (cx - size // 2, cy - size // 2, size, size), max(1, line_w - 1))
    elif 'seal' in symbol or 'sigil' in symbol:
        r = int(min(w, h) * 0.08)
        pygame.draw.circle(layer, soft, (cx, cy), r, line_w)
        pygame.draw.line(layer, soft, (cx - r, cy), (cx + r, cy), line_w)
    elif 'solar' in symbol:
        r = int(min(w, h) * 0.07)
        pygame.draw.circle(layer, soft, (cx, cy), r, line_w)
        ray = max(8, min(w, h) // 30)
        for dx, dy in ((0, -r-ray), (r+ray, 0), (0, r+ray), (-r-ray, 0)):
            pygame.draw.line(layer, soft, (cx, cy), (cx + dx, cy + dy), line_w)


def _layer_layout_summary() -> dict[str, dict[str, object]]:
    return {
        key: {
            'surface_size': list(spec.surface_size),
            'dest_rect': list(spec.dest_rect),
        }
        for key, spec in LAYER_SPECS.items()
    }


def _composite_layer(target: pygame.Surface, layer_surface: pygame.Surface, spec: LayerSpec) -> pygame.Surface:
    out = pygame.Surface(target.get_size(), pygame.SRCALPHA)
    dest = pygame.Rect(spec.dest_rect)
    if layer_surface.get_size() != dest.size:
        scaled = pygame.transform.smoothscale(layer_surface, dest.size).convert_alpha()
    else:
        scaled = layer_surface
    out.blit(scaled, dest.topleft)
    target.blit(out, (0, 0))
    return out


def validate_readability(subject_layer: pygame.Surface, object_layer: pygame.Surface, fx_layer: pygame.Surface, final_surface: pygame.Surface, object_kind: str = '') -> AssemblyMetrics:
    occ_subject = _occ_ratio(subject_layer)
    occ_object = _occ_ratio(object_layer)
    occ_fx = _occ_ratio(fx_layer)
    contrast_score = _contrast_score(subject_layer, object_layer, final_surface)
    focus_balance = _focus_balance(subject_layer, object_layer, final_surface.get_size())
    low_object = str(object_kind or '').lower().replace(' ', '_') in {'weapon', 'greatsword', 'solar_axe'}
    object_threshold = 0.02 if low_object else 0.03
    readability_ok = occ_subject >= 0.20 and occ_object >= object_threshold and occ_fx <= 0.18 and contrast_score >= 0.10 and focus_balance >= 0.42
    return AssemblyMetrics(occ_subject=occ_subject, occ_object=occ_object, occ_fx=occ_fx, contrast_score=contrast_score, focus_balance=focus_balance, readability_ok=readability_ok)


def assembly_pipeline_summary() -> dict[str, object]:
    return {
        'pipeline_order': list(PIPELINE_ORDER),
        'work_resolution': list(SCENE_WORK_SIZE),
        'output_resolution': list(SCENE_OUTPUT_SIZE),
        'layer_layout': _layer_layout_summary(),
        'readability_thresholds': {
            'occ_subject_min': 0.20,
            'occ_object_min': 0.03,
            'occ_object_min_elongated': 0.02,
            'occ_fx_max': 0.18,
            'contrast_score_min': 0.10,
            'focus_balance_min': 0.42,
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

    work = pygame.Surface(SCENE_WORK_SIZE, pygame.SRCALPHA, 32)

    background_layer = pygame.Surface(LAYER_SPECS['background'].surface_size, pygame.SRCALPHA)
    _draw_background(background_layer, semantic, palette, rng)
    env_ref_path = _pick_environment_reference(semantic, refs)
    _blit_environment_reference(background_layer, env_ref_path, palette)
    _draw_foreground_plane(background_layer, palette, rng)
    _composite_layer(work, background_layer, LAYER_SPECS['background'])

    subject_source = pygame.Surface(LAYER_SPECS['subject'].surface_size, pygame.SRCALPHA)
    object_source = pygame.Surface(LAYER_SPECS['object'].surface_size, pygame.SRCALPHA)
    symbol_source = pygame.Surface(LAYER_SPECS['symbol'].surface_size, pygame.SRCALPHA)
    fx_source = pygame.Surface(LAYER_SPECS['fx'].surface_size, pygame.SRCALPHA)
    shadow_source = pygame.Surface(LAYER_SPECS['shadow'].surface_size, pygame.SRCALPHA)

    shadow_rect = pygame.Rect(LAYER_SPECS['subject'].dest_rect)
    pygame.draw.ellipse(
        shadow_source,
        (0, 0, 0, 132),
        (
            int(shadow_rect.x + shadow_rect.w * 0.16),
            int(shadow_rect.y + shadow_rect.h * 0.82),
            int(shadow_rect.w * 0.68),
            int(shadow_rect.h * 0.14),
        ),
    )

    draw_subject(subject_source, semantic, refs, fg_palette, rng)
    draw_focus_object(object_source, semantic, refs, fg_palette, rng)
    _draw_symbol(symbol_source, semantic, fg_palette, rng)
    draw_fx(fx_source, semantic, palette, rng)

    shadow_layer = _composite_layer(work, shadow_source, LAYER_SPECS['shadow'])
    subject_layer = _composite_layer(work, subject_source, LAYER_SPECS['subject'])
    object_layer = _composite_layer(work, object_source, LAYER_SPECS['object'])
    symbol_layer = _composite_layer(work, symbol_source, LAYER_SPECS['symbol'])
    fx_layer = _composite_layer(work, fx_source, LAYER_SPECS['fx'])

    _separate_planes(work, subject_layer, object_layer, palette)
    _apply_contrast(work)
    final = pygame.transform.smoothscale(work, SCENE_OUTPUT_SIZE).convert_alpha()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(final, str(out_path))

    metrics = validate_readability(subject_layer, object_layer, fx_layer, work, str(semantic.get('object_kind', '') or ''))
    return AssemblyResult(
        card_id=card_id,
        path=str(out_path),
        pipeline_order=list(PIPELINE_ORDER),
        scene_type=str(semantic.get('scene_type', '') or ''),
        environment_preset=env_preset.preset_id,
        palette_id=civ.palette_id,
        output_resolution=SCENE_OUTPUT_SIZE,
        layer_layout=_layer_layout_summary(),
        references_used=[r.path.name for r in refs[:4]],
        metrics=metrics,
    )
