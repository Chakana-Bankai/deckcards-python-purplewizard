from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import random

import pygame
from rich.console import Console

from game.art.art_stack_accel import (
    blur_score_cv,
    load_reference_with_pillow,
    noise_overlay,
    save_surface_with_pillow,
    surface_alpha_array,
    surface_luma_array,
    surface_rgba_array,
)
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
from game.art.character_compositor import compose_character_subject
from game.art.finish_render_system import apply_scene_finish
from game.art.scene_spec import validate_scene_semantic
from game.core.paths import art_reference_dir

PIPELINE_ORDER = [
    'entity_type_detection',
    'grammar_selection',
    'skeleton_or_structure_points',
    'body_or_shape_volumes',
    'silhouette_merge',
    'anchor_placement',
    'object_integration',
    'scene_placement',
    'symbol_placement',
    'fx_layers',
    'final_grade',
    'readability_validation',
]

SCENE_COMPOSITION_SIZE = (480, 270)
SCENE_OUTPUT_SIZE = (1920, 1080)
SAFE_ART_ZONE_RATIO = 0.70
MAX_OCC_SUBJECT = 0.40
MAX_OCC_OBJECT = 0.25
TARGET_BACKGROUND_RATIO = 0.35
SKY_ZONE_RATIO = 0.30
SUBJECT_ZONE_RATIO = 0.40
GROUND_ZONE_RATIO = 0.30

REQUIRED_OCC_SUBJECT = 0.22
REQUIRED_OCC_OBJECT = 0.06
REQUIRED_CONTRAST = 0.62
REQUIRED_SUBJECT_VISIBLE = 0.80
REQUIRED_MAX_FX_OCCLUSION = 0.15
REQUIRED_MIN_WEAPON_ATTACHED = 0.85
REQUIRED_MAX_WHITE_CLIP = 0.05
REQUIRED_MIN_SILHOUETTE_INTEGRITY = 0.75
REQUIRED_MIN_LIMB_CONNECTION = 0.72
REQUIRED_MIN_FRONTAL_BLOCK = 0.42
REQUIRED_MIN_GRAMMAR_MATCH = 0.80
PREFERRED_OCC_SUBJECT_RANGE = (0.28, 0.38)
PREFERRED_OCC_OBJECT_RANGE = (0.08, 0.14)

console = Console(stderr=True, highlight=False)


@dataclass(slots=True)
class LayerSpec:
    layer_id: str
    surface_size: tuple[int, int]
    dest_rect: tuple[int, int, int, int]


LAYER_SPECS = {
    'background': LayerSpec('background', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'environment': LayerSpec('environment', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'subject_mask': LayerSpec('subject_mask', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'subject_detail': LayerSpec('subject_detail', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'weapon_back': LayerSpec('weapon_back', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'object_mask': LayerSpec('object_mask', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'weapon_front': LayerSpec('weapon_front', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'symbol': LayerSpec('symbol', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'fx_back': LayerSpec('fx_back', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
    'fx_front': LayerSpec('fx_front', SCENE_COMPOSITION_SIZE, (0, 0, *SCENE_COMPOSITION_SIZE)),
}


@dataclass(slots=True)
class AssemblyMetrics:
    occ_subject: float
    occ_object: float
    occ_fx: float
    contrast_score: float
    focus_balance: float
    readability_ok: bool
    white_clip_ratio: float
    subject_visible_ratio: float
    subject_occluded_by_fx_ratio: float
    weapon_attached_ratio: float
    silhouette_integrity: float
    limb_connection_score: float
    frontal_block_score: float
    grammar_match_score: float


@dataclass(slots=True)
class AssemblyResult:
    card_id: str
    path: str
    pipeline_order: list[str]
    scene_type: str
    environment_preset: str
    palette_id: str
    output_resolution: tuple[int, int]
    composition_resolution: tuple[int, int]
    layer_layout: dict[str, dict[str, object]]
    references_used: list[str]
    metrics: AssemblyMetrics


def _occ_ratio(layer: pygame.Surface, alpha_cutoff: int = 12) -> float:
    alpha = surface_alpha_array(layer)
    return round(float((alpha > alpha_cutoff).mean()), 4)


def _sample_luma(surface: pygame.Surface, rect: pygame.Rect, step: int = 6) -> float:
    rect = rect.clip(surface.get_rect())
    if rect.width <= 0 or rect.height <= 0:
        return 0.0
    luma = surface_luma_array(surface)
    stride = max(1, step)
    sample = luma[rect.top:rect.bottom:stride, rect.left:rect.right:stride]
    if sample.size == 0:
        return 0.0
    return float(sample.mean())


def _masked_luma(surface: pygame.Surface, mask_layer: pygame.Surface, step: int = 4) -> float:
    bounds = mask_layer.get_bounding_rect(min_alpha=12).clip(surface.get_rect())
    if bounds.width <= 0 or bounds.height <= 0:
        return 0.0
    stride = max(1, step)
    luma = surface_luma_array(surface)[bounds.top:bounds.bottom:stride, bounds.left:bounds.right:stride]
    alpha = surface_alpha_array(mask_layer)[bounds.top:bounds.bottom:stride, bounds.left:bounds.right:stride]
    masked = luma[alpha > 12]
    if masked.size == 0:
        return 0.0
    return float(masked.mean())


def _merge_layers(*layers: pygame.Surface) -> pygame.Surface:
    if not layers:
        raise ValueError('at least one layer is required')
    merged = pygame.Surface(layers[0].get_size(), pygame.SRCALPHA)
    for layer in layers:
        merged.blit(layer, (0, 0))
    return merged


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
        if blur_score_cv(ref_path) < 35.0:
            console.print(f"[yellow]art-ref warning[/yellow] skipped blurry environment ref: {ref_path.name}")
            return False
        framed = load_reference_with_pillow(ref_path, layer.get_size())
    except Exception:
        return False
    lw, lh = layer.get_size()
    mid = palette[1]
    low = palette[2]
    acc = palette[3]
    tint = pygame.Surface((lw, lh), pygame.SRCALPHA)
    tint.fill((mid[0], mid[1], mid[2], 42))
    framed.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    shade = pygame.Surface((lw, lh), pygame.SRCALPHA)
    pygame.draw.rect(shade, (0, 0, 0, 44), (0, int(lh * 0.52), lw, int(lh * 0.48)))
    framed.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    glow = pygame.Surface((lw, lh), pygame.SRCALPHA)
    glow.fill((acc[0], acc[1], acc[2], 6))
    framed.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    floor = pygame.Surface((lw, lh), pygame.SRCALPHA)
    pygame.draw.rect(floor, (low[0], low[1], low[2], 22), (0, int(lh * 0.70), lw, int(lh * 0.30)))
    framed.blit(floor, (0, 0))
    layer.blit(framed, (0, 0))
    return True


def _build_scene_sectors(size: tuple[int, int]) -> dict[str, pygame.Rect]:
    w, h = size
    sky_h = int(h * SKY_ZONE_RATIO)
    subject_h = int(h * SUBJECT_ZONE_RATIO)
    ground_h = h - sky_h - subject_h
    safe_w = int(w * SAFE_ART_ZONE_RATIO)
    safe_h = int(h * SAFE_ART_ZONE_RATIO)
    safe_rect = pygame.Rect((w - safe_w) // 2, (h - safe_h) // 2, safe_w, safe_h)
    sky_sector = pygame.Rect(0, 0, w, sky_h)
    center_subject_zone = pygame.Rect(int(w * 0.25), sky_h, int(w * 0.50), subject_h)
    ground_sector = pygame.Rect(0, sky_h + subject_h, w, ground_h)
    subject_sector = center_subject_zone.clip(safe_rect)
    object_sector = pygame.Rect(
        int(center_subject_zone.left + center_subject_zone.width * 0.58),
        int(center_subject_zone.top + center_subject_zone.height * 0.08),
        int(center_subject_zone.width * 0.26),
        int(center_subject_zone.height * 0.74),
    ).clip(safe_rect)
    symbol_sector = pygame.Rect(
        int(center_subject_zone.left + center_subject_zone.width * 0.12),
        max(0, int(sky_sector.bottom - center_subject_zone.height * 0.18)),
        int(center_subject_zone.width * 0.68),
        int(center_subject_zone.height * 0.26),
    ).clip(pygame.Rect(0, 0, w, h))
    fx_front_sector = subject_sector.inflate(-int(subject_sector.width * 0.18), -int(subject_sector.height * 0.22)).clip(safe_rect)
    return {
        'background_sector': pygame.Rect(0, 0, w, h),
        'environment_sector': pygame.Rect(0, 0, w, h),
        'safe_art_sector': safe_rect,
        'sky_sector': sky_sector,
        'subject_center_zone': center_subject_zone,
        'ground_sector': ground_sector,
        'subject_sector': subject_sector,
        'object_sector': object_sector,
        'symbol_sector': symbol_sector,
        'fx_back_sector': safe_rect.inflate(int(safe_rect.width * 0.08), int(safe_rect.height * 0.06)).clip(pygame.Rect(0, 0, w, h)),
        'fx_front_sector': fx_front_sector,
    }


def _suppress_bright_rectangular_intrusions(layer: pygame.Surface, subject_layout: dict[str, object], sectors: dict[str, pygame.Rect]):
    subject_rect = subject_layout['rect'].clip(layer.get_rect())
    if subject_rect.width <= 0 or subject_rect.height <= 0:
        return
    corridor = pygame.Rect(
        subject_rect.centerx,
        max(0, int(subject_rect.top - subject_rect.height * 0.10)),
        min(layer.get_width() - subject_rect.centerx, int(subject_rect.width * 0.82)),
        int(subject_rect.height * 0.95),
    ).clip(sectors['environment_sector'])
    if corridor.width <= 0 or corridor.height <= 0:
        return
    for y in range(corridor.top, corridor.bottom):
        for x in range(corridor.left, corridor.right):
            c = layer.get_at((x, y))
            luma = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0
            chroma = (max(c.r, c.g, c.b) - min(c.r, c.g, c.b)) / 255.0
            if luma < 0.56 or chroma > 0.18:
                continue
            dx = (x - corridor.left) / max(1.0, corridor.width)
            dy = abs(y - subject_rect.centery) / max(1.0, corridor.height / 2.0)
            if dx < 0.10 and dy > 0.75:
                continue
            fade = 0.32 if dx < 0.55 else 0.22
            alpha_cap = 70 if dx < 0.55 else 46
            layer.set_at((x, y), (int(c.r * fade), int(c.g * fade), int(c.b * fade), min(c.a, alpha_cap)))

def _suppress_environment_intrusions(layer: pygame.Surface, subject_layout: dict[str, object], sectors: dict[str, pygame.Rect]):
    subject_rect = subject_layout['rect'].clip(layer.get_rect())
    if subject_rect.width <= 0 or subject_rect.height <= 0:
        return
    corridor = pygame.Rect(
        int(subject_rect.centerx - max(16, subject_rect.width * 0.16)),
        max(0, int(subject_rect.top - subject_rect.height * 0.16)),
        int(max(32, subject_rect.width * 0.32)),
        int(min(layer.get_height(), subject_rect.height * 1.18)),
    ).clip(sectors['subject_sector'].inflate(subject_rect.width // 5, subject_rect.height // 8).clip(layer.get_rect()))
    if corridor.width <= 0 or corridor.height <= 0:
        return
    for y in range(corridor.top, corridor.bottom):
        for x in range(corridor.left, corridor.right):
            c = layer.get_at((x, y))
            if c.a <= 0:
                continue
            dx = abs(x - subject_rect.centerx) / max(1.0, corridor.width / 2.0)
            dy = abs(y - subject_rect.centery) / max(1.0, corridor.height / 2.0)
            center_weight = max(0.0, 1.0 - (dx * 0.75 + dy * 0.35))
            luma = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0
            alpha_cap = int(42 - center_weight * 18)
            shade = 0.28 if luma > 0.40 else 0.40
            layer.set_at((x, y), (int(c.r * shade), int(c.g * shade), int(c.b * shade), min(c.a, max(10, alpha_cap))))


def _draw_foreground_plane(surface: pygame.Surface, palette, rng: random.Random):
    w, h = surface.get_size()
    low = palette[2]
    accent = palette[3]
    plane = pygame.Surface((w, h), pygame.SRCALPHA)
    horizon = int(h * 0.70)
    pts = [(0, h), (0, horizon), (int(w * 0.18), int(h * 0.68)), (int(w * 0.40), int(h * 0.74)), (int(w * 0.62), int(h * 0.70)), (int(w * 0.84), int(h * 0.75)), (w, int(h * 0.70)), (w, h)]
    pygame.draw.polygon(plane, (max(10, low[0] // 2), max(10, low[1] // 2), max(10, low[2] // 2), 138), pts)
    for _ in range(4):
        x = rng.randint(0, w - 1)
        y = rng.randint(horizon - h // 20, h - 1)
        rw = rng.randint(w // 22, w // 12)
        rh = rng.randint(h // 22, h // 12)
        pygame.draw.ellipse(plane, (accent[0], accent[1], accent[2], 12), (x - rw // 2, y - rh // 2, rw, rh))
    surface.blit(plane, (0, 0))
    grain = noise_overlay((w, h), accent, 18, scale=22.0, octaves=2, seed=rng.randint(0, 9999))
    surface.blit(grain, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def _draw_symbol_layer(layer: pygame.Surface, semantic: dict, palette, subject_layout: dict[str, object], sectors: dict[str, pygame.Rect]):
    symbol = str(semantic.get('symbol', '') or '').lower()
    if not symbol:
        return
    subject_rect = subject_layout['rect']
    symbol_center = subject_layout['symbol_center_anchor']
    halo_anchor = subject_layout['halo_anchor']
    max_alpha = 24
    accent = palette[3]
    symbol_surface = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    halo_rect = pygame.Rect(0, 0, int(subject_rect.width * 0.86), int(subject_rect.height * 0.50))
    halo_rect.center = (int(halo_anchor[0]), int(halo_anchor[1]))
    halo_rect.clamp_ip(sectors['symbol_sector'].inflate(0, subject_rect.height // 4).clip(layer.get_rect()))
    pygame.draw.ellipse(symbol_surface, (accent[0], accent[1], accent[2], 16), halo_rect, max(1, layer.get_width() // 220))
    cx = int(symbol_center[0])
    cy = min(sectors['symbol_sector'].bottom - 4, int(symbol_center[1]))
    line_w = max(1, layer.get_width() // 220)
    if 'chakana' in symbol:
        size = max(8, subject_rect.width // 7)
        pygame.draw.line(symbol_surface, (accent[0], accent[1], accent[2], max_alpha), (cx - size, cy), (cx + size, cy), line_w)
        pygame.draw.line(symbol_surface, (accent[0], accent[1], accent[2], max_alpha), (cx, cy - size), (cx, cy + size), line_w)
        pygame.draw.rect(symbol_surface, (accent[0], accent[1], accent[2], max_alpha - 4), (cx - size // 2, cy - size // 2, size, size), line_w)
    elif 'seal' in symbol or 'sigil' in symbol:
        r = max(8, subject_rect.width // 8)
        pygame.draw.circle(symbol_surface, (accent[0], accent[1], accent[2], max_alpha), (cx, cy), r, line_w)
        pygame.draw.line(symbol_surface, (accent[0], accent[1], accent[2], max_alpha - 4), (cx - r, cy), (cx + r, cy), line_w)
    else:
        r = max(8, subject_rect.width // 9)
        pygame.draw.circle(symbol_surface, (accent[0], accent[1], accent[2], max_alpha), (cx, cy), r, line_w)
        for dx, dy in ((0, -r - 5), (r + 5, 0), (0, r + 5), (-r - 5, 0)):
            pygame.draw.line(symbol_surface, (accent[0], accent[1], accent[2], max_alpha - 6), (cx, cy), (cx + dx, cy + dy), line_w)
    pygame.draw.rect(symbol_surface, (0, 0, 0, 0), subject_layout['subject_core_rect'])
    layer.blit(symbol_surface, (0, 0))


def _alpha_mask(source: pygame.Surface, cutoff: int = 48) -> pygame.Surface:
    mask_surface = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    w, h = source.get_size()
    for y in range(h):
        for x in range(w):
            c = source.get_at((x, y))
            if c.a >= cutoff:
                mask_surface.set_at((x, y), (255, 255, 255, 255))
    return mask_surface


def _dilate_mask(mask_surface: pygame.Surface, radius: int = 1) -> pygame.Surface:
    if radius <= 0:
        return mask_surface.copy()
    w, h = mask_surface.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    points = []
    for y in range(h):
        for x in range(w):
            if mask_surface.get_at((x, y)).a > 12:
                points.append((x, y))
    for x, y in points:
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                if ox * ox + oy * oy > radius * radius + radius:
                    continue
                nx = x + ox
                ny = y + oy
                if 0 <= nx < w and 0 <= ny < h:
                    out.set_at((nx, ny), (255, 255, 255, 255))
    return out


def _apply_subject_outline(target: pygame.Surface, subject_mask: pygame.Surface, outline_color):
    mask = pygame.mask.from_surface(subject_mask, 12)
    if mask.count() <= 0:
        return
    outline = mask.outline()
    if len(outline) <= 1:
        return
    width = max(2, min(4, target.get_width() // 160))
    for radius in range(1, width + 1):
        line_w = max(1, width - radius + 1)
        for ox, oy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius), (-radius, -radius), (radius, -radius), (-radius, radius), (radius, radius)):
            pts = [(x + ox, y + oy) for x, y in outline]
            pygame.draw.lines(target, outline_color, True, pts, line_w)


def _enforce_figure_ground_separation(target: pygame.Surface, subject_mask: pygame.Surface, palette):
    subject_box = subject_mask.get_bounding_rect(min_alpha=12).clip(target.get_rect())
    if subject_box.width <= 0 or subject_box.height <= 0:
        return
    subject_luma = _masked_luma(target, subject_mask, step=max(2, subject_box.width // 24))
    outer = subject_box.inflate(max(20, subject_box.width // 3), max(20, subject_box.height // 3)).clip(target.get_rect())
    background_luma = _sample_luma(target, outer, max(2, outer.width // 20))
    if abs(subject_luma - background_luma) >= 0.25:
        return
    outer_mask = _dilate_mask(subject_mask, max(8, min(16, subject_box.width // 9)))
    inner_mask = _dilate_mask(subject_mask, max(3, min(7, subject_box.width // 18)))
    ring_rect = outer_mask.get_bounding_rect(min_alpha=12).clip(target.get_rect())
    for y in range(ring_rect.top, ring_rect.bottom):
        for x in range(ring_rect.left, ring_rect.right):
            if outer_mask.get_at((x, y)).a <= 12 or inner_mask.get_at((x, y)).a > 12:
                continue
            c = target.get_at((x, y))
            target.set_at((x, y), (int(c.r * 0.78), int(c.g * 0.78), int(c.b * 0.80), c.a))
    lift = pygame.Surface(target.get_size(), pygame.SRCALPHA)
    bounds = subject_mask.get_bounding_rect(min_alpha=12)
    for y in range(bounds.top, bounds.bottom):
        for x in range(bounds.left, bounds.right):
            if subject_mask.get_at((x, y)).a > 12:
                lift.set_at((x, y), (palette[3][0], palette[3][1], palette[3][2], 22))
    target.blit(lift, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def _enforce_object_separation(target: pygame.Surface, object_mask: pygame.Surface, subject_mask: pygame.Surface, palette):
    object_box = object_mask.get_bounding_rect(min_alpha=12).clip(target.get_rect())
    if object_box.width <= 0 or object_box.height <= 0:
        return
    subject_box = subject_mask.get_bounding_rect(min_alpha=12).clip(target.get_rect())
    torso = pygame.Rect(subject_box.x + subject_box.width // 4, subject_box.y + subject_box.height // 3, max(1, subject_box.width // 2), max(1, subject_box.height // 3)).clip(target.get_rect())
    object_luma = _masked_luma(target, object_mask, step=max(2, object_box.width // 16))
    torso_luma = _sample_luma(target, torso, max(2, torso.width // 10))
    env_luma = _sample_luma(target, object_box.inflate(max(12, object_box.width // 3), max(12, object_box.height // 3)).clip(target.get_rect()), max(2, object_box.width // 12))
    if min(abs(object_luma - torso_luma), abs(object_luma - env_luma)) >= 0.35:
        return
    glow_mask = _dilate_mask(object_mask, 3)
    accent = palette[3]
    for y in range(object_box.top - 6, object_box.bottom + 6):
        if not (0 <= y < target.get_height()):
            continue
        for x in range(object_box.left - 6, object_box.right + 6):
            if not (0 <= x < target.get_width()):
                continue
            outer = glow_mask.get_at((x, y)).a > 12
            inner = object_mask.get_at((x, y)).a > 12
            if not outer:
                continue
            if inner:
                target.set_at((x, y), (min(255, accent[0]), min(255, accent[1]), min(255, accent[2]), 255))
                continue
            c = target.get_at((x, y))
            boost = 0.22
            target.set_at((x, y), (
                min(255, int(c.r * (1.0 - boost) + accent[0] * boost)),
                min(255, int(c.g * (1.0 - boost) + accent[1] * boost)),
                min(255, int(c.b * (1.0 - boost) + accent[2] * boost)),
                c.a,
            ))


def _clip_layer_alpha(surface: pygame.Surface, max_alpha: int):
    w, h = surface.get_size()
    for y in range(h):
        for x in range(w):
            c = surface.get_at((x, y))
            if c.a > max_alpha:
                surface.set_at((x, y), (c.r, c.g, c.b, max_alpha))


def _compress_highlights(surface: pygame.Surface):
    w, h = surface.get_size()
    for y in range(h):
        for x in range(w):
            c = surface.get_at((x, y))
            if c.a <= 12:
                continue
            avg = (int(c.r) + int(c.g) + int(c.b)) / 3.0
            if avg >= 238:
                factor = 0.68
            elif avg >= 225:
                factor = 0.76
            elif avg >= 210:
                factor = 0.86
            else:
                continue
            surface.set_at((x, y), (int(c.r * factor), int(c.g * factor), int(c.b * factor), c.a))


def _white_clip_ratio(surface: pygame.Surface) -> float:
    rgba = surface_rgba_array(surface)
    alpha = rgba[:, :, 3] > 12
    total = int(alpha.sum())
    if total <= 0:
        return 0.0
    white = (rgba[:, :, 0] >= 245) & (rgba[:, :, 1] >= 245) & (rgba[:, :, 2] >= 245) & alpha
    return round(float(white.sum()) / float(total), 4)


def _overlap_ratio(a: pygame.Surface, b: pygame.Surface, cutoff_a: int = 12, cutoff_b: int = 12) -> float:
    mask_a = pygame.mask.from_surface(_alpha_mask(a, cutoff_a), 12)
    count_a = mask_a.count()
    if count_a <= 0:
        return 0.0
    mask_b = pygame.mask.from_surface(_alpha_mask(b, cutoff_b), 12)
    overlap = mask_a.overlap_mask(mask_b, (0, 0)).count()
    return round(overlap / max(1, count_a), 4)


def _weapon_attached_ratio(object_mask: pygame.Surface, subject_layout: dict[str, object]) -> float:
    grip_rect = subject_layout.get('weapon_grip_rect')
    if isinstance(grip_rect, pygame.Rect) and grip_rect.width > 0 and grip_rect.height > 0:
        box = grip_rect
    else:
        box = object_mask.get_bounding_rect(min_alpha=12)
    if box.width <= 0 or box.height <= 0:
        return 0.0
    anchors = [subject_layout['right_hand_anchor'], subject_layout['left_hand_anchor'], subject_layout['back_anchor']]
    distances = []
    for ax, ay in anchors:
        nearest_x = min(max(ax, box.left), box.right)
        nearest_y = min(max(ay, box.top), box.bottom)
        distances.append(((nearest_x - ax) ** 2 + (nearest_y - ay) ** 2) ** 0.5)
    dist = min(distances)
    max_dist = max(6.0, subject_layout['rect'].height * 0.18)
    return round(max(0.0, 1.0 - (dist / max_dist)), 4)


def _contrast_score(subject_mask: pygame.Surface, object_mask: pygame.Surface, final_surface: pygame.Surface) -> float:
    subject_box = subject_mask.get_bounding_rect(min_alpha=12)
    object_box = object_mask.get_bounding_rect(min_alpha=12)
    union = subject_box.union(object_box) if object_box.width and object_box.height else subject_box
    if union.width <= 0 or union.height <= 0:
        union = pygame.Rect(int(final_surface.get_width() * 0.30), int(final_surface.get_height() * 0.12), int(final_surface.get_width() * 0.40), int(final_surface.get_height() * 0.70))
    outer = union.inflate(max(20, union.width // 3), max(20, union.height // 3)).clip(final_surface.get_rect())
    subject_luma = _masked_luma(final_surface, subject_mask, step=max(2, union.width // 18))
    total = 0.0
    count = 0
    step = max(2, outer.width // 20)
    for x in range(outer.left, outer.right, step):
        for y in range(outer.top, outer.bottom, step):
            if union.collidepoint(x, y):
                continue
            c = final_surface.get_at((x, y))
            total += (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0
            count += 1
    bg_luma = total / max(1, count)
    return round(min(1.0, abs(subject_luma - bg_luma) * 8.6), 4)


def _focus_balance(subject_mask: pygame.Surface, object_mask: pygame.Surface, size: tuple[int, int]) -> float:
    w, h = size
    subj = subject_mask.get_bounding_rect(min_alpha=12)
    obj = object_mask.get_bounding_rect(min_alpha=12)
    score = 0.0
    if subj.width > 0 and subj.height > 0:
        score += max(0.0, 1.0 - abs((subj.centerx / max(1, w)) - 0.5) * 1.8)
        score += max(0.0, 1.0 - abs((subj.centery / max(1, h)) - 0.53) * 2.0)
        subject_height_ratio = subj.height / max(1, h)
        score += max(0.0, 1.0 - abs(subject_height_ratio - 0.53) * 2.5)
    if obj.width > 0 and obj.height > 0:
        score += max(0.0, 1.0 - abs((obj.centerx / max(1, w)) - 0.62) * 2.2)
    return round(score / 4.0, 4)



def _grammar_match_score(subject_layout: dict[str, object], occ_subject: float, occ_object: float, weapon_attached_ratio: float, silhouette_integrity: float) -> float:
    grammar_profile = str(subject_layout.get('grammar_profile_id', '') or '')
    subgrammar_id = str(subject_layout.get('subgrammar_id', '') or '')
    ratios = subject_layout.get('grammar_ratios', {})
    checks = []
    checks.append(1.0 if grammar_profile == 'HUMANOID' else 0.4)
    checks.append(1.0 if subgrammar_id in {'ARCHON', 'SOLAR_WARRIOR', 'GUIDE_MAGE'} else 0.4)
    def within(value: float, low: float, high: float) -> float:
        if low <= value <= high:
            return 1.0
        dist = low - value if value < low else value - high
        return max(0.0, 1.0 - dist * 6.0)
    checks.append(within(float(ratios.get('head_ratio', 0.0)), 0.16, 0.18))
    checks.append(within(float(ratios.get('torso_ratio', 0.0)), 0.30, 0.34))
    checks.append(within(float(ratios.get('leg_ratio', 0.0)), 0.34, 0.40))
    checks.append(within(float(ratios.get('arm_ratio', 0.0)), 0.30, 0.36))
    checks.append(within(float(ratios.get('shoulder_ratio', 0.0)), 1.7, 2.0))
    checks.append(max(0.0, min(1.0, occ_subject / 0.28)))
    checks.append(max(0.0, min(1.0, occ_object / 0.06)))
    checks.append(weapon_attached_ratio)
    checks.append(silhouette_integrity)
    return round(sum(checks) / max(1, len(checks)), 4)
def validate_readability(subject_mask: pygame.Surface, object_mask: pygame.Surface, fx_mask: pygame.Surface, symbol_mask: pygame.Surface, final_surface: pygame.Surface, subject_layout: dict[str, object]) -> AssemblyMetrics:
    occ_subject = _occ_ratio(subject_mask, 12)
    occ_object = _occ_ratio(object_mask, 12)
    occ_fx = _occ_ratio(fx_mask, 20)
    contrast_score = _contrast_score(subject_mask, object_mask, final_surface)
    focus_balance = _focus_balance(subject_mask, object_mask, final_surface.get_size())
    subject_occluded_by_fx_ratio = _overlap_ratio(subject_mask, fx_mask, 12, 20)
    subject_occluded_by_symbol_ratio = _overlap_ratio(subject_mask, symbol_mask, 12, 20)
    subject_visible_ratio = round(max(0.0, 1.0 - subject_occluded_by_fx_ratio - min(0.10, subject_occluded_by_symbol_ratio)), 4)
    white_clip_ratio = _white_clip_ratio(final_surface)
    weapon_attached_ratio = _weapon_attached_ratio(object_mask, subject_layout)
    silhouette_integrity = round(float(subject_layout.get('silhouette_integrity', 0.0)), 4)
    limb_connection_score = round(float(subject_layout.get('limb_connection_score', 0.0)), 4)
    frontal_block_score = round(float(subject_layout.get('frontal_block_score', 0.0)), 4)
    grammar_match_score = _grammar_match_score(subject_layout, occ_subject, occ_object, weapon_attached_ratio, silhouette_integrity)
    readability_ok = (
        occ_subject >= REQUIRED_OCC_SUBJECT
        and occ_subject <= MAX_OCC_SUBJECT
        and occ_object >= REQUIRED_OCC_OBJECT
        and occ_object <= MAX_OCC_OBJECT
        and contrast_score >= REQUIRED_CONTRAST
        and subject_visible_ratio >= REQUIRED_SUBJECT_VISIBLE
        and subject_occluded_by_fx_ratio <= REQUIRED_MAX_FX_OCCLUSION
        and weapon_attached_ratio >= REQUIRED_MIN_WEAPON_ATTACHED
        and white_clip_ratio <= REQUIRED_MAX_WHITE_CLIP
        and silhouette_integrity >= REQUIRED_MIN_SILHOUETTE_INTEGRITY
        and limb_connection_score >= REQUIRED_MIN_LIMB_CONNECTION
        and frontal_block_score >= REQUIRED_MIN_FRONTAL_BLOCK
        and grammar_match_score >= REQUIRED_MIN_GRAMMAR_MATCH
    )
    return AssemblyMetrics(
        occ_subject=round(occ_subject, 4),
        occ_object=round(occ_object, 4),
        occ_fx=round(occ_fx, 4),
        contrast_score=contrast_score,
        focus_balance=focus_balance,
        readability_ok=readability_ok,
        white_clip_ratio=white_clip_ratio,
        subject_visible_ratio=subject_visible_ratio,
        subject_occluded_by_fx_ratio=subject_occluded_by_fx_ratio,
        weapon_attached_ratio=weapon_attached_ratio,
        silhouette_integrity=silhouette_integrity,
        limb_connection_score=limb_connection_score,
        frontal_block_score=frontal_block_score,
        grammar_match_score=grammar_match_score,
    )


def _layer_layout_summary() -> dict[str, dict[str, object]]:
    return {key: {'surface_size': list(spec.surface_size), 'dest_rect': list(spec.dest_rect)} for key, spec in LAYER_SPECS.items()}


def assembly_pipeline_summary() -> dict[str, object]:
    return {
        'pipeline_order': list(PIPELINE_ORDER),
        'composition_resolution': list(SCENE_COMPOSITION_SIZE),
        'output_resolution': list(SCENE_OUTPUT_SIZE),
        'layer_layout': _layer_layout_summary(),
        'readability_thresholds': {
            'safe_art_zone_ratio': SAFE_ART_ZONE_RATIO,
            'occ_subject_min': REQUIRED_OCC_SUBJECT,
            'occ_subject_max': MAX_OCC_SUBJECT,
            'occ_subject_preferred_range': list(PREFERRED_OCC_SUBJECT_RANGE),
            'occ_object_min': REQUIRED_OCC_OBJECT,
            'occ_object_max': MAX_OCC_OBJECT,
            'occ_object_preferred_range': list(PREFERRED_OCC_OBJECT_RANGE),
            'contrast_score_min': REQUIRED_CONTRAST,
            'subject_visible_ratio_min': REQUIRED_SUBJECT_VISIBLE,
            'subject_occluded_by_fx_ratio_max': REQUIRED_MAX_FX_OCCLUSION,
            'weapon_attached_ratio_min': REQUIRED_MIN_WEAPON_ATTACHED,
            'white_clip_ratio_max': REQUIRED_MAX_WHITE_CLIP,
            'silhouette_integrity_min': REQUIRED_MIN_SILHOUETTE_INTEGRITY,
            'limb_connection_score_min': REQUIRED_MIN_LIMB_CONNECTION,
            'frontal_block_score_min': REQUIRED_MIN_FRONTAL_BLOCK,
            'grammar_match_score_min': REQUIRED_MIN_GRAMMAR_MATCH,
        },
    }


def _render_scene_variant(semantic: dict, refs: list[ReferenceChoice], palette, fg_palette, rng: random.Random) -> tuple[pygame.Surface, AssemblyMetrics]:
    comp_size = SCENE_COMPOSITION_SIZE
    sectors = _build_scene_sectors(comp_size)
    composite = pygame.Surface(comp_size, pygame.SRCALPHA, 32)
    background_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    environment_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    subject_mask_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    subject_detail_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    weapon_back_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    weapon_front_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    symbol_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    fx_back_source = pygame.Surface(comp_size, pygame.SRCALPHA)
    fx_front_source = pygame.Surface(comp_size, pygame.SRCALPHA)

    _draw_background(background_source, semantic, palette, rng)
    env_ref_path = _pick_environment_reference(semantic, refs)
    _blit_environment_reference(environment_source, env_ref_path, palette)
    _draw_foreground_plane(environment_source, palette, rng)

    character = compose_character_subject(comp_size, semantic, fg_palette, rng)
    _suppress_environment_intrusions(environment_source, character['layout'], sectors)
    _suppress_bright_rectangular_intrusions(environment_source, character['layout'], sectors)
    subject_mask_source.blit(character['subject_mask'], (0, 0))
    subject_detail_source.blit(character['subject_detail'], (0, 0))
    weapon_back_source.blit(character['weapon_back_layer'], (0, 0))
    weapon_front_source.blit(character['weapon_front_layer'], (0, 0))
    subject_layout = character['layout']
    _draw_symbol_layer(symbol_source, semantic, fg_palette, subject_layout, sectors)
    draw_fx(fx_back_source, semantic, palette, rng, keepout=subject_layout['subject_core_rect'].inflate(18, 18), fx_sector=sectors['fx_back_sector'], spawn_anchor=subject_layout['halo_anchor'])
    draw_fx(fx_front_source, semantic, palette, rng, keepout=subject_layout['subject_core_rect'].inflate(72, 56), fx_sector=sectors['fx_front_sector'], spawn_anchor=subject_layout['fx_spawn_anchor'])

    subject_body_source = _merge_layers(subject_mask_source, subject_detail_source)
    object_source = _merge_layers(weapon_back_source, weapon_front_source)
    object_mask = _dilate_mask(_alpha_mask(object_source, 72), 2)
    fx_mask = _alpha_mask(_merge_layers(fx_back_source, fx_front_source), 20)
    symbol_mask = _alpha_mask(symbol_source, 20)
    subject_metric_mask = _dilate_mask(_alpha_mask(subject_body_source, 72), 16)
    object_metric_mask = _dilate_mask(object_mask, 8 if str(subject_layout.get('weapon_template_id', 'staff')) in {'staff', 'orb'} else 5)
    _clip_layer_alpha(symbol_source, 24)
    _clip_layer_alpha(fx_back_source, 28)
    _clip_layer_alpha(fx_front_source, 18)

    composite.blit(background_source, (0, 0))
    composite.blit(environment_source, (0, 0))
    composite.blit(symbol_source, (0, 0))
    composite.blit(fx_back_source, (0, 0))
    composite.blit(weapon_back_source, (0, 0))
    composite.blit(subject_mask_source, (0, 0))
    composite.blit(subject_detail_source, (0, 0))
    composite.blit(weapon_front_source, (0, 0))
    composite.blit(fx_front_source, (0, 0))

    _apply_subject_outline(composite, subject_metric_mask, (max(6, fg_palette[0][0] // 2), max(6, fg_palette[0][1] // 2), max(6, fg_palette[0][2] // 2), 255))
    _enforce_figure_ground_separation(composite, subject_metric_mask, fg_palette)
    _enforce_object_separation(composite, object_metric_mask, subject_metric_mask, fg_palette)
    _apply_contrast(composite)
    _compress_highlights(composite)
    apply_scene_finish(composite, subject_layout['rect'], fg_palette)
    _compress_highlights(composite)

    metrics = validate_readability(subject_metric_mask, object_metric_mask, fx_mask, symbol_mask, composite, subject_layout)
    return composite, metrics


def assemble_scene_art(card_id: str, prompt: str, seed: int, out_path: Path) -> AssemblyResult:
    semantic = validate_scene_semantic(semantic_from_prompt(prompt))
    semantic['safe_art_zone_ratio'] = SAFE_ART_ZONE_RATIO
    semantic.setdefault('max_subject_occ', MAX_OCC_SUBJECT)
    semantic.setdefault('max_object_occ', MAX_OCC_OBJECT)
    pose_text = str(semantic.get('subject_pose', '') or '').lower()
    if 'solar_warrior_attack' in pose_text or 'attack' in pose_text:
        semantic.setdefault('subject_anchor_mode', 'lower_center')
    elif 'guide_mage_calm' in pose_text or 'calm' in pose_text:
        semantic.setdefault('subject_anchor_mode', 'golden_ratio')
    else:
        semantic.setdefault('subject_anchor_mode', 'center')
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
    attempts: list[tuple[pygame.Surface, AssemblyMetrics]] = []
    for retry_index in range(3):
        attempt_semantic = dict(semantic)
        if retry_index == 1:
            attempt_semantic['subject_scale_boost'] = 0.06
            attempt_semantic['object_scale_boost'] = 0.05
            attempt_semantic['subject_center_shift'] = 0.0
        elif retry_index == 2:
            attempt_semantic['subject_scale_boost'] = 0.08
            attempt_semantic['object_scale_boost'] = 0.08
            attempt_semantic['subject_center_shift'] = 0.0
        fg_palette = _strong_foreground_palette(palette, attempt_semantic.get('subject_kind', ''), attempt_semantic.get('object_kind', ''))
        composed, metrics = _render_scene_variant(attempt_semantic, refs, palette, fg_palette, random.Random(seed + retry_index * 4099))
        attempts.append((composed, metrics))
        if metrics.readability_ok:
            break

    best_surface, best_metrics = max(
        attempts,
        key=lambda item: (
            1 if item[1].readability_ok else 0,
            item[1].silhouette_integrity,
            item[1].limb_connection_score,
            item[1].subject_visible_ratio,
            -item[1].subject_occluded_by_fx_ratio,
            item[1].weapon_attached_ratio,
            item[1].contrast_score,
        ),
    )
    final = pygame.transform.smoothscale(best_surface, SCENE_OUTPUT_SIZE).convert_alpha()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_surface_with_pillow(final, out_path, SCENE_OUTPUT_SIZE)
    env_preset = resolve_environment_preset(semantic.get('scene_type', ''), semantic.get('environment_kind', ''), semantic.get('environment', ''))
    return AssemblyResult(
        card_id=card_id,
        path=str(out_path),
        pipeline_order=list(PIPELINE_ORDER),
        scene_type=str(semantic.get('scene_type', '') or ''),
        environment_preset=env_preset.preset_id,
        palette_id=civ.palette_id,
        output_resolution=SCENE_OUTPUT_SIZE,
        composition_resolution=SCENE_COMPOSITION_SIZE,
        layer_layout=_layer_layout_summary(),
        references_used=[r.path.name for r in refs[:4]],
        metrics=best_metrics,
    )



