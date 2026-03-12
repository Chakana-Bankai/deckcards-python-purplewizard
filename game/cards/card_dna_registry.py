from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from game.core.paths import project_root


class CardLoreModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    lore_text: str
    tags: list[str] = Field(default_factory=list)
    author: str = 'Chakana Studio'
    source_order: str = ''


class CardGameplayModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    gameplay_role: str
    deck_archetype: str = ''
    source_archetype: str = ''
    action_types: list[str] = Field(default_factory=list)
    cost: int = 0
    target: str = 'enemy'
    direction: str = 'ESTE'
    effects: list[dict] = Field(default_factory=list)
    taxonomy: str = 'engine'
    family: str = 'neutral'
    legacy_role: str = ''


class CardVisualModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    entity_type: str = 'HUMANOID'
    archetype: str
    dominant_shape: str
    secondary_shape: str
    weapon_type: str
    environment_type: str
    pose_type: str
    symbol_type: str
    energy_type: str
    palette_family: str
    artwork: str = ''
    sprite_path: str = ''
    source_archetype: str = ''


class CardDnaEntryModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    canonical_id: str
    legacy_id: str = ''
    set: str = ''
    rarity: str = 'common'
    lore: CardLoreModel
    gameplay: CardGameplayModel
    visual: CardVisualModel


class CardDnaCatalogModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: str
    count: int
    archetype_counts: dict[str, int] = Field(default_factory=dict)
    deck_archetype_counts: dict[str, int] = Field(default_factory=dict)
    gameplay_role_counts: dict[str, int] = Field(default_factory=dict)
    action_type_counts: dict[str, int] = Field(default_factory=dict)
    cards: dict[str, CardDnaEntryModel] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def _catalog_path() -> Path:
    return project_root() / 'data' / 'card_dna' / 'card_dna_catalog.json'


@lru_cache(maxsize=1)
def load_card_dna_catalog() -> CardDnaCatalogModel:
    path = _catalog_path()
    return CardDnaCatalogModel(**json.loads(path.read_text(encoding='utf-8')))


@lru_cache(maxsize=512)
def load_card_dna_entry(card_id: str) -> CardDnaEntryModel:
    return load_card_dna_catalog().cards[card_id]


@lru_cache(maxsize=512)
def load_card_visual_dna(card_id: str) -> CardVisualModel:
    return load_card_dna_entry(card_id).visual


def load_card_visual_dna_dict(card_id: str) -> dict[str, object]:
    return load_card_visual_dna(card_id).model_dump()


def load_combat_card_payloads() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for entry in load_card_dna_catalog().cards.values():
        payloads.append(
            {
                'id': entry.id,
                'canonical_id': entry.canonical_id,
                'legacy_id': entry.legacy_id,
                'name_key': entry.lore.name,
                'text_key': entry.lore.lore_text,
                'rarity': entry.rarity,
                'cost': entry.gameplay.cost,
                'target': entry.gameplay.target,
                'tags': list(entry.lore.tags),
                'effects': list(entry.gameplay.effects),
                'role': entry.gameplay.gameplay_role,
                'family': entry.gameplay.family,
                'direction': entry.gameplay.direction,
                'metadata': {
                    'card_dna': entry.model_dump(),
                    'visual': entry.visual.model_dump(),
                    'lore': entry.lore.model_dump(),
                    'gameplay': entry.gameplay.model_dump(),
                },
            }
        )
    return payloads
