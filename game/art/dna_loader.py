from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from game.cards.card_canon_registry import load_canon_card
from game.cards.card_dna_registry import load_card_visual_dna
from game.core.paths import project_root


class CardDnaModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    card_id: str
    entity_type: str = Field(default='HUMANOID')
    archetype: str
    dominant_shape: str
    secondary_shape: str
    weapon_type: str
    environment_type: str
    pose_type: str
    symbol_type: str
    energy_type: str
    palette_family: str


class CardDnaIndexModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: str
    status: str
    entry_count: int
    entries: list[str]
    required_fields: list[str]
    derivation_policy: str
    catalog_file: str | None = None


def _card_dna_dir() -> Path:
    return project_root() / 'data' / 'card_dna'


@lru_cache(maxsize=1)
def load_card_dna_index() -> CardDnaIndexModel:
    path = _card_dna_dir() / 'index.json'
    return CardDnaIndexModel(**json.loads(path.read_text(encoding='utf-8')))


def _canon_visual_fallback(card_id: str) -> CardDnaModel:
    card = load_canon_card(card_id)
    faction = str(card.faction or '').lower()
    visual_language = dict(card.art.visual_language or {})
    weapon_bias = str(visual_language.get('weapon_bias', '') or '').lower()
    tags = {str(tag or '').lower() for tag in list(card.tags or [])}
    card_type = str(card.type or '').lower()
    role = str(card.ai_role or '').lower()

    archetype_map = {
        'cosmic_warrior': 'SOLAR_WARRIOR',
        'harmony_guardian': 'GUIDE_MAGE',
        'oracle_of_fate': 'GUIDE_MAGE',
        'archon': 'ARCHON',
    }
    dominant_shape = str(visual_language.get('shape', '') or '').lower() or {
        'cosmic_warrior': 'triangle',
        'harmony_guardian': 'diamond',
        'oracle_of_fate': 'rectangle',
        'archon': 'circle',
    }.get(faction, 'triangle')
    secondary_shape = {
        'triangle': 'diamond',
        'diamond': 'rectangle',
        'rectangle': 'circle',
        'circle': 'triangle',
    }.get(dominant_shape, 'rectangle')

    if 'spear' in weapon_bias or 'blade' in weapon_bias:
        weapon_type = 'spear'
    elif 'shield' in weapon_bias and 'staff' in weapon_bias:
        weapon_type = 'staff'
    elif 'staff' in weapon_bias:
        weapon_type = 'staff'
    elif 'claw' in weapon_bias:
        weapon_type = 'sword'
    else:
        weapon_type = 'staff' if faction in {'harmony_guardian', 'oracle_of_fate', 'archon'} else 'spear'

    if faction == 'archon':
        environment_type = 'archon_void_scene'
    elif faction == 'cosmic_warrior':
        environment_type = 'hyperborea_temple_scene'
    elif faction == 'harmony_guardian':
        environment_type = 'mountain_guardian_scene'
    else:
        environment_type = 'sacred_plateau_scene'

    if faction == 'archon':
        pose_type = 'ritual_uplift' if card_type in {'ritual', 'curse'} or role in {'summoner', 'controller'} else 'predatory_lunge'
    elif faction == 'cosmic_warrior':
        pose_type = 'attack_diagonal' if card_type == 'attack' else 'heroic_raised_weapon'
    elif faction == 'harmony_guardian':
        pose_type = 'support_vertical' if role in {'support', 'tank'} else 'frontal_iconic_pose'
    else:
        pose_type = 'support_vertical' if role in {'support', 'controller', 'summoner'} else 'frontal_iconic_pose'

    if faction == 'archon':
        symbol_type = 'void_seal'
        energy_type = 'void_sparks'
    elif faction == 'cosmic_warrior':
        symbol_type = 'solar_disc'
        energy_type = 'solar_flare'
    elif faction == 'harmony_guardian':
        symbol_type = 'chakana_gate'
        energy_type = 'stable_rings'
    else:
        symbol_type = 'oracle_eye'
        energy_type = 'wisdom_glyphs'

    if 'ritual' in tags:
        energy_type = 'ritual_spiral' if faction == 'archon' else energy_type
    if 'summon' in tags and faction != 'archon':
        energy_type = 'wisdom_glyphs'
    if 'block' in tags and faction == 'harmony_guardian':
        energy_type = 'stable_rings'

    palette_family = str(card.art.palette or '').replace('-', '_') or {
        'cosmic_warrior': 'gold_amber_ivory',
        'harmony_guardian': 'jade_teal_stone',
        'oracle_of_fate': 'violet_teal_pearl',
        'archon': 'obsidian_crimson_violet',
    }.get(faction, 'gold_amber_ivory')

    return CardDnaModel(
        card_id=card_id,
        entity_type='HUMANOID',
        archetype=archetype_map.get(faction, 'SOLAR_WARRIOR'),
        dominant_shape=dominant_shape,
        secondary_shape=secondary_shape,
        weapon_type=weapon_type,
        environment_type=environment_type,
        pose_type=pose_type,
        symbol_type=symbol_type,
        energy_type=energy_type,
        palette_family=palette_family,
    )


@lru_cache(maxsize=512)
def load_card_dna(card_id: str) -> CardDnaModel:
    try:
        visual = load_card_visual_dna(card_id)
        return CardDnaModel(
            card_id=card_id,
            entity_type=visual.entity_type,
            archetype=visual.archetype.upper(),
            dominant_shape=visual.dominant_shape,
            secondary_shape=visual.secondary_shape,
            weapon_type=visual.weapon_type,
            environment_type=visual.environment_type,
            pose_type=visual.pose_type,
            symbol_type=visual.symbol_type,
            energy_type=visual.energy_type,
            palette_family=visual.palette_family,
        )
    except Exception:
        return _canon_visual_fallback(card_id)


def load_all_explicit_card_dna() -> list[CardDnaModel]:
    index = load_card_dna_index()
    return [load_card_dna(card_id) for card_id in index.entries]
