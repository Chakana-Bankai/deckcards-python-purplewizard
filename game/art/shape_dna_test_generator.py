from __future__ import annotations

import os
from pathlib import Path

import pygame

from game.art.assembly_pipeline import assemble_scene_art
from game.art.dna_evolver import evolve_card_dna
from game.core.paths import project_root

TEST_CARDS = {
    'ARCHON': {
        'card_id': 'ARC-ARCHON-ATTACK-ARCANO_DEL_VACIO_01',
        'seed_candidates': [1101, 1102, 1107, 1113],
    },
    'SOLAR_WARRIOR': {
        'card_id': 'HYP-SOLAR-ATTACK-GUERRERO_ASTRAL_DE_HIPERBOREA_I',
        'seed_candidates': [2202, 2203, 2211, 2227],
    },
    'GUIDE_MAGE': {
        'card_id': 'BASE-GUIDE-GUARD-CAMPO_PROTECTOR',
        'seed_candidates': [3303, 3304, 3311, 3327],
    },
}


def _baseline_prompt(label: str) -> str:
    if label == 'ARCHON':
        return (
            'palette black crimson toxic green, '
            'motif archon corruption ritual staff, '
            'sacred geometry ritual seal, '
            'subject archon hierophant, '
            'object void ritual staff, '
            'environment void cathedral temple, '
            'scene type archon_void_scene, '
            'subject pose ritual_vertical, '
            'secondary object staff, '
            'camera ominous low angle, '
            'mood oppressive malign, '
            'subject kind archon_foreground, '
            'object kind ritual_staff, '
            'environment kind archon_cathedral, '
            'effects dark aura corruption smoke, '
            'effect signature corruption aura, '
            'energy pattern void sparks, '
            'lore tokens archon corruption ritual staff'
        )
    if label == 'SOLAR_WARRIOR':
        return (
            'palette gold amber ivory, '
            'motif solar warrior attack spear mountain, '
            'sacred geometry solar disc, '
            'subject solar warrior champion, '
            'object radiant spear, '
            'environment warm mountain citadel, '
            'scene type hyperborea_temple_scene, '
            'subject pose attack_diagonal, '
            'secondary object spear, '
            'camera heroic medium close, '
            'mood heroic radiant, '
            'subject kind warrior_foreground, '
            'object kind spear, '
            'environment kind citadel, '
            'effects warm light solar aura, '
            'effect signature spear flare, '
            'energy pattern sun arc, '
            'lore tokens solar warrior attack spear mountain solar'
        )
    return (
        'palette teal gold pearl, '
        'motif guide mage wisdom support chakana temple, '
        'sacred geometry chakana, '
        'subject guide mage sage, '
        'object orb staff, '
        'environment sacred temple plateau, '
        'scene type mountain_guardian_scene, '
        'subject pose support_vertical, '
        'secondary object orb, '
        'camera calm medium close, '
        'mood serene wise, '
        'subject kind oracle_totem, '
        'object kind orb, '
        'environment kind sanctuary, '
        'effects mystic aura wisdom glyphs, '
        'effect signature wisdom glyphs, '
        'energy pattern sacred geometry, '
        'lore tokens guide mage wisdom support chakana temple'
    )



def _variant_prompt(label: str, evolved: dict[str, object]) -> str:
    slots = evolved['chosen_variation_slots']
    overrides = evolved['final_overrides']
    if label == 'ARCHON':
        helmet = slots.get('helmet_variant', 'archon_crown').replace('_', ' ')
        cape = slots.get('cape_variant', 'split_ritual_robe').replace('_', ' ')
        aura = slots.get('aura_variant', 'corruption_smoke').replace('_', ' ')
        symbol = overrides.get('symbol_type', 'corrupt_seal').replace('_', ' ')
        env = slots.get('environment_detail_variant', 'void_monolith').replace('_', ' ')
        return (
            f'palette black crimson toxic green, motif archon ritual severe {helmet} {cape}, '
            f'sacred geometry {symbol}, subject archon hierophant with {helmet}, '
            f'object ritual staff with {slots.get("weapon_variant", "ritual_staff_head").replace("_", " ")}, '
            f'environment void cathedral temple with {env}, scene type archon_void_scene, '
            f'subject pose {overrides.get("pose_type", "ritual_vertical")}, secondary object staff, '
            'camera ominous low angle, mood oppressive malign, '
            'subject kind archon_foreground, object kind ritual_staff, environment kind archon_cathedral, '
            f'effects dark aura {aura}, effect signature {aura}, energy pattern void sparks, '
            f'lore tokens archon corruption ritual staff {helmet} {cape} {env}'
        )
    if label == 'SOLAR_WARRIOR':
        weapon = slots.get('weapon_variant', 'sun_spear').replace('_', ' ')
        helmet = slots.get('helmet_variant', 'solar_crest').replace('_', ' ')
        cape = slots.get('cape_variant', 'short_battle_cape').replace('_', ' ')
        aura = slots.get('aura_variant', 'solar_flare').replace('_', ' ')
        symbol = overrides.get('symbol_type', 'solar_disc').replace('_', ' ')
        env = slots.get('environment_detail_variant', 'sun_banner').replace('_', ' ')
        object_kind = 'sword' if 'blade' in weapon else 'spear'
        object_name = 'ceremonial blade' if 'blade' in weapon else 'sun spear'
        return (
            f'palette gold amber ivory, motif solar warrior heroic triangular {helmet} {cape}, '
            f'sacred geometry {symbol}, subject solar warrior champion with {helmet}, '
            f'object {object_name}, environment warm mountain citadel with {env}, '
            'scene type hyperborea_temple_scene, '
            f'subject pose {overrides.get("pose_type", "attack_diagonal")}, secondary object {object_name}, '
            'camera heroic medium close, mood heroic radiant, '
            'subject kind warrior_foreground, '
            f'object kind {object_kind}, environment kind citadel, '
            f'effects warm light {aura}, effect signature {aura}, energy pattern sun arc, '
            f'lore tokens solar warrior attack spear mountain solar {helmet} {cape} {env}'
        )
    helmet = slots.get('helmet_variant', 'hooded_cowl').replace('_', ' ')
    cape = slots.get('cape_variant', 'wide_support_robe').replace('_', ' ')
    aura = slots.get('aura_variant', 'wisdom_glyphs').replace('_', ' ')
    symbol = overrides.get('symbol_type', 'chakana_gate').replace('_', ' ')
    env = slots.get('environment_detail_variant', 'temple_lanterns').replace('_', ' ')
    weapon = slots.get('weapon_variant', 'orb_staff').replace('_', ' ')
    return (
        f'palette teal gold pearl, motif guide mage wisdom symbolic {helmet} {cape}, '
        f'sacred geometry {symbol}, subject guide mage sage with {helmet}, '
        f'object {weapon}, environment sacred temple plateau with {env}, '
        'scene type mountain_guardian_scene, '
        f'subject pose {overrides.get("pose_type", "support_vertical")}, secondary object {weapon}, '
        'camera calm medium close, mood serene wise, '
        'subject kind oracle_totem, object kind orb, environment kind sanctuary, '
        f'effects mystic aura {aura}, effect signature {aura}, energy pattern sacred geometry, '
        f'lore tokens guide mage wisdom support chakana temple {helmet} {cape} {env}'
    )



def _variant_key(evolved: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(evolved['chosen_variation_slots'].items()))



def _identity_stable(evolved: dict[str, object], metrics) -> bool:
    base_shape = evolved['base_dna']['dominant_shape']
    final_shape = evolved['final_constraint_result']['normalized_spec'].get('dominant_shape', base_shape)
    return evolved['accepted'] and base_shape == final_shape and metrics.silhouette_integrity >= 0.75



def _readability_improved(base_metrics, variant_metrics) -> bool:
    base_score = base_metrics.silhouette_integrity * 0.6 + base_metrics.subject_visible_ratio * 0.4
    variant_score = variant_metrics.silhouette_integrity * 0.6 + variant_metrics.subject_visible_ratio * 0.4
    return variant_score >= base_score



def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'card_art' / 'generated' / 'test_shape_dna'
    tmp_dir = root / 'reports' / 'art' / '_tmp_shape_dna'
    report_path = root / 'reports' / 'art' / 'shape_dna_test_report.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['shape_dna_test_report']

    for index, (label, config) in enumerate(TEST_CARDS.items(), start=1):
        card_id = config['card_id']
        base_prompt = _baseline_prompt(label)
        baseline_path = tmp_dir / f'{label.lower()}_baseline.png'
        baseline_result = assemble_scene_art(card_id.lower(), base_prompt, 9100 + index * 31, baseline_path)

        seen = set()
        accepted_variants = []
        for seed in config['seed_candidates']:
            evolved = evolve_card_dna(card_id, seed).model_dump()
            key = _variant_key(evolved)
            if key in seen:
                continue
            seen.add(key)
            accepted_variants.append(evolved)
            if len(accepted_variants) >= 2:
                break

        lines.extend([f'[{label}]', f'card_id={card_id}', f'base_dna={accepted_variants[0]["base_dna"] if accepted_variants else {}}'])
        for variant_index, evolved in enumerate(accepted_variants, start=1):
            prompt = _variant_prompt(label, evolved)
            out_path = out_dir / f'{label.lower()}_variant_{variant_index}.png'
            render_result = assemble_scene_art(card_id.lower(), prompt, evolved['seed'] + 7000, out_path)
            improved = _readability_improved(baseline_result.metrics, render_result.metrics)
            stable = _identity_stable(evolved, render_result.metrics)
            lines.extend([
                f'variant_{variant_index}_path={out_path.as_posix()}',
                f'variant_{variant_index}_seed={evolved["seed"]}',
                f'variant_{variant_index}_chosen_slots={evolved["chosen_variation_slots"]}',
                f'variant_{variant_index}_rejected_invalid={evolved["rejected_invalid_variations"]}',
                f'variant_{variant_index}_final_accepted={evolved["accepted"]}',
                f'variant_{variant_index}_final_overrides={evolved["final_overrides"]}',
                f'variant_{variant_index}_silhouette_integrity={render_result.metrics.silhouette_integrity}',
                f'variant_{variant_index}_subject_visible_ratio={render_result.metrics.subject_visible_ratio}',
                f'variant_{variant_index}_readability_improved={improved}',
                f'variant_{variant_index}_identity_stable={stable}',
                '',
            ])
        lines.append('')

    report_path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    print(f'[shape_dna] out={out_dir}')
    print(f'[shape_dna] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
