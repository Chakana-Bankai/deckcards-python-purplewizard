from __future__ import annotations

from random import Random

from pydantic import BaseModel, ConfigDict, Field

from game.art.dna_loader import CardDnaModel, load_card_dna
from game.art.shape_constraints import validate_variation_payload
from game.art.variation_registry import evolution_profile_for_dna

MAX_STABILIZATION_PASSES = 2

VARIATION_OVERRIDE_PRESETS = {
    'helmet_variant': {
        'solar_crest': {'silhouette_integrity': 0.02, 'subject_height_ratio': 0.01},
        'archon_crown': {'silhouette_integrity': 0.01, 'subject_height_ratio': 0.01},
        'hooded_cowl': {'silhouette_integrity': 0.01},
        'none': {},
    },
    'shoulder_variant': {
        'broad_plate': {'subject_width_ratio': 0.02, 'silhouette_integrity': 0.02},
        'ritual_spike': {'subject_width_ratio': 0.01, 'silhouette_integrity': 0.01},
        'soft_wrap': {'subject_width_ratio': -0.01, 'silhouette_integrity': 0.01},
    },
    'cape_variant': {
        'short_battle_cape': {'subject_height_ratio': 0.01},
        'split_ritual_robe': {'subject_height_ratio': 0.02},
        'wide_support_robe': {'subject_width_ratio': 0.01, 'subject_height_ratio': 0.01},
    },
    'weapon_variant': {
        'sun_spear': {'weapon_type': 'spear', 'weapon_length_ratio': 0.58},
        'ceremonial_blade': {'weapon_type': 'sword', 'weapon_length_ratio': 0.48},
        'ritual_staff_head': {'weapon_type': 'staff', 'weapon_length_ratio': 0.56},
        'orb_staff': {'weapon_type': 'orb', 'weapon_length_ratio': 0.36},
        'book_focus': {'weapon_type': 'orb', 'weapon_length_ratio': 0.26},
    },
    'symbol_variant': {
        'solar_disc': {'symbol_type': 'solar_disc', 'symbol_coverage_ratio': 0.11},
        'corrupt_seal': {'symbol_type': 'corrupt_seal', 'symbol_coverage_ratio': 0.11},
        'chakana_gate': {'symbol_type': 'chakana_gate', 'symbol_coverage_ratio': 0.12},
    },
    'stance_variant': {
        'heroic_lunge': {'pose_type': 'attack_diagonal', 'silhouette_integrity': 0.02},
        'ritual_uplift': {'pose_type': 'ritual_vertical', 'silhouette_integrity': 0.01},
        'calm_offset_support': {'pose_type': 'support_vertical', 'silhouette_integrity': 0.01},
    },
    'aura_variant': {
        'solar_flare': {'halo_size_ratio': 0.48},
        'corruption_smoke': {'halo_size_ratio': 0.52},
        'wisdom_glyphs': {'halo_size_ratio': 0.46},
    },
    'environment_detail_variant': {
        'sun_banner': {},
        'void_monolith': {},
        'temple_lanterns': {},
    },
}


class DnaEvolutionResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    card_id: str
    seed: int
    base_dna: dict[str, object]
    chosen_variation_slots: dict[str, str]
    rejected_invalid_variations: list[dict[str, object]] = Field(default_factory=list)
    final_overrides: dict[str, object] = Field(default_factory=dict)
    accepted: bool
    stabilization_passes: int = 0
    final_constraint_result: dict[str, object] = Field(default_factory=dict)



def _merge_overrides(chosen_slots: dict[str, str]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for slot_id, value in chosen_slots.items():
        slot_overrides = VARIATION_OVERRIDE_PRESETS.get(slot_id, {}).get(value, {})
        for key, override_value in slot_overrides.items():
            if isinstance(override_value, (int, float)) and isinstance(merged.get(key), (int, float)):
                merged[key] = merged[key] + override_value
            else:
                merged[key] = override_value
    return merged



def _clamp_override_ranges(overrides: dict[str, object]) -> dict[str, object]:
    clamped = dict(overrides)
    if 'subject_width_ratio' in clamped:
        clamped['subject_width_ratio'] = max(0.24, min(0.35, float(clamped['subject_width_ratio'])))
    if 'subject_height_ratio' in clamped:
        clamped['subject_height_ratio'] = max(0.32, min(0.45, float(clamped['subject_height_ratio'])))
    if 'weapon_length_ratio' in clamped:
        clamped['weapon_length_ratio'] = max(0.22, min(0.60, float(clamped['weapon_length_ratio'])))
    if 'symbol_coverage_ratio' in clamped:
        clamped['symbol_coverage_ratio'] = max(0.04, min(0.15, float(clamped['symbol_coverage_ratio'])))
    if 'halo_size_ratio' in clamped:
        clamped['halo_size_ratio'] = max(0.18, min(0.75, float(clamped['halo_size_ratio'])))
    if 'silhouette_integrity' in clamped:
        clamped['silhouette_integrity'] = max(0.75, min(0.98, float(clamped['silhouette_integrity'])))
    return clamped



def _pick_slot_value(rng: Random, allowed_values: list[str]) -> str | None:
    if not allowed_values:
        return None
    if len(allowed_values) == 1:
        return allowed_values[0]
    return allowed_values[rng.randrange(len(allowed_values))]



def evolve_card_dna(card_id: str, seed: int) -> DnaEvolutionResult:
    base_dna = load_card_dna(card_id)
    return evolve_from_base_dna(base_dna, seed)



def evolve_from_base_dna(base_dna: CardDnaModel, seed: int) -> DnaEvolutionResult:
    rng = Random(seed)
    profile = evolution_profile_for_dna(base_dna)
    slot_profile = profile['slot_profile']
    rejected_invalid_variations: list[dict[str, object]] = []
    chosen_slots: dict[str, str] = {}
    final_overrides: dict[str, object] = {}
    final_result = None

    for pass_index in range(MAX_STABILIZATION_PASSES + 1):
        chosen_slots = {}
        for slot in slot_profile:
            allowed_values = list(slot.get('allowed_values', []))
            if not allowed_values:
                continue
            if pass_index == 0:
                picked = _pick_slot_value(rng, allowed_values)
            else:
                picked = allowed_values[0]
            if picked:
                chosen_slots[slot['slot_id']] = picked

        final_overrides = _clamp_override_ranges(_merge_overrides(chosen_slots))
        final_result = validate_variation_payload(base_dna, chosen_slots, final_overrides)
        if final_result.accepted:
            return DnaEvolutionResult(
                card_id=base_dna.card_id,
                seed=seed,
                base_dna=base_dna.model_dump(),
                chosen_variation_slots=chosen_slots,
                rejected_invalid_variations=rejected_invalid_variations,
                final_overrides=final_overrides,
                accepted=True,
                stabilization_passes=pass_index,
                final_constraint_result=final_result.model_dump(),
            )

        rejected_invalid_variations.append(
            {
                'pass_index': pass_index,
                'chosen_variation_slots': dict(chosen_slots),
                'reasons': list(final_result.reasons),
                'fallback_options': dict(final_result.fallback_options),
            }
        )

        # Stabilization: replace rejected slots with first valid fallback, then retry once more.
        for slot_id, fallback_values in final_result.fallback_options.items():
            if fallback_values:
                chosen_slots[slot_id] = fallback_values[0]
        final_overrides = _clamp_override_ranges(_merge_overrides(chosen_slots))
        final_result = validate_variation_payload(base_dna, chosen_slots, final_overrides)
        if final_result.accepted:
            return DnaEvolutionResult(
                card_id=base_dna.card_id,
                seed=seed,
                base_dna=base_dna.model_dump(),
                chosen_variation_slots=chosen_slots,
                rejected_invalid_variations=rejected_invalid_variations,
                final_overrides=final_overrides,
                accepted=True,
                stabilization_passes=pass_index + 1,
                final_constraint_result=final_result.model_dump(),
            )

        rejected_invalid_variations.append(
            {
                'pass_index': pass_index,
                'chosen_variation_slots': dict(chosen_slots),
                'reasons': list(final_result.reasons),
                'fallback_options': dict(final_result.fallback_options),
                'mode': 'stabilized_retry_failed',
            }
        )

    return DnaEvolutionResult(
        card_id=base_dna.card_id,
        seed=seed,
        base_dna=base_dna.model_dump(),
        chosen_variation_slots=chosen_slots,
        rejected_invalid_variations=rejected_invalid_variations,
        final_overrides=final_overrides,
        accepted=False,
        stabilization_passes=MAX_STABILIZATION_PASSES,
        final_constraint_result=final_result.model_dump() if final_result is not None else {},
    )
