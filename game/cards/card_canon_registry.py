from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from game.core.paths import project_root


class CanonArtModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    artwork_id: str = ''
    visual_language: dict[str, object] = Field(default_factory=dict)
    palette: str = ''
    energy: str = ''
    symbol: str = ''
    motif: str = ''


class CanonLoreModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = ''
    author: str = 'Chakana Studio'
    identity: str = ''


class CanonCodexEntryModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = ''
    effect_text: str = ''
    lore: str = ''
    tags: list[str] = Field(default_factory=list)
    faction: str = ''
    role: str = ''
    art_metadata: dict[str, object] = Field(default_factory=dict)


class CanonCardModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    faction: str
    tier: str
    rarity: str
    type: str
    cost: int = 0
    tags: list[str] = Field(default_factory=list)
    effects: list[dict[str, object]] = Field(default_factory=list)
    ai_role: str = 'controller'
    art: CanonArtModel = Field(default_factory=CanonArtModel)
    lore: CanonLoreModel = Field(default_factory=CanonLoreModel)
    codex_entry: CanonCodexEntryModel = Field(default_factory=CanonCodexEntryModel)


class CanonCatalogModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: str
    count: int
    faction_counts: dict[str, int] = Field(default_factory=dict)
    rarity_counts: dict[str, int] = Field(default_factory=dict)
    ai_role_counts: dict[str, int] = Field(default_factory=dict)
    cards: list[CanonCardModel] = Field(default_factory=list)


@lru_cache(maxsize=1)
def _canon_path() -> Path:
    return project_root() / 'data' / 'cards' / 'card_canon_300.json'


@lru_cache(maxsize=1)
def _enemy_progression_path() -> Path:
    return project_root() / 'data' / 'cards' / 'enemy_deck_progression.json'


@lru_cache(maxsize=1)
def load_card_canon_catalog() -> CanonCatalogModel:
    return CanonCatalogModel(**json.loads(_canon_path().read_text(encoding='utf-8')))


@lru_cache(maxsize=1)
def load_card_canon_index() -> dict[str, CanonCardModel]:
    return {card.id: card for card in load_card_canon_catalog().cards}


@lru_cache(maxsize=512)
def load_canon_card(card_id: str) -> CanonCardModel:
    return load_card_canon_index()[card_id]


@lru_cache(maxsize=1)
def load_enemy_deck_progression() -> dict[str, dict[str, list[str]]]:
    return json.loads(_enemy_progression_path().read_text(encoding='utf-8'))


def load_canon_codex_payloads() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for card in load_card_canon_catalog().cards:
        payloads.append(
            {
                'id': card.id,
                'name_key': card.name,
                'text_key': card.codex_entry.effect_text,
                'role': card.ai_role,
                'rarity': card.rarity,
                'cost': int(card.cost),
                'tags': list(card.tags),
                'effects': [dict(effect) for effect in list(card.effects)],
                'archetype': card.faction,
                'lore_text': card.lore.text,
                'artwork': card.art.artwork_id,
                'set': card.faction,
                'tier': card.tier,
                'codex_summary': card.codex_entry.summary,
                'codex_entry': card.codex_entry.model_dump(),
                'art': card.art.model_dump(),
            }
        )
    return payloads
