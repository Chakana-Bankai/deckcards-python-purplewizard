from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict, Field

from game.art.dna_loader import CardDnaModel
from game.core.paths import project_root


class VariationOptionModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    value: str
    archetype_compatibility: list[str] = Field(default_factory=list)
    min_scale_effect: float = 0.0
    max_scale_effect: float = 0.0


class VariationSlotModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slot_id: str
    description: str
    visual_priority: float
    options: list[VariationOptionModel]


class VariationRegistryModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: str
    status: str
    slots: dict[str, VariationSlotModel]


class ArchetypeEvolutionRuleModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    identity_lock: dict[str, object]
    allowed_slots: dict[str, list[str]]
    forbidden_slots: dict[str, list[str]] = Field(default_factory=dict)
    variation_notes: list[str] = Field(default_factory=list)


class ArchetypeEvolutionRegistryModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    version: str
    status: str
    archetypes: dict[str, ArchetypeEvolutionRuleModel]


def _variation_rules_dir() -> Path:
    return project_root() / 'data' / 'variation_rules'


@lru_cache(maxsize=1)
def load_archetype_evolution_registry() -> ArchetypeEvolutionRegistryModel:
    path = _variation_rules_dir() / 'archetype_evolution_rules.json'
    return ArchetypeEvolutionRegistryModel(**json.loads(path.read_text(encoding='utf-8')))


@lru_cache(maxsize=1)
def load_variation_registry() -> VariationRegistryModel:
    path = _variation_rules_dir() / 'variation_slots.json'
    return VariationRegistryModel(**json.loads(path.read_text(encoding='utf-8')))


def list_variation_slots() -> list[str]:
    registry = load_variation_registry()
    return list(registry.slots.keys())


def resolve_variation_slot(slot_id: str) -> VariationSlotModel:
    registry = load_variation_registry()
    return registry.slots[slot_id]


def allowed_slot_options(slot_id: str, archetype: str) -> list[VariationOptionModel]:
    slot = resolve_variation_slot(slot_id)
    wanted = str(archetype or '').upper()
    return [option for option in slot.options if wanted in option.archetype_compatibility]


def allowed_variation_slots_for_archetype(archetype: str) -> dict[str, list[VariationOptionModel]]:
    registry = load_variation_registry()
    return {
        slot_id: allowed_slot_options(slot_id, archetype)
        for slot_id in registry.slots.keys()
    }


def prioritized_slot_summary_for_dna(card_dna: CardDnaModel) -> list[dict[str, object]]:
    registry = load_variation_registry()
    summary: list[dict[str, object]] = []
    for slot_id, slot in registry.slots.items():
        allowed = allowed_slot_options(slot_id, card_dna.archetype)
        summary.append(
            {
                'slot_id': slot_id,
                'visual_priority': slot.visual_priority,
                'allowed_values': [option.value for option in allowed],
                'min_scale_effect': min((option.min_scale_effect for option in allowed), default=0.0),
                'max_scale_effect': max((option.max_scale_effect for option in allowed), default=0.0),
            }
        )
    summary.sort(key=lambda item: item['visual_priority'], reverse=True)
    return summary

def resolve_archetype_evolution_rule(archetype: str) -> ArchetypeEvolutionRuleModel:
    registry = load_archetype_evolution_registry()
    return registry.archetypes[str(archetype or '').upper()]


def allowed_evolution_values(archetype: str, slot_id: str) -> list[VariationOptionModel]:
    rule = resolve_archetype_evolution_rule(archetype)
    allowed_values = set(rule.allowed_slots.get(slot_id, []))
    base_options = allowed_slot_options(slot_id, archetype)
    return [option for option in base_options if option.value in allowed_values]


def evolution_profile_for_dna(card_dna: CardDnaModel) -> dict[str, object]:
    rule = resolve_archetype_evolution_rule(card_dna.archetype)
    prioritized = []
    for slot_id in list_variation_slots():
        allowed = allowed_evolution_values(card_dna.archetype, slot_id)
        slot = resolve_variation_slot(slot_id)
        prioritized.append({
            'slot_id': slot_id,
            'visual_priority': slot.visual_priority,
            'allowed_values': [option.value for option in allowed],
            'forbidden_values': list(rule.forbidden_slots.get(slot_id, [])),
        })
    prioritized.sort(key=lambda item: item['visual_priority'], reverse=True)
    return {
        'archetype': card_dna.archetype,
        'identity_lock': dict(rule.identity_lock),
        'variation_notes': list(rule.variation_notes),
        'slot_profile': prioritized,
    }
