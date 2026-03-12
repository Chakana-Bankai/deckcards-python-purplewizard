from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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


@lru_cache(maxsize=256)
def load_card_dna(card_id: str) -> CardDnaModel:
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


def load_all_explicit_card_dna() -> list[CardDnaModel]:
    index = load_card_dna_index()
    return [load_card_dna(card_id) for card_id in index.entries]
