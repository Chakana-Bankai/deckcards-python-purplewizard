from __future__ import annotations

from pathlib import Path
import random

import pygame

from game.art.shape_dna import load_card_shape_dna
from game.art.symbol_overlay import draw_symbol_overlay
from game.art.scene_background import render_scene_background
from game.art.palette_system import resolve_civilization_palette
from game.art.character_compositor import compose_character_subject
from game.art.identity_lock import validate_identity_lock
from game.art.system_registry import canonical_pipeline_order
from game.render.frame_renderer import apply_frame_overlay

CANVAS_SIZE = (1920, 1080)
COMPOSITION_SIZE = (480, 270)


def _semantic_from_dna(dna, prompt_hint: str = '') -> dict[str, object]:
    archetype_map = {
        'SOLAR_WARRIOR': ('warrior_foreground', 'solar warrior champion'),
        'ARCHON': ('archon_foreground', 'archon hierophant'),
        'GUIDE_MAGE': ('oracle_totem', 'guide mage sage'),
    }
    env_map = {
        'SOLAR_WARRIOR': 'hyperborea_temple_scene',
        'ARCHON': 'archon_void_scene',
        'GUIDE_MAGE': 'mountain_guardian_scene',
    }
    palette_map = {
        'SOLAR_WARRIOR': 'gold amber ivory',
        'ARCHON': 'violet neutral crimson',
        'GUIDE_MAGE': 'teal gold pearl',
    }
    subject_kind, subject = archetype_map.get(dna.archetype, ('warrior_foreground', 'ritual subject'))
    return {
        'subject_kind': subject_kind,
        'subject': subject,
        'object_kind': dna.weapon_type,
        'object': dna.weapon_type,
        'secondary_object': dna.weapon_type,
        'scene_type': env_map.get(dna.archetype, dna.environment_type),
        'environment_kind': dna.environment_type,
        'environment': dna.environment_type.replace('_', ' '),
        'subject_pose': dna.pose_type,
        'symbol': dna.symbol_type,
        'energy': dna.energy_type,
        'palette': palette_map.get(dna.archetype, dna.palette_family.replace('_', ' ')),
        'safe_art_zone_ratio': 0.70,
        'subject_anchor_mode': 'center',
        'prompt_hint': prompt_hint,
        'use_symbolic_only': True,
    }


def render_card_from_dna(card_id: str, out_path: Path, *, prompt_hint: str = '', rarity: str = 'common', apply_frame: bool = False) -> dict[str, object]:
    seed = abs(hash(card_id)) % 100000
    rng = random.Random(seed)
    dna = load_card_shape_dna(card_id)
    semantic = _semantic_from_dna(dna, prompt_hint)
    palette_spec = resolve_civilization_palette(semantic)
    palette = (palette_spec.primary, palette_spec.secondary, palette_spec.shadow, palette_spec.glow)

    bg_layers = render_scene_background(COMPOSITION_SIZE, semantic, palette, seed=seed)
    subject = compose_character_subject(COMPOSITION_SIZE, semantic, palette, rng)

    comp = pygame.Surface(COMPOSITION_SIZE, pygame.SRCALPHA)
    comp.blit(bg_layers['background_far'], (0, 0))
    comp.blit(bg_layers['background_mid'], (0, 0))
    comp.blit(subject['ambient_noise'], (0, 0))
    comp.blit(subject['light_beams'], (0, 0))
    comp.blit(subject['halo_glow'], (0, 0))
    comp.blit(subject['halo_noise'], (0, 0))
    comp.blit(subject['energy_particles'], (0, 0))
    comp.blit(subject['halo_core'], (0, 0))
    comp.blit(bg_layers['background_near'], (0, 0))
    comp.blit(subject['weapon_back_layer'], (0, 0))
    comp.blit(subject['subject_mask'], (0, 0))
    comp.blit(subject['subject_detail'], (0, 0))

    symbol_layer = pygame.Surface(COMPOSITION_SIZE, pygame.SRCALPHA)
    draw_symbol_overlay(symbol_layer, dna.symbol_type, subject['layout']['symbol_center_anchor'], subject['layout']['rect'], palette)
    comp.blit(symbol_layer, (0, 0))
    comp.blit(subject['weapon_front_layer'], (0, 0))

    full = pygame.transform.smoothscale(comp, CANVAS_SIZE).convert_alpha()
    if apply_frame:
        frame_rect = pygame.Rect(36, 36, CANVAS_SIZE[0] - 72, CANVAS_SIZE[1] - 72)
        apply_frame_overlay(full, frame_rect, rarity, accent=palette[3], set_is_hiperboria=card_id.startswith('HYP-'))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(full, out_path)

    object_rect = subject['weapon_back_layer'].get_bounding_rect(min_alpha=12).union(subject['weapon_front_layer'].get_bounding_rect(min_alpha=12))
    identity = validate_identity_lock(subject['layout']['rect'], object_rect, COMPOSITION_SIZE, subject['layout']['silhouette_integrity'])
    return {
        'card_id': card_id,
        'pipeline': canonical_pipeline_order(),
        'dna': dna.model_dump(),
        'identity_lock': identity,
        'path': str(out_path),
        'framed': bool(apply_frame),
    }
