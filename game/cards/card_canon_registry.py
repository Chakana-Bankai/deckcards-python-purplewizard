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


class CanonKpiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    expected_pick_rate: float = 0.0
    expected_play_rate: float = 0.0
    target_win_rate_delta: float = 0.0
    dead_card_risk: str = 'medium'


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
    kpi: CanonKpiModel = Field(default_factory=CanonKpiModel)


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
    path = _canon_path()
    if path.exists():
        return CanonCatalogModel(**json.loads(path.read_text(encoding='utf-8')))
    return _build_runtime_catalog()


def _load_runtime_cards() -> list[dict]:
    root = project_root() / 'game' / 'data'
    out: list[dict] = []
    for path in (root / 'cards.json', root / 'cards_hiperboria.json', root / 'cards_arconte.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        rows = payload.get('cards', []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
        for row in rows:
            if isinstance(row, dict) and row.get('id'):
                out.append(dict(row))
    return out


def _build_runtime_catalog() -> CanonCatalogModel:
    rows = _load_runtime_cards()
    cards: list[CanonCardModel] = []
    faction_counts: dict[str, int] = {}
    rarity_counts: dict[str, int] = {}
    ai_role_counts: dict[str, int] = {}

    for row in rows:
        faction = str(row.get('archetype', row.get('set', 'runtime')) or 'runtime')
        rarity = str(row.get('rarity', 'common') or 'common')
        role = str(row.get('role', 'controller') or 'controller')
        faction_counts[faction] = faction_counts.get(faction, 0) + 1
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        ai_role_counts[role] = ai_role_counts.get(role, 0) + 1
        cards.append(
            CanonCardModel(
                id=str(row.get('id')),
                name=str(row.get('name', row.get('name_key', row.get('id', 'card')))),
                faction=faction,
                tier=str(row.get('set', 'runtime') or 'runtime'),
                rarity=rarity,
                type=str(row.get('role', 'control') or 'control'),
                cost=int(row.get('cost', 0) or 0),
                tags=[str(tag) for tag in list(row.get('tags', []) or [])],
                effects=[dict(effect) for effect in list(row.get('effects', []) or []) if isinstance(effect, dict)],
                ai_role=role,
                art=CanonArtModel(
                    artwork_id=str(row.get('artwork', row.get('id', 'card'))),
                    palette=str(row.get('palette', '') or ''),
                    energy=str(row.get('energy', '') or ''),
                    symbol=str(row.get('symbol', '') or ''),
                    motif=str(row.get('motif', '') or ''),
                ),
                lore=CanonLoreModel(
                    text=str(row.get('lore_text', '') or ''),
                    author=str(row.get('author', 'Chakana Studio') or 'Chakana Studio'),
                    identity=faction,
                ),
                codex_entry=CanonCodexEntryModel(
                    summary=str(row.get('effect_text', row.get('text_key', '')) or ''),
                    effect_text=str(row.get('effect_text', row.get('text_key', '')) or ''),
                    lore=str(row.get('lore_text', '') or ''),
                    tags=[str(tag) for tag in list(row.get('tags', []) or [])],
                    faction=faction,
                    role=role,
                ),
            )
        )

    return CanonCatalogModel(
        version='runtime_catalog_v1',
        count=len(cards),
        faction_counts=faction_counts,
        rarity_counts=rarity_counts,
        ai_role_counts=ai_role_counts,
        cards=cards,
    )


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


def load_canon_combat_payloads() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for card in load_card_canon_catalog().cards:
        payloads.append(
            {
                'id': card.id,
                'name_key': card.name,
                'text_key': card.codex_entry.effect_text or card.codex_entry.summary,
                'rarity': card.rarity,
                'cost': int(card.cost),
                'target': 'enemy' if card.type in {'attack', 'curse'} else 'self',
                'tags': list(card.tags),
                'effects': [dict(effect) for effect in list(card.effects)],
                'role': card.ai_role,
                'family': card.type,
                'direction': 'ESTE',
                'metadata': {
                    'canon': True,
                    'card': card.model_dump(),
                    'art': card.art.model_dump(),
                    'lore': card.lore.model_dump(),
                    'codex_entry': card.codex_entry.model_dump(),
                    'kpi': card.kpi.model_dump(),
                },
            }
        )
    return payloads
