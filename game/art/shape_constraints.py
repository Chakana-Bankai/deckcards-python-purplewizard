from __future__ import annotations

from functools import lru_cache
import json

from pydantic import BaseModel, ConfigDict, Field

from game.art.character_templates import CHARACTER_TEMPLATES
from game.art.dna_loader import CardDnaModel
from game.art.variation_registry import (
    allowed_evolution_values,
    list_variation_slots,
    resolve_archetype_evolution_rule,
    resolve_variation_slot,
)
from game.core.paths import project_root

HALO_SIZE_MAX_RATIO = 0.75
SYMBOL_COVERAGE_MAX_RATIO = 0.15
MIN_SUBJECT_WIDTH_RATIO = 0.24
MIN_SUBJECT_HEIGHT_RATIO = 0.32
MIN_WEAPON_LENGTH_RATIO = 0.22
MIN_SILHOUETTE_INTEGRITY = 0.75

ARCHETYPE_TEMPLATE_MAP = {
    'ARCHON': 'archon_base',
    'SOLAR_WARRIOR': 'solar_warrior_base',
    'GUIDE_MAGE': 'guide_mage_base',
}


class ShapeConstraintSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    card_id: str
    archetype: str
    dominant_shape: str
    pose_type: str
    weapon_type: str
    symbol_type: str
    subject_width_ratio: float
    subject_height_ratio: float
    weapon_length_ratio: float
    symbol_coverage_ratio: float = 0.0
    halo_size_ratio: float = 0.0
    silhouette_integrity: float = 1.0
    variation_slots: dict[str, str] = Field(default_factory=dict)


class ShapeConstraintResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    accepted: bool
    rejected_slots: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    fallback_options: dict[str, list[str]] = Field(default_factory=dict)
    normalized_spec: dict[str, object] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def _load_shape_grammar() -> dict[str, object]:
    path = project_root() / 'data' / 'art_identity' / 'shape_grammar.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


@lru_cache(maxsize=1)
def _load_scene_rules() -> dict[str, object]:
    path = project_root() / 'data' / 'art_identity' / 'scene_rules.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _template_defaults(archetype: str) -> dict[str, object]:
    key = ARCHETYPE_TEMPLATE_MAP.get(str(archetype or '').upper(), 'solar_warrior_base')
    return dict(CHARACTER_TEMPLATES[key])


def _shape_rule(archetype: str) -> dict[str, object]:
    classes = _load_shape_grammar().get('classes', {})
    key_map = {
        'ARCHON': 'archon',
        'SOLAR_WARRIOR': 'solar_warrior',
        'GUIDE_MAGE': 'guide_mage',
    }
    return dict(classes.get(key_map.get(str(archetype or '').upper(), 'solar_warrior'), {}))


def _scene_limits() -> dict[str, float]:
    rules = _load_scene_rules()
    occ = rules.get('occupancy_rules', {})
    symbolic = rules.get('scene_structure', {}).get('symbolic_layer', {})
    return {
        'subject_min': float(occ.get('subject_min', 0.22)),
        'subject_max': float(occ.get('subject_max', 0.40)),
        'object_min': float(occ.get('object_min', 0.06)),
        'object_max': float(occ.get('object_max', 0.25)),
        'symbol_overlap_max': float(symbolic.get('subject_overlap_max', SYMBOL_COVERAGE_MAX_RATIO)),
    }


def build_constraint_spec(card_dna: CardDnaModel, variation_slots: dict[str, str] | None = None, overrides: dict[str, object] | None = None) -> ShapeConstraintSpec:
    variation_slots = dict(variation_slots or {})
    overrides = dict(overrides or {})
    template = _template_defaults(card_dna.archetype)
    shape_rule = _shape_rule(card_dna.archetype)
    spec_payload = {
        'card_id': card_dna.card_id,
        'archetype': card_dna.archetype,
        'dominant_shape': card_dna.dominant_shape,
        'pose_type': card_dna.pose_type,
        'weapon_type': card_dna.weapon_type,
        'symbol_type': card_dna.symbol_type,
        'subject_width_ratio': float(template.get('width_ratio', 0.32)),
        'subject_height_ratio': float(template.get('height_ratio', 0.42)),
        'weapon_length_ratio': float(shape_rule.get('weapon_length_max_ratio', 0.60)) * 0.92,
        'symbol_coverage_ratio': 0.10,
        'halo_size_ratio': 0.45,
        'silhouette_integrity': 0.82,
        'variation_slots': variation_slots,
    }
    spec_payload.update(overrides)
    return ShapeConstraintSpec(**spec_payload)


def _slot_value_allowed(archetype: str, slot_id: str, value: str) -> bool:
    allowed = allowed_evolution_values(archetype, slot_id)
    return any(option.value == value for option in allowed)


def _fallback_options(archetype: str, rejected_slots: list[str]) -> dict[str, list[str]]:
    fallbacks: dict[str, list[str]] = {}
    for slot_id in rejected_slots:
        fallbacks[slot_id] = [option.value for option in allowed_evolution_values(archetype, slot_id)]
    return fallbacks


def validate_shape_constraints(spec: ShapeConstraintSpec) -> ShapeConstraintResult:
    reasons: list[str] = []
    rejected_slots: list[str] = []

    shape_rule = _shape_rule(spec.archetype)
    scene_limits = _scene_limits()
    identity_rule = resolve_archetype_evolution_rule(spec.archetype)

    expected_shape = str(shape_rule.get('dominant_shape', spec.dominant_shape))
    if spec.dominant_shape != expected_shape:
        reasons.append(f'dominant_shape_mismatch:{spec.dominant_shape}->{expected_shape}')

    max_width = float(shape_rule.get('subject_width_max_ratio', 0.35))
    max_height = float(shape_rule.get('subject_height_max_ratio', 0.45))
    if not (MIN_SUBJECT_WIDTH_RATIO <= spec.subject_width_ratio <= max_width):
        reasons.append(f'subject_width_ratio_out_of_range:{spec.subject_width_ratio}')
    if not (MIN_SUBJECT_HEIGHT_RATIO <= spec.subject_height_ratio <= max_height):
        reasons.append(f'subject_height_ratio_out_of_range:{spec.subject_height_ratio}')

    max_weapon = float(shape_rule.get('weapon_length_max_ratio', 0.60))
    if not (MIN_WEAPON_LENGTH_RATIO <= spec.weapon_length_ratio <= max_weapon):
        reasons.append(f'weapon_length_ratio_out_of_range:{spec.weapon_length_ratio}')

    if spec.symbol_coverage_ratio > scene_limits['symbol_overlap_max']:
        reasons.append(f'symbol_coverage_exceeded:{spec.symbol_coverage_ratio}')
    if spec.halo_size_ratio > HALO_SIZE_MAX_RATIO:
        reasons.append(f'halo_size_exceeded:{spec.halo_size_ratio}')
    if spec.silhouette_integrity < MIN_SILHOUETTE_INTEGRITY:
        reasons.append(f'silhouette_integrity_below_min:{spec.silhouette_integrity}')

    expected_pose_bias = str(identity_rule.identity_lock.get('pose_bias', '') or '')
    if expected_pose_bias and expected_pose_bias not in spec.pose_type:
        reasons.append(f'pose_bias_mismatch:{spec.pose_type}->{expected_pose_bias}')

    for slot_id, value in spec.variation_slots.items():
        if slot_id not in list_variation_slots():
            rejected_slots.append(slot_id)
            reasons.append(f'unknown_slot:{slot_id}')
            continue
        if not _slot_value_allowed(spec.archetype, slot_id, value):
            rejected_slots.append(slot_id)
            reasons.append(f'slot_value_not_allowed:{slot_id}={value}')
            continue
        forbidden = set(identity_rule.forbidden_slots.get(slot_id, []))
        if value in forbidden:
            rejected_slots.append(slot_id)
            reasons.append(f'slot_value_forbidden:{slot_id}={value}')

    accepted = len(reasons) == 0
    return ShapeConstraintResult(
        accepted=accepted,
        rejected_slots=sorted(set(rejected_slots)),
        reasons=reasons,
        fallback_options=_fallback_options(spec.archetype, sorted(set(rejected_slots))),
        normalized_spec=spec.model_dump(),
    )


def validate_variation_payload(card_dna: CardDnaModel, variation_slots: dict[str, str], overrides: dict[str, object] | None = None) -> ShapeConstraintResult:
    spec = build_constraint_spec(card_dna, variation_slots=variation_slots, overrides=overrides)
    return validate_shape_constraints(spec)
