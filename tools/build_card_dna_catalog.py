from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from game.core.paths import project_root


VISUAL_ARCHETYPE_MAP = {
    'cosmic_warrior': 'solar_warrior',
    'archon_war': 'archon',
    'harmony_guardian': 'guide_mage',
    'oracle_of_fate': 'guide_mage',
}

DECK_ARCHETYPE_MAP = {
    'cosmic_warrior': 'solar_warrior',
    'archon_war': 'archon',
    'harmony_guardian': 'guide_mage',
    'oracle_of_fate': 'guide_mage',
}

SHAPE_MAP = {
    'solar_warrior': ('triangle', 'heroic_armor'),
    'archon': ('circle', 'ritual_halo'),
    'guide_mage': ('rectangle', 'symbolic_robe'),
    'beast_guardian': ('diamond', 'ward_plate'),
    'void_monk': ('spiral', 'void_cloak'),
    'sacred_construct': ('square', 'temple_frame'),
}

VISUAL_DEFAULTS = {
    'solar_warrior': {'weapon_type': 'spear', 'environment_type': 'ritual_duel_scene', 'pose_type': 'attack_diagonal', 'symbol_type': 'solar_disc', 'energy_type': 'solar_light', 'palette_family': 'gold_amber_ivory'},
    'archon': {'weapon_type': 'staff', 'environment_type': 'archon_void_scene', 'pose_type': 'ritual_vertical', 'symbol_type': 'corrupt_seal', 'energy_type': 'void_sparks', 'palette_family': 'violet_crimson_obsidian'},
    'guide_mage': {'weapon_type': 'staff', 'environment_type': 'mountain_guardian_scene', 'pose_type': 'support_vertical', 'symbol_type': 'chakana', 'energy_type': 'sacred_wind', 'palette_family': 'teal_gold_pearl'},
    'beast_guardian': {'weapon_type': 'shield', 'environment_type': 'mountain_guardian_scene', 'pose_type': 'guarded_anchor', 'symbol_type': 'ward_mandala', 'energy_type': 'stable_rings', 'palette_family': 'teal_gold_stone'},
    'void_monk': {'weapon_type': 'focus', 'environment_type': 'void_sanctum_scene', 'pose_type': 'spiral_ritual', 'symbol_type': 'void_eye', 'energy_type': 'shadow_streams', 'palette_family': 'indigo_ash_violet'},
    'sacred_construct': {'weapon_type': 'relic', 'environment_type': 'temple_construct_scene', 'pose_type': 'frontal_iconic_pose', 'symbol_type': 'chakana_gate', 'energy_type': 'stable_rings', 'palette_family': 'stone_gold_cyan'},
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _load_balance_overrides(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    raw = _load_json(path)
    if not isinstance(raw, dict):
        return {}
    overrides = raw.get('cards', {})
    return overrides if isinstance(overrides, dict) else {}


def _normalize_effect_type(effect_type: str, tags: list[str], visual_archetype: str) -> list[str]:
    t = str(effect_type or '').lower()
    out: set[str] = set()
    if t in {'damage', 'self_damage', 'damage_if_enemy_break', 'damage_plus_rupture'}:
        out.add('damage')
    if t in {'block', 'gain_block', 'gain_block_if_no_direction', 'double_block_cap'}:
        out.add('shield')
    if t in {'heal', 'heal_percent'}:
        out.add('heal')
    if t in {'gain_mana', 'gain_mana_next_turn', 'draw', 'draw_if_enemy_break', 'draw_if_no_block', 'draw_on_kill', 'draw_if_direction_played', 'copy_last_played', 'copy_next_played', 'retain', 'discount_next_attack', 'scry'}:
        out.add('buff')
        if t == 'draw':
            out.add('draw')
    if t in {'status', 'apply_break', 'weaken_enemy', 'vulnerable_enemy', 'debuff'}:
        out.add('debuff')
    if t in {'summon', 'spawn', 'invoke', 'ritual_trama'}:
        out.add('summon')
    if t in {'ritual_trama', 'harmony_delta', 'set_rupture', 'rupture'}:
        out.add('ritual')
    if 'ritual' in tags:
        out.add('ritual')
    if any(tok in tags for tok in ('summon', 'invoke', 'portal')):
        out.add('summon')
    if not out and visual_archetype in {'guide_mage', 'beast_guardian'}:
        out.add('buff')
    return sorted(out)


def _map_gameplay_role(raw_role: str, tags: list[str], effects: list[dict], deck_archetype: str) -> str:
    role = str(raw_role or '').lower()
    effect_types = {str(e.get('type', '')).lower() for e in effects if isinstance(e, dict)}
    tags_set = {str(t).lower() for t in tags}
    if 'artifact' in tags_set or deck_archetype == 'sacred_construct':
        return 'artifact'
    if 'summon' in tags_set or 'portal' in tags_set or 'invoke' in tags_set or role == 'ritual':
        return 'summoner'
    if role in {'defense', 'guard'} or 'block' in tags_set or 'gain_block' in effect_types or 'block' in effect_types:
        return 'tank'
    if role in {'control'} or {'draw', 'scry', 'copy_last_played', 'copy_next_played'} & effect_types:
        return 'controller'
    if role in {'energy'} or {'heal', 'gain_mana', 'gain_mana_next_turn', 'retain'} & effect_types:
        return 'support'
    if role in {'attack', 'combo'} or 'damage' in effect_types or 'damage_plus_rupture' in effect_types:
        return 'attacker'
    if deck_archetype in {'guide_mage', 'beast_guardian'}:
        return 'support'
    return 'controller'


def _derive_weapon(card: dict, scene_spec: dict, visual_archetype: str) -> str:
    text = ' '.join([
        str(card.get('name', '') or ''),
        str(scene_spec.get('object_kind', '') or ''),
        str(scene_spec.get('secondary_object', '') or ''),
        ' '.join(str(t) for t in (card.get('tags') or [])),
    ]).lower()
    if visual_archetype == 'archon':
        return 'staff'
    if visual_archetype == 'guide_mage':
        if any(tok in text for tok in ('orb', 'eye', 'codex', 'book', 'divination')):
            return 'focus'
        return 'staff'
    if any(tok in text for tok in ('spear', 'lanza')):
        return 'spear'
    if any(tok in text for tok in ('sword', 'blade', 'filo', 'axe', 'garra', 'claw')):
        return 'sword'
    if any(tok in text for tok in ('shield', 'escudo', 'ward', 'muralla')):
        return 'shield'
    if any(tok in text for tok in ('orb', 'eye', 'codex', 'book', 'divination')):
        return 'focus'
    if any(tok in text for tok in ('altar', 'seal', 'tablet', 'portal', 'relic')):
        return 'relic'
    return VISUAL_DEFAULTS[visual_archetype]['weapon_type']


def _derive_visual(card: dict, scene_spec: dict, visual_archetype: str) -> dict:
    dominant_shape, secondary_shape = SHAPE_MAP[visual_archetype]
    defaults = VISUAL_DEFAULTS[visual_archetype]
    return {
        'entity_type': 'HUMANOID' if visual_archetype in {'solar_warrior', 'archon', 'guide_mage', 'beast_guardian', 'void_monk'} else 'OBJECT',
        'archetype': visual_archetype,
        'dominant_shape': dominant_shape,
        'secondary_shape': secondary_shape,
        'weapon_type': _derive_weapon(card, scene_spec, visual_archetype),
        'environment_type': str(scene_spec.get('scene_type', '') or defaults['environment_type']).strip().lower().replace(' ', '_'),
        'pose_type': str(scene_spec.get('subject_pose', '') or defaults['pose_type']).strip().lower().replace(' ', '_'),
        'symbol_type': str(scene_spec.get('symbol', '') or card.get('set_emblem', '') or defaults['symbol_type']).strip().lower().replace(' ', '_'),
        'energy_type': str(scene_spec.get('energy', '') or card.get('energy', '') or defaults['energy_type']).strip().lower().replace(' ', '_'),
        'palette_family': str(scene_spec.get('palette', '') or card.get('palette', '') or defaults['palette_family']).strip().lower().replace(' ', '_').replace('-', '_'),
        'artwork': str(card.get('artwork', '') or card.get('id', '')),
        'sprite_path': str(card.get('sprite_path', '') or ''),
        'source_archetype': str(card.get('archetype', '') or ''),
    }


def _merge_effects(base_effects: list[dict], override_effects: list[dict] | None) -> list[dict]:
    if not isinstance(override_effects, list) or not override_effects:
        return [dict(effect) for effect in list(base_effects or []) if isinstance(effect, dict)]
    return [dict(effect) for effect in override_effects if isinstance(effect, dict)]


def _apply_card_override(card: dict, override: dict) -> dict:
    if not isinstance(override, dict) or not override:
        return dict(card)
    cooked = dict(card)
    scalar_fields = ['cost', 'target', 'direction', 'role', 'family', 'taxonomy', 'rarity']
    for field in scalar_fields:
        if field in override:
            cooked[field] = override[field]
    if 'tags' in override and isinstance(override['tags'], list):
        cooked['tags'] = list(override['tags'])
    if 'effects' in override:
        cooked['effects'] = _merge_effects(cooked.get('effects', []), override.get('effects'))
    return cooked


def main() -> int:
    root = project_root()
    manifest_path = root / 'data' / 'cards' / 'card_manifest.json'
    prompts_path = root / 'game' / 'data' / 'card_prompts.json'
    index_path = root / 'data' / 'card_dna' / 'index.json'
    catalog_path = root / 'data' / 'card_dna' / 'card_dna_catalog.json'
    report_path = root / 'reports' / 'card_dna_validation.txt'
    overrides_path = root / 'data' / 'balance' / 'card_balance_overrides.json'
    manifest = _load_json(manifest_path)
    prompts = _load_json(prompts_path).get('cards', {})
    cards = manifest.get('cards', [])
    overrides = _load_balance_overrides(overrides_path)

    catalog_cards = {}
    visual_archetype_counts = Counter()
    deck_archetype_counts = Counter()
    gameplay_role_counts = Counter()
    action_type_counts = Counter()
    issues = []

    for card in cards:
        cid = str(card.get('id', '') or '')
        if not cid:
            issues.append('missing_id_in_manifest')
            continue
        card = _apply_card_override(card, overrides.get(cid, {}))
        source_archetype = str(card.get('archetype', '') or card.get('family', '') or '').lower().strip()
        visual_archetype = VISUAL_ARCHETYPE_MAP.get(source_archetype, 'guide_mage')
        deck_archetype = DECK_ARCHETYPE_MAP.get(source_archetype, 'guide_mage')
        prompt_entry = prompts.get(cid, {}) if isinstance(prompts, dict) else {}
        scene_spec = prompt_entry.get('scene_spec', {}) if isinstance(prompt_entry, dict) else {}
        lore = {
            'name': str(card.get('name', '') or cid),
            'lore_text': str(card.get('lore_text', '') or 'La Chakana sostiene el balance cosmico.'),
            'tags': list(card.get('tags', []) or []),
            'author': str(card.get('author', 'Chakana Studio') or 'Chakana Studio'),
            'source_order': str(card.get('source_order', '') or card.get('order', '') or ''),
        }
        action_types = sorted({atype for effect in list(card.get('effects', []) or []) for atype in _normalize_effect_type(effect.get('type', ''), lore['tags'], visual_archetype)})
        if not action_types:
            action_types = ['ritual'] if 'ritual' in {t.lower() for t in lore['tags']} else ['buff']
        gameplay = {
            'gameplay_role': _map_gameplay_role(card.get('role', ''), lore['tags'], list(card.get('effects', []) or []), deck_archetype),
            'deck_archetype': deck_archetype,
            'source_archetype': source_archetype,
            'action_types': action_types,
            'cost': int(card.get('cost', 0) or 0),
            'target': str(card.get('target', 'enemy') or 'enemy'),
            'direction': str(card.get('direction', 'ESTE') or 'ESTE'),
            'effects': list(card.get('effects', []) or []),
            'taxonomy': str(card.get('taxonomy', 'engine') or 'engine'),
            'family': str(card.get('family', 'neutral') or 'neutral'),
            'legacy_role': str(card.get('role', '') or ''),
        }
        visual = _derive_visual(card, scene_spec, visual_archetype)
        entry = {
            'id': cid,
            'canonical_id': str(card.get('canonical_id', cid) or cid),
            'legacy_id': str(card.get('legacy_id', '') or ''),
            'set': str(card.get('set', '') or '').lower(),
            'rarity': str(card.get('rarity', 'common') or 'common').lower(),
            'lore': lore,
            'gameplay': gameplay,
            'visual': visual,
        }
        catalog_cards[cid] = entry
        visual_archetype_counts[visual_archetype] += 1
        deck_archetype_counts[deck_archetype] += 1
        gameplay_role_counts[gameplay['gameplay_role']] += 1
        for action_type in action_types:
            action_type_counts[action_type] += 1

    catalog = {
        'version': 'card_dna_catalog_v2',
        'count': len(catalog_cards),
        'archetype_counts': dict(sorted(visual_archetype_counts.items())),
        'deck_archetype_counts': dict(sorted(deck_archetype_counts.items())),
        'gameplay_role_counts': dict(sorted(gameplay_role_counts.items())),
        'action_type_counts': dict(sorted(action_type_counts.items())),
        'cards': dict(sorted(catalog_cards.items())),
    }
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')

    index = {
        'version': 'card_dna_v3',
        'status': 'canonical_catalog_180_cards',
        'entry_count': len(catalog_cards),
        'entries': sorted(catalog_cards.keys()),
        'required_fields': ['id', 'lore', 'gameplay', 'rarity', 'visual'],
        'derivation_policy': 'canonical catalog first; explicit seed entries optional; no art fallback outside card_dna.visual',
        'catalog_file': 'data/card_dna/card_dna_catalog.json',
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')

    lines = [
        'card_dna_validation',
        f'total_cards={len(catalog_cards)}',
        f'unique_ids={len(set(catalog_cards.keys()))}',
        f'missing_ids={len(cards) - len(catalog_cards)}',
        f'issues={len(issues)}',
        f'visual_archetype_counts={dict(sorted(visual_archetype_counts.items()))}',
        f'deck_archetype_counts={dict(sorted(deck_archetype_counts.items()))}',
        f'gameplay_role_counts={dict(sorted(gameplay_role_counts.items()))}',
        f'action_type_counts={dict(sorted(action_type_counts.items()))}',
        f'overrides_applied={len(overrides)}',
        '',
        'cards:',
    ]
    for cid, entry in sorted(catalog_cards.items()):
        has_required = all([entry.get('id'), entry.get('lore'), entry.get('gameplay'), entry.get('rarity'), entry.get('visual')])
        lines.append(
            ' | '.join([
                cid,
                f"deck_archetype={entry['gameplay']['deck_archetype']}",
                f"visual_archetype={entry['visual']['archetype']}",
                f"gameplay_role={entry['gameplay']['gameplay_role']}",
                f"action_types={','.join(entry['gameplay']['action_types'])}",
                f"rarity={entry['rarity']}",
                f"weapon={entry['visual']['weapon_type']}",
                f"energy={entry['visual']['energy_type']}",
                f"pose={entry['visual']['pose_type']}",
                f"status={'OK' if has_required else 'MISSING_FIELDS'}",
            ])
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(report_path)
    print(catalog_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
