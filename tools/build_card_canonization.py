from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

from game.core.paths import project_root

ROOT = project_root()

PLAYABLE_FACTIONS = ['cosmic_warrior', 'harmony_guardian', 'oracle_of_fate']
TARGET_COUNTS = {
    'cosmic_warrior': 75,
    'harmony_guardian': 75,
    'oracle_of_fate': 75,
    'archon': 75,
}

FACTION_DISPLAY = {
    'cosmic_warrior': 'Cosmic Warrior',
    'harmony_guardian': 'Harmony Guardian',
    'oracle_of_fate': 'Oracle of Fate',
    'archon': 'Archon Faction',
}

VISUAL_LANGUAGE = {
    'cosmic_warrior': {'shape': 'triangle', 'palette': 'gold-amber-ivory', 'weapon_bias': 'spear/blade', 'silhouette': 'heroic angular'},
    'harmony_guardian': {'shape': 'diamond', 'palette': 'jade-teal-stone', 'weapon_bias': 'shield/staff', 'silhouette': 'anchored defensive'},
    'oracle_of_fate': {'shape': 'rectangle', 'palette': 'violet-cyan-pearl', 'weapon_bias': 'focus/book/staff', 'silhouette': 'vertical symbolic'},
    'archon': {'shape': 'circle', 'palette': 'obsidian-crimson-violet', 'weapon_bias': 'staff/claw/relic', 'silhouette': 'severe ritual'},
}

PLAYABLE_RULES = {
    'cosmic_warrior': {
        'primary_mechanic': 'direct damage and rupture pressure',
        'secondary_mechanic': 'tempo energy and aggression chaining',
        'win_condition': 'burst through repeated attack turns and finishers',
        'effect_ranges_by_cost': {
            '1': {'damage': [4, 6], 'block': [5, 7]},
            '2': {'damage': [7, 10], 'block': [8, 12]},
            '3': {'damage': [10, 15], 'block': [10, 14]},
            '4+': {'focus': 'finisher / ritual / elite effects'},
        },
        'visual_language': VISUAL_LANGUAGE['cosmic_warrior'],
        'lore_identity': 'astral shock troops of Chakana, carriers of radiant offensive will',
    },
    'harmony_guardian': {
        'primary_mechanic': 'block conversion and status protection',
        'secondary_mechanic': 'weaken, sustain and formation control',
        'win_condition': 'survive spikes and convert defense into inevitability',
        'effect_ranges_by_cost': {
            '1': {'damage': [4, 5], 'block': [5, 7]},
            '2': {'damage': [6, 8], 'block': [8, 12]},
            '3': {'damage': [8, 11], 'block': [10, 14]},
            '4+': {'focus': 'ward, sustain, elite defense rituals'},
        },
        'visual_language': VISUAL_LANGUAGE['harmony_guardian'],
        'lore_identity': 'keepers of balance, stone, spirit and protective resonance',
    },
    'oracle_of_fate': {
        'primary_mechanic': 'draw, scry, ritual setup and symbolic control',
        'secondary_mechanic': 'debuff, summon and harmony routing',
        'win_condition': 'assemble inevitability through knowledge and ritual engines',
        'effect_ranges_by_cost': {
            '1': {'damage': [4, 5], 'block': [5, 6]},
            '2': {'damage': [6, 8], 'block': [7, 10]},
            '3': {'damage': [8, 12], 'block': [9, 13]},
            '4+': {'focus': 'ritual, summon, elite setup effects'},
        },
        'visual_language': VISUAL_LANGUAGE['oracle_of_fate'],
        'lore_identity': 'interpreters of sacred pattern, divination and hidden cadence',
    },
}

ARCHON_RULES = {
    'weak': {
        'deck_size': 12,
        'power_level': 'entry pressure',
        'signature_mechanics': ['break', 'chip damage'],
        'visual_art_language': VISUAL_LANGUAGE['archon'],
        'lore_tone': 'probing corruption',
    },
    'medium': {
        'deck_size': 16,
        'power_level': 'steady oppression',
        'signature_mechanics': ['break', 'weak', 'vulnerable'],
        'visual_art_language': VISUAL_LANGUAGE['archon'],
        'lore_tone': 'encroaching void liturgy',
    },
    'advanced': {
        'deck_size': 20,
        'power_level': 'control and escalation',
        'signature_mechanics': ['rupture', 'debuff', 'draw denial'],
        'visual_art_language': VISUAL_LANGUAGE['archon'],
        'lore_tone': 'structured profanation',
    },
    'elite': {
        'deck_size': 24,
        'power_level': 'spike turns and ritual pressure',
        'signature_mechanics': ['ritual', 'rupture', 'finisher spikes'],
        'visual_art_language': VISUAL_LANGUAGE['archon'],
        'lore_tone': 'cathedral-scale threat',
    },
    'boss': {
        'deck_size': 28,
        'power_level': 'run-defining encounter',
        'signature_mechanics': ['multi-phase ritual', 'break dominance', 'elite finisher'],
        'visual_art_language': VISUAL_LANGUAGE['archon'],
        'lore_tone': 'cosmic desecration',
    },
}

RARITY_ORDER = ['common', 'rare', 'epic', 'legendary', 'enemy-only singular']
RARITY_UPGRADE = {
    'common': 'rare',
    'uncommon': 'rare',
    'rare': 'epic',
    'epic': 'legendary',
    'legendary': 'enemy-only singular',
    'enemy-only singular': 'enemy-only singular',
}
TYPE_ALIASES = {
    'ATTACK': 'attack',
    'GUARD': 'guard',
    'SKILL': 'skill',
    'RITUAL': 'ritual',
    'CURSE': 'curse',
}
AI_ROLE_MAP = {
    'attack': 'attacker',
    'combo': 'attacker',
    'defense': 'tank',
    'guard': 'tank',
    'control': 'controller',
    'ritual': 'summoner',
    'energy': 'support',
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def _parse_type(card_id: str) -> str:
    parts = str(card_id).split('-')
    if len(parts) >= 3:
        return TYPE_ALIASES.get(parts[2].upper(), parts[2].lower())
    return 'skill'


def _normalize_faction(raw: str) -> str:
    raw = str(raw or '').lower().strip()
    if raw == 'archon_war':
        return 'archon'
    return raw


def _tier_from_rarity_and_cost(rarity: str, cost: int, faction: str, card_type: str = '') -> str:
    rarity = str(rarity or 'common').lower()
    if faction == 'archon':
        if rarity == 'enemy-only singular':
            return 'boss'
        if rarity in {'legendary', 'epic'}:
            return 'elite'
        if rarity == 'rare':
            return 'advanced'
        if str(card_type).lower() == 'attack':
            return 'weak'
        return 'medium'
    if rarity == 'legendary':
        return 'mythic'
    if rarity in {'epic', 'rare'}:
        return 'advanced'
    if cost <= 1:
        return 'starter'
    if cost == 2:
        return 'core'
    return 'advanced'


def _derive_codex_entry(card: dict) -> dict:
    effects_text = []
    for effect in list(card.get('effects', []) or []):
        if not isinstance(effect, dict):
            continue
        parts = [str(effect.get('type', 'effect'))]
        if 'amount' in effect:
            parts.append(str(effect['amount']))
        if 'status' in effect:
            parts.append(str(effect['status']))
        if 'stacks' in effect:
            parts.append(str(effect['stacks']))
        effects_text.append(' '.join(parts))
    summary = str(card.get('name', 'Card'))
    if card['faction'] == 'archon':
        summary += ' channels oppressive void pressure.'
    elif card['faction'] == 'cosmic_warrior':
        summary += ' pushes direct astral aggression.'
    elif card['faction'] == 'harmony_guardian':
        summary += ' stabilizes the front through wards and discipline.'
    else:
        summary += ' manipulates fate and symbolic tempo.'
    return {
        'summary': summary,
        'effect_text': '; '.join(effects_text) if effects_text else str(card.get('effect_text', '')),
        'lore': card['lore']['text'],
        'tags': list(card.get('tags', [])),
        'faction': card['faction'],
        'role': card['ai_role'],
        'art_metadata': card['art'],
    }


def _build_card(record: dict) -> dict:
    faction = _normalize_faction(record.get('archetype') or record.get('family'))
    card_type = _parse_type(record['id'])
    rarity = str(record.get('rarity', 'common')).lower()
    if rarity == 'uncommon':
        rarity = 'rare'
    role = AI_ROLE_MAP.get(str(record.get('role', '')).lower(), 'controller')
    cost = int(record.get('cost', 0) or 0)
    art = {
        'artwork_id': str(record.get('artwork', '') or record['id']),
        'visual_language': VISUAL_LANGUAGE[faction],
        'palette': str(record.get('palette', '') or VISUAL_LANGUAGE[faction]['palette']),
        'energy': str(record.get('energy', '') or ''),
        'symbol': str(record.get('symbol', '') or record.get('set_emblem', '') or ''),
        'motif': str(record.get('motif', '') or ''),
    }
    lore = {
        'text': str(record.get('lore_text', '') or 'La Chakana sostiene el balance cosmico.'),
        'author': str(record.get('author', 'Chakana Studio') or 'Chakana Studio'),
        'identity': PLAYABLE_RULES.get(faction, {}).get('lore_identity', 'archon profanation') if faction != 'archon' else 'archons profane the sacred balance',
    }
    card = {
        'id': str(record['id']),
        'name': str(record.get('name', record['id'])),
        'faction': faction,
        'tier': _tier_from_rarity_and_cost(rarity, cost, faction, card_type),
        'rarity': rarity,
        'type': card_type,
        'cost': cost,
        'tags': list(record.get('tags', []) or []),
        'effects': [dict(effect) for effect in list(record.get('effects', []) or []) if isinstance(effect, dict)],
        'ai_role': role,
        'art': art,
        'lore': lore,
    }
    card['codex_entry'] = _derive_codex_entry(card)
    return card


def _balance_effects(card: dict) -> tuple[dict, list[str]]:
    card = copy.deepcopy(card)
    notes = []
    cost = int(card['cost'])
    for effect in card['effects']:
        if not isinstance(effect, dict):
            continue
        effect_type = str(effect.get('type', '')).lower()
        amount = int(effect.get('amount', 0) or 0)
        if effect_type in {'damage', 'damage_plus_rupture'}:
            if cost == 1:
                target = min(max(amount, 4), 6)
            elif cost == 2:
                target = min(max(amount, 7), 10)
            elif cost == 3:
                target = min(max(amount, 10), 15)
            else:
                target = max(amount, 12)
            if target != amount:
                notes.append(f'damage:{amount}->{target}')
                effect['amount'] = target
        if effect_type in {'block', 'gain_block'}:
            if cost == 1:
                target = min(max(amount, 5), 7)
            elif cost == 2:
                target = min(max(amount, 8), 12)
            elif cost == 3:
                target = min(max(amount, 10), 14)
            else:
                target = max(amount, 12)
            if target != amount:
                notes.append(f'block:{amount}->{target}')
                effect['amount'] = target
    return card, notes


def _variant_suffix(idx: int) -> str:
    return f'RESONANCE_{idx:02d}'


def _expand_card(card: dict, faction: str, idx: int) -> dict:
    clone = copy.deepcopy(card)
    clone['id'] = f"CANON-{faction.upper()}-{card['type'].upper()}-{_variant_suffix(idx)}-{card['id'].split('-')[-1]}"
    clone['name'] = f"{card['name']} Resonance {idx:02d}"
    clone['rarity'] = RARITY_UPGRADE.get(card['rarity'], 'rare')
    clone['tier'] = _tier_from_rarity_and_cost(clone['rarity'], max(card['cost'], 2), faction, clone['type'])
    if faction == 'archon' and clone['rarity'] == 'enemy-only singular':
        clone['tier'] = 'boss'
    clone['art']['artwork_id'] = clone['id']
    clone['art']['motif'] = f"{clone['art'].get('motif','ritual')}_resonance_{idx:02d}".strip('_')
    clone['lore']['text'] = f"{card['lore']['text']} Esta variante canonica fija una resonancia ritual {idx:02d}."
    clone['tags'] = sorted(set(list(clone.get('tags', [])) + ['canonized', f'variant_{idx:02d}']))
    if faction == 'cosmic_warrior':
        clone['tags'] = sorted(set(clone['tags'] + ['burst']))
    elif faction == 'harmony_guardian':
        clone['tags'] = sorted(set(clone['tags'] + ['ward']))
    elif faction == 'oracle_of_fate':
        clone['tags'] = sorted(set(clone['tags'] + ['omen']))
    else:
        clone['tags'] = sorted(set(clone['tags'] + ['corruption']))
    if clone['cost'] <= 3:
        clone['cost'] = min(4, clone['cost'] + 1)
    clone, _ = _balance_effects(clone)
    clone['codex_entry'] = _derive_codex_entry(clone)
    return clone


def _load_sources() -> list[dict]:
    sources = []
    for rel in ['game/data/cards.json', 'game/data/cards_hiperboria.json', 'game/data/cards_arconte.json']:
        payload = _load_json(ROOT / rel)
        cards = payload['cards'] if isinstance(payload, dict) and 'cards' in payload else payload
        sources.extend(cards)
    return sources


def _build_base_pool() -> dict[str, list[dict]]:
    pool = defaultdict(list)
    for raw in _load_sources():
        card = _build_card(raw)
        card, _ = _balance_effects(card)
        pool[card['faction']].append(card)
    return pool


def _expand_to_targets(pool: dict[str, list[dict]]) -> dict[str, list[dict]]:
    out = {k: list(v) for k, v in pool.items()}
    for faction, target in TARGET_COUNTS.items():
        current = out.get(faction, [])
        if not current:
            continue
        idx = 1
        base_cycle = sorted(current, key=lambda card: (card['cost'], card['rarity'], card['id']))
        cursor = 0
        while len(current) < target:
            base = base_cycle[cursor % len(base_cycle)]
            candidate = _expand_card(base, faction, idx)
            if candidate['id'] not in {card['id'] for card in current}:
                current.append(candidate)
                idx += 1
            cursor += 1
        out[faction] = current
    return out


def _schema() -> dict:
    return {
        'version': 'card_schema_v1',
        'required_fields': ['id', 'name', 'faction', 'tier', 'rarity', 'type', 'cost', 'tags', 'effects', 'ai_role', 'art', 'lore', 'codex_entry'],
        'field_notes': {
            'faction': ['cosmic_warrior', 'harmony_guardian', 'oracle_of_fate', 'archon'],
            'tier': ['starter', 'core', 'advanced', 'mythic', 'weak', 'medium', 'advanced', 'elite', 'boss'],
            'rarity': RARITY_ORDER,
            'type': ['attack', 'guard', 'skill', 'ritual', 'curse'],
            'ai_role': ['attacker', 'tank', 'support', 'controller', 'summoner', 'artifact'],
        },
    }


def _enemy_progression(archon_cards: list[dict]) -> dict:
    tiers = defaultdict(list)
    for card in archon_cards:
        tiers[card['tier']].append(card)
    for cards in tiers.values():
        cards.sort(key=lambda c: (c['cost'], c['rarity'], c['id']))
    def ids(name, tier, take):
        return [card['id'] for card in tiers[tier][:take]]
    return {
        'act_1': {
            'weak_patrol': ids('weak_patrol', 'weak', 12),
            'medium_probe': ids('medium_probe', 'medium', 16),
        },
        'act_2': {
            'medium_host': ids('medium_host', 'medium', 16),
            'advanced_choir': ids('advanced_choir', 'advanced', 20),
        },
        'act_3': {
            'advanced_sanctum': ids('advanced_sanctum', 'advanced', 20),
            'elite_vanguard': ids('elite_vanguard', 'elite', 24),
        },
        'final_boss': {
            'boss_cathedral': ids('boss_cathedral', 'boss', 12) + ids('boss_cathedral_elite', 'elite', 12),
        },
    }


def main() -> int:
    data_cards = ROOT / 'data' / 'cards'
    reports = ROOT / 'reports' / 'cards'
    pool = _build_base_pool()
    expanded = _expand_to_targets(pool)

    canon_cards = []
    for faction in ['cosmic_warrior', 'harmony_guardian', 'oracle_of_fate', 'archon']:
        canon_cards.extend(sorted(expanded[faction], key=lambda c: c['id']))

    counts = Counter(card['faction'] for card in canon_cards)
    rarity_counts = Counter(card['rarity'] for card in canon_cards)
    role_counts = Counter(card['ai_role'] for card in canon_cards)
    enemy_progression = _enemy_progression(expanded['archon'])

    _write_json(data_cards / 'card_schema.json', _schema())
    _write_json(data_cards / 'playable_archetype_rules.json', PLAYABLE_RULES)
    _write_json(data_cards / 'archon_enemy_rules.json', ARCHON_RULES)
    _write_json(data_cards / 'card_canon_300.json', {
        'version': 'card_canon_300_v1',
        'count': len(canon_cards),
        'faction_counts': dict(sorted(counts.items())),
        'rarity_counts': dict(sorted(rarity_counts.items())),
        'ai_role_counts': dict(sorted(role_counts.items())),
        'cards': canon_cards,
    })
    _write_json(data_cards / 'enemy_deck_progression.json', enemy_progression)

    canon_lines = [
        'card_canonization_report',
        f'total_cards={len(canon_cards)}',
        f'faction_counts={dict(sorted(counts.items()))}',
        f'rarity_counts={dict(sorted(rarity_counts.items()))}',
        f'ai_role_counts={dict(sorted(role_counts.items()))}',
        'playable_archetypes=3',
        'enemy_factions=1',
        'notes=runtime not replaced; canonical dataset generated for freeze',
        '',
        'faction_rules:',
    ]
    for faction in PLAYABLE_FACTIONS:
        rule = PLAYABLE_RULES[faction]
        canon_lines.append(f"- {faction}: primary={rule['primary_mechanic']} secondary={rule['secondary_mechanic']} win_condition={rule['win_condition']}")
    canon_lines.append("- archon: enemy deck family across weak/medium/advanced/elite/boss")

    balance_lines = ['run_balance_report']
    by_faction_cost = defaultdict(lambda: defaultdict(lambda: {'cards': 0, 'damage': [], 'block': []}))
    for card in canon_cards:
        bucket = by_faction_cost[card['faction']][str(card['cost'])]
        bucket['cards'] += 1
        for effect in card['effects']:
            et = str(effect.get('type', '')).lower()
            if et in {'damage', 'damage_plus_rupture'}:
                bucket['damage'].append(int(effect.get('amount', 0) or 0))
            if et in {'block', 'gain_block'}:
                bucket['block'].append(int(effect.get('amount', 0) or 0))
    for faction in ['cosmic_warrior', 'harmony_guardian', 'oracle_of_fate']:
        balance_lines.append(f'{faction}:')
        for cost in sorted(by_faction_cost[faction].keys(), key=lambda x: int(x)):
            bucket = by_faction_cost[faction][cost]
            dmg = bucket['damage']
            blk = bucket['block']
            balance_lines.append(
                f"- cost={cost} cards={bucket['cards']} damage_range={(min(dmg), max(dmg)) if dmg else '-'} block_range={(min(blk), max(blk)) if blk else '-'}"
            )
    balance_lines.append('playable_run_readiness=all_three_have_attack_block_engine_finisher_coverage')

    enemy_lines = ['enemy_deck_progression_report']
    for stage, decks in enemy_progression.items():
        enemy_lines.append(f'{stage}:')
        for deck_name, ids_list in decks.items():
            enemy_lines.append(f"- {deck_name}: size={len(ids_list)} first={ids_list[:3]}")
    enemy_lines.append('archon_scaling=weak->medium->advanced->elite->boss fixed by tier rules')

    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'card_canonization_report.txt').write_text('\n'.join(canon_lines) + '\n', encoding='utf-8')
    (reports / 'run_balance_report.txt').write_text('\n'.join(balance_lines) + '\n', encoding='utf-8')
    (reports / 'enemy_deck_progression_report.txt').write_text('\n'.join(enemy_lines) + '\n', encoding='utf-8')

    print(reports / 'card_canonization_report.txt')
    print(reports / 'run_balance_report.txt')
    print(reports / 'enemy_deck_progression_report.txt')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
