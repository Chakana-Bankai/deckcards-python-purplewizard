from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict, Field

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


def _card_dna_dir() -> Path:
    return project_root() / 'data' / 'card_dna'


@lru_cache(maxsize=1)
def _load_shape_grammar() -> dict[str, object]:
    path = project_root() / 'data' / 'art_identity' / 'shape_grammar.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _load_card_prompts() -> dict[str, object]:
    path = project_root() / 'game' / 'data' / 'card_prompts.json'
    if not path.exists():
        return {'cards': {}}
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        return payload
    return {'cards': {}}


@lru_cache(maxsize=1)
def load_card_dna_index() -> CardDnaIndexModel:
    path = _card_dna_dir() / 'index.json'
    return CardDnaIndexModel(**json.loads(path.read_text(encoding='utf-8')))


@lru_cache(maxsize=256)
def _load_explicit_card_dna(card_id: str) -> CardDnaModel | None:
    path = _card_dna_dir() / f'{card_id}.json'
    if not path.exists():
        return None
    return CardDnaModel(**json.loads(path.read_text(encoding='utf-8')))


def _normalize_archetype(card_id: str, scene_spec: dict[str, object]) -> str:
    cid = str(card_id or '').upper()
    subject_kind = str(scene_spec.get('subject_kind', '') or '').lower()
    if 'ARCHON' in cid or 'archon' in subject_kind:
        return 'ARCHON'
    if 'GUIDE' in cid or any(tok in subject_kind for tok in ('guide', 'oracle', 'mage')):
        return 'GUIDE_MAGE'
    return 'SOLAR_WARRIOR'


def _shape_fields_for_archetype(archetype: str) -> tuple[str, str]:
    grammar = _load_shape_grammar().get('classes', {})
    key_map = {
        'ARCHON': 'archon',
        'SOLAR_WARRIOR': 'solar_warrior',
        'GUIDE_MAGE': 'guide_mage',
    }
    entry = grammar.get(key_map.get(archetype, 'solar_warrior'), {})
    dominant = str(entry.get('dominant_shape', 'triangle'))
    secondary_map = {
        'ARCHON': 'vertical_cathedral',
        'SOLAR_WARRIOR': 'heroic_armor',
        'GUIDE_MAGE': 'support_robe',
    }
    return dominant, secondary_map.get(archetype, 'heroic_armor')


def _normalize_weapon_type(scene_spec: dict[str, object]) -> str:
    text = ' '.join([
        str(scene_spec.get('object_kind', '') or ''),
        str(scene_spec.get('secondary_object', '') or ''),
        str(scene_spec.get('subject_pose', '') or ''),
    ]).lower()
    if 'spear' in text:
        return 'spear'
    if 'sword' in text or 'blade' in text:
        return 'sword'
    if 'orb' in text:
        return 'orb'
    return 'staff'


def _normalize_palette_family(scene_spec: dict[str, object]) -> str:
    return str(scene_spec.get('palette', '') or 'gold violet turquoise').strip().lower().replace(' ', '_')


def derive_card_dna(card_id: str) -> CardDnaModel:
    cards = _load_card_prompts().get('cards', {})
    card_entry = cards.get(card_id, {}) if isinstance(cards, dict) else {}
    scene_spec = card_entry.get('scene_spec', {}) if isinstance(card_entry, dict) else {}
    archetype = _normalize_archetype(card_id, scene_spec)
    dominant_shape, secondary_shape = _shape_fields_for_archetype(archetype)
    payload = {
        'card_id': card_id,
        'entity_type': 'HUMANOID',
        'archetype': archetype,
        'dominant_shape': dominant_shape,
        'secondary_shape': secondary_shape,
        'weapon_type': _normalize_weapon_type(scene_spec),
        'environment_type': str(scene_spec.get('scene_type', '') or 'mountain_guardian_scene'),
        'pose_type': str(scene_spec.get('subject_pose', '') or 'frontal guarding stance').strip().lower().replace(' ', '_'),
        'symbol_type': str(scene_spec.get('symbol', '') or 'chakana').strip().lower().replace(' ', '_'),
        'energy_type': str(scene_spec.get('energy', '') or 'sacred wind').strip().lower().replace(' ', '_'),
        'palette_family': _normalize_palette_family(scene_spec),
    }
    return CardDnaModel(**payload)


def load_card_dna(card_id: str) -> CardDnaModel:
    explicit = _load_explicit_card_dna(card_id)
    if explicit is not None:
        return explicit
    return derive_card_dna(card_id)


def load_all_explicit_card_dna() -> list[CardDnaModel]:
    index = load_card_dna_index()
    return [load_card_dna(card_id) for card_id in index.entries]
