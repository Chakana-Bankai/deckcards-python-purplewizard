from __future__ import annotations

import io
import statistics
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from dataclasses import dataclass, field

from game.cards.card_canon_registry import load_card_canon_catalog, load_canon_combat_payloads, load_enemy_deck_progression
from game.combat.combat_state import CombatState
from game.core.rng import SeededRNG
from tools.lib.common import ROOT, write_text_report

REPORT_PATH = ROOT / 'reports' / 'run_tests' / 'archetype_run_balance_report.txt'
PLAYABLE_ARCHETYPES = ('cosmic_warrior', 'harmony_guardian', 'oracle_of_fate')
RUNS_PER_ARCHETYPE = 60
DRY_RUNS_PER_ARCHETYPE = 12
MAX_TURNS = 22
FINAL_BOSS_MAX_TURNS = 30
PLAYER_HP = 78


@dataclass
class StageResult:
    stage_key: str
    deck_name: str
    win: bool
    turns: int
    damage_dealt: int
    damage_taken: int
    block_generated: int
    cards_played: int
    dead_cards_seen: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    run_id: str
    archetype: str
    anchor_card_id: str
    win: bool
    act_reached: str
    turn_count: int
    damage_taken_total: int
    damage_dealt_total: int
    block_generated_total: int
    cards_played_total: int
    dead_cards_seen: list[str] = field(default_factory=list)
    dominant_failure_reason: str = 'victory'
    stages: list[StageResult] = field(default_factory=list)
    card_usage: dict[str, int] = field(default_factory=dict)


_EFFECT_ALIAS = {
    'block': 'gain_block',
    'shield': 'gain_block',
    'gain_mana': 'gain_energy',
    'energy': 'gain_energy',
}


def _normalize_effect_type(effect_type: str) -> str:
    return _EFFECT_ALIAS.get(str(effect_type or '').strip().lower(), str(effect_type or '').strip().lower())


def _estimate_card_outputs(card_payload: dict) -> dict[str, int]:
    out = {
        'damage': 0,
        'block': 0,
        'heal': 0,
        'buff': 0,
        'debuff': 0,
    }
    for effect in list(card_payload.get('effects', []) or []):
        if not isinstance(effect, dict):
            continue
        eff_type = _normalize_effect_type(effect.get('type', ''))
        amount = int(effect.get('amount', effect.get('base', 0)) or 0)
        if eff_type == 'damage':
            out['damage'] += max(0, amount)
        elif eff_type == 'gain_block':
            out['block'] += max(0, amount)
        elif eff_type == 'heal':
            out['heal'] += max(0, amount)
        elif eff_type in {'apply_break', 'vulnerable_enemy', 'weaken_enemy', 'status'}:
            out['debuff'] += max(1, amount)
        elif eff_type in {'draw', 'scry', 'gain_energy', 'harmony_delta', 'ritual_trama'}:
            out['buff'] += max(1, amount)
    return out


def _deck_bias_score(card_payload: dict, role: str) -> float:
    score = 0.0
    est = _estimate_card_outputs(card_payload)
    if role == 'attacker':
        score += est['damage'] * 1.2 + est['buff'] * 0.4
    elif role == 'tank':
        score += est['block'] * 1.2 + est['heal'] * 0.9 + est['debuff'] * 0.3
    elif role == 'support':
        score += est['heal'] * 1.1 + est['buff'] * 0.9 + est['block'] * 0.5
    elif role == 'controller':
        score += est['debuff'] * 1.1 + est['buff'] * 0.7 + est['damage'] * 0.4
    elif role == 'summoner':
        score += est['buff'] * 1.0 + est['damage'] * 0.6 + est['block'] * 0.4
    else:
        score += est['damage'] + est['block'] + est['buff']
    score += max(0, 5 - int(card_payload.get('cost', 0) or 0)) * 0.15
    return score


def _build_player_deck(archetype: str, cards_by_id: dict[str, dict], catalog_cards: dict[str, object], run_seed: int) -> tuple[list[str], str]:
    pool = [card for card in catalog_cards.values() if str(card.faction) == archetype]
    if not pool:
        raise RuntimeError(f'No cards available for archetype {archetype}')
    role_priority = {
        'cosmic_warrior': ('attacker', 'controller', 'tank'),
        'harmony_guardian': ('tank', 'support', 'controller'),
        'oracle_of_fate': ('controller', 'support', 'summoner'),
    }.get(archetype, ('controller', 'support', 'attacker'))
    role_buckets: dict[str, list[object]] = defaultdict(list)
    for card in pool:
        role_buckets[str(card.ai_role)].append(card)
    picked: list[str] = []
    anchor_card_id = ''
    for role in role_priority:
        ranked = sorted(
            role_buckets.get(role, []),
            key=lambda item: (
                -_deck_bias_score(cards_by_id[item.id], str(item.ai_role)),
                int(item.cost),
                item.id,
            ),
        )
        take = 7 if role == role_priority[0] else 5
        for card in ranked[:take]:
            if card.id not in picked:
                picked.append(card.id)
                if not anchor_card_id:
                    anchor_card_id = card.id
    fallback = sorted(
        pool,
        key=lambda item: (
            -_deck_bias_score(cards_by_id[item.id], str(item.ai_role)),
            int(item.cost),
            item.id,
        ),
    )
    for card in fallback:
        if len(picked) >= 20:
            break
        if card.id not in picked:
            picked.append(card.id)
            if not anchor_card_id:
                anchor_card_id = card.id
    rotation = run_seed % max(1, len(picked))
    picked = picked[rotation:] + picked[:rotation]
    return picked[:20], anchor_card_id or picked[0]


def _stage_specs() -> list[tuple[str, str, int]]:
    return [
        ('act_1', 'weak_patrol', 42),
        ('act_2', 'advanced_choir', 56),
        ('act_3', 'elite_vanguard', 74),
        ('final_boss', 'boss_cathedral', 96),
    ]


def _archon_card_to_enemy_intent(card_row: dict, hp_hint: int) -> dict:
    est = _estimate_card_outputs(card_row)
    card_type = str(card_row.get('family', card_row.get('type', 'skill'))).lower()
    name = str(card_row.get('name_key') or card_row.get('id') or 'archon_card')
    if est['damage'] > 0:
        dmg = max(4, min(18, int(round(est['damage'] * 0.68))))
        return {
            'id': f"{card_row.get('id')}_enemy_attack",
            'name': name,
            'intent': 'attack',
            'value': [dmg, dmg + 2],
        }
    if est['block'] > 0:
        blk = max(4, min(16, int(round(est['block'] * 0.72))))
        return {
            'id': f"{card_row.get('id')}_enemy_defend",
            'name': name,
            'intent': 'defend',
            'value': [blk, blk + 2],
        }
    if est['heal'] > 0:
        heal = max(3, min(12, est['heal']))
        return {
            'id': f"{card_row.get('id')}_enemy_heal",
            'name': name,
            'intent': 'heal',
            'stacks': heal,
        }
    if est['debuff'] > 0 or card_type in {'curse', 'ritual'}:
        return {
            'id': f"{card_row.get('id')}_enemy_debuff",
            'name': name,
            'intent': 'debuff',
            'status': 'weak' if hp_hint < 80 else 'vulnerable',
            'stacks': max(1, min(3, est['debuff'] or 1)),
        }
    return {
        'id': f"{card_row.get('id')}_enemy_channel",
        'name': name,
        'intent': 'buff',
        'status': 'ward',
        'stacks': 1,
    }


def _build_enemy_rows(cards_by_id: dict[str, dict]) -> list[dict]:
    progression = load_enemy_deck_progression()
    rows: list[dict] = []
    tier_map = {
        'weak_patrol': ('common', 'balanced', [40, 44]),
        'medium_probe': ('normal', 'control', [48, 54]),
        'medium_host': ('normal', 'control', [52, 58]),
        'advanced_choir': ('elite', 'aggro', [64, 72]),
        'advanced_sanctum': ('elite', 'bulwark', [70, 78]),
        'elite_vanguard': ('elite', 'bulwark', [82, 88]),
        'boss_cathedral': ('boss', 'control', [108, 116]),
    }
    for stage_key, stage_payload in progression.items():
        if not isinstance(stage_payload, dict):
            continue
        for deck_name, card_ids in stage_payload.items():
            tier, ai_profile, hp = tier_map.get(deck_name, ('normal', 'balanced', [50, 56]))
            enemy_deck = []
            for card_id in list(card_ids or []):
                payload = cards_by_id.get(str(card_id))
                if payload:
                    enemy_deck.append(_archon_card_to_enemy_intent(payload, hp[-1]))
            rows.append(
                {
                    'id': deck_name,
                    'name_key': f'enemy_{deck_name}',
                    'tier': tier,
                    'enemy_type': 'arconte',
                    'ai_profile': ai_profile,
                    'hp': hp,
                    'pattern': [{'intent': 'attack', 'value': [6, 8]}],
                    'enemy_deck': enemy_deck,
                    'stage': stage_key,
                }
            )
    return rows


def _drain_actions(state: CombatState, max_steps: int = 180) -> None:
    for _ in range(max_steps):
        queue_items = getattr(getattr(state, 'queue', None), 'queue', None)
        if not queue_items:
            return
        state.update(0.016)


def _choose_play_index(state: CombatState) -> int | None:
    best_idx = None
    best_score = -999999.0
    for idx, card in enumerate(list(state.hand)):
        card_cost = int(card.cost or 0)
        if card_cost > int(state.player.get('energy', 0) or 0):
            continue
        payload = {
            'cost': card_cost,
            'effects': list(getattr(card.definition, 'effects', []) or []),
        }
        est = _estimate_card_outputs(payload)
        score = est['damage'] * 1.1 + est['block'] * 0.9 + est['heal'] * 0.95 + est['buff'] * 0.55 + est['debuff'] * 0.5 - card_cost * 0.15
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx


def _run_single_stage(run_state: dict, enemy_id: str, cards_data: list[dict], enemies_data: list[dict], max_turns: int) -> tuple[bool, StageResult, dict[str, int]]:
    rng = SeededRNG(int(run_state['seed']))
    usage_counter: Counter[str] = Counter()
    with redirect_stdout(io.StringIO()):
        state = CombatState(rng, run_state, [enemy_id], cards_data=cards_data, enemies_data=enemies_data)
        enemy_hp_start = sum(int(getattr(enemy, 'max_hp', 0) or 0) for enemy in list(state.enemies or []))
        cards_played = 0
        block_generated = 0
        while state.result is None and int(state.turn or 0) <= max_turns:
            acted = False
            for _ in range(24):
                idx = _choose_play_index(state)
                if idx is None:
                    break
                card = state.hand[idx]
                before_block = int(state.player.get('block', 0) or 0)
                card_id = str(getattr(getattr(card, 'definition', None), 'id', '') or '')
                try:
                    state.play_card(idx, 0 if state.enemies else None)
                    _drain_actions(state)
                except Exception:
                    break
                after_block = int(state.player.get('block', 0) or 0)
                block_generated += max(0, after_block - before_block)
                cards_played += 1
                if card_id:
                    usage_counter[card_id] += 1
                acted = True
                if state.result is not None:
                    break
            if state.result is not None:
                break
            state.end_turn()
            _drain_actions(state)
            if not acted and not state.hand and not state.draw_pile and not state.discard_pile:
                break
        enemy_hp_end = sum(max(0, int(getattr(enemy, 'hp', 0) or 0)) for enemy in list(state.enemies or []))
        stage_result = StageResult(
            stage_key='',
            deck_name=enemy_id,
            win=(str(state.result) == 'victory'),
            turns=max(1, int(state.turn or 1)),
            damage_dealt=max(0, enemy_hp_start - enemy_hp_end),
            damage_taken=max(0, state.player_damage_taken),
            block_generated=max(0, block_generated),
            cards_played=max(0, cards_played),
            dead_cards_seen=[],
        )
        run_state['player']['hp'] = max(0, int(state.player.get('hp', 0) or 0))
    return stage_result.win, stage_result, dict(usage_counter)


def _simulate_run(archetype: str, run_index: int, cards_data: list[dict], cards_by_id: dict[str, dict], catalog_cards: dict[str, object], enemies_data: list[dict]) -> RunResult:
    run_seed = 40000 + PLAYABLE_ARCHETYPES.index(archetype) * 1000 + run_index
    deck_ids, anchor_card_id = _build_player_deck(archetype, cards_by_id, catalog_cards, run_seed)
    run_state = {
        'seed': run_seed,
        'player': {
            'hp': PLAYER_HP,
            'max_hp': PLAYER_HP,
            'block': 0,
            'energy': 3,
            'rupture': 0,
            'statuses': {},
            'harmony_current': 0,
            'harmony_max': 10,
            'harmony_ready_threshold': 6,
        },
        'deck': list(deck_ids),
        'relics': [],
    }
    total_turns = 0
    total_damage_taken = 0
    total_damage_dealt = 0
    total_block = 0
    total_cards_played = 0
    card_usage: Counter[str] = Counter()
    stages: list[StageResult] = []
    act_reached = 'act1'
    dominant_failure_reason = 'victory'
    for stage_key, deck_name, hp_gate in _stage_specs():
        max_turns = FINAL_BOSS_MAX_TURNS if stage_key == 'final_boss' else MAX_TURNS
        win, stage_result, usage = _run_single_stage(run_state, deck_name, cards_data, enemies_data, max_turns)
        stage_result.stage_key = stage_key
        stages.append(stage_result)
        card_usage.update(usage)
        total_turns += stage_result.turns
        total_damage_taken += stage_result.damage_taken
        total_damage_dealt += stage_result.damage_dealt
        total_block += stage_result.block_generated
        total_cards_played += stage_result.cards_played
        if not win:
            act_reached = stage_key
            hp_now = int(run_state['player'].get('hp', 0) or 0)
            if hp_now <= 0:
                dominant_failure_reason = 'damage_race'
            elif total_cards_played <= max(6, total_turns // 2):
                dominant_failure_reason = 'draw_fail'
            elif total_block < total_damage_taken * 0.35:
                dominant_failure_reason = 'sustain_fail'
            else:
                dominant_failure_reason = 'scaling_fail'
            break
        if int(run_state['player'].get('hp', 0) or 0) <= hp_gate // 4 and stage_key != 'final_boss':
            act_reached = stage_key
        else:
            act_reached = 'victory' if stage_key == 'final_boss' else stage_key
    played_ids = set(card_usage.keys())
    dead_cards_seen = [card_id for card_id in deck_ids if card_id not in played_ids]
    return RunResult(
        run_id=f'{archetype}_{run_index:03d}',
        archetype=archetype,
        anchor_card_id=anchor_card_id,
        win=(act_reached == 'victory'),
        act_reached=act_reached,
        turn_count=total_turns,
        damage_taken_total=total_damage_taken,
        damage_dealt_total=total_damage_dealt,
        block_generated_total=total_block,
        cards_played_total=total_cards_played,
        dead_cards_seen=dead_cards_seen,
        dominant_failure_reason=dominant_failure_reason,
        stages=stages,
        card_usage=dict(card_usage),
    )


def run(*, dry_run: bool = False):
    catalog = load_card_canon_catalog()
    cards_data = load_canon_combat_payloads()
    cards_by_id = {str(card.get('id')): card for card in cards_data if isinstance(card, dict) and card.get('id')}
    catalog_cards = {card.id: card for card in catalog.cards}
    enemies_data = _build_enemy_rows(cards_by_id)
    runs_per_archetype = DRY_RUNS_PER_ARCHETYPE if dry_run else RUNS_PER_ARCHETYPE

    all_runs: list[RunResult] = []
    per_card_stats = defaultdict(lambda: {'appearances': 0, 'plays': 0, 'wins': 0, 'damage': 0, 'block': 0, 'dead_runs': 0})

    for archetype in PLAYABLE_ARCHETYPES:
        for run_index in range(runs_per_archetype):
            result = _simulate_run(archetype, run_index, cards_data, cards_by_id, catalog_cards, enemies_data)
            all_runs.append(result)
            deck_ids, _ = _build_player_deck(archetype, cards_by_id, catalog_cards, 40000 + PLAYABLE_ARCHETYPES.index(archetype) * 1000 + run_index)
            for card_id in deck_ids:
                stat = per_card_stats[card_id]
                stat['appearances'] += 1
                if result.win:
                    stat['wins'] += 1
                if card_id in result.dead_cards_seen:
                    stat['dead_runs'] += 1
            for card_id, plays in result.card_usage.items():
                stat = per_card_stats[card_id]
                stat['plays'] += plays
                est = _estimate_card_outputs(cards_by_id[card_id])
                stat['damage'] += est['damage'] * plays
                stat['block'] += est['block'] * plays

    total_runs = len(all_runs)
    global_win_rate = sum(1 for run in all_runs if run.win) / max(1, total_runs)
    archetype_summary: dict[str, dict[str, float]] = {}
    for archetype in PLAYABLE_ARCHETYPES:
        subset = [run for run in all_runs if run.archetype == archetype]
        archetype_summary[archetype] = {
            'runs': len(subset),
            'win_rate': sum(1 for run in subset if run.win) / max(1, len(subset)),
            'average_turns': statistics.mean([run.turn_count for run in subset]) if subset else 0.0,
            'average_damage_taken': statistics.mean([run.damage_taken_total for run in subset]) if subset else 0.0,
            'average_damage_dealt': statistics.mean([run.damage_dealt_total for run in subset]) if subset else 0.0,
            'average_block_generated': statistics.mean([run.block_generated_total for run in subset]) if subset else 0.0,
            'average_dead_cards': statistics.mean([len(run.dead_cards_seen) for run in subset]) if subset else 0.0,
        }

    problem_cards = []
    for card_id, stats in per_card_stats.items():
        appearances = max(1, stats['appearances'])
        play_rate = stats['plays'] / appearances
        win_rate = stats['wins'] / appearances
        dead_rate = stats['dead_runs'] / appearances
        delta = win_rate - global_win_rate
        card = catalog_cards[card_id]
        problem_cards.append({
            'card_id': card_id,
            'faction': card.faction,
            'name': card.name,
            'play_rate': round(play_rate, 4),
            'win_rate': round(win_rate, 4),
            'delta_vs_global': round(delta, 4),
            'dead_rate': round(dead_rate, 4),
            'damage_proxy': round(stats['damage'] / appearances, 3),
            'block_proxy': round(stats['block'] / appearances, 3),
            'role': card.ai_role,
        })

    overperformers = sorted(problem_cards, key=lambda row: (row['delta_vs_global'], row['play_rate'], row['damage_proxy']), reverse=True)[:12]
    underperformers = sorted(problem_cards, key=lambda row: (row['delta_vs_global'], row['play_rate'], -row['dead_rate']))[:12]
    dead_cards = sorted(problem_cards, key=lambda row: (row['dead_rate'], -row['play_rate']), reverse=True)[:12]
    failure_reasons = Counter(run.dominant_failure_reason for run in all_runs if not run.win)

    lines = [
        'archetype_run_balance_report',
        f'dry_run={dry_run}',
        f'runs_per_archetype={runs_per_archetype}',
        f'total_runs={total_runs}',
        f'global_win_rate={global_win_rate:.4f}',
        '',
        'per_archetype_summary:',
    ]
    for archetype in PLAYABLE_ARCHETYPES:
        row = archetype_summary[archetype]
        lines.append(
            f"- {archetype}: runs={int(row['runs'])} win_rate={row['win_rate']:.4f} average_turns={row['average_turns']:.2f} average_damage_taken={row['average_damage_taken']:.2f} average_damage_dealt={row['average_damage_dealt']:.2f} average_block_generated={row['average_block_generated']:.2f} average_dead_cards={row['average_dead_cards']:.2f}"
        )

    lines.extend(['', 'failure_reasons:'])
    for key, value in failure_reasons.most_common():
        lines.append(f'- {key}: {value}')

    lines.extend(['', 'problem_cards_overperformers:'])
    for row in overperformers:
        lines.append(f"- {row['card_id']} | faction={row['faction']} | {row['name']} | role={row['role']} | win_rate={row['win_rate']:.4f} | delta={row['delta_vs_global']:+.4f} | play_rate={row['play_rate']:.4f} | damage_proxy={row['damage_proxy']:.2f}")

    lines.extend(['', 'problem_cards_underperformers:'])
    for row in underperformers:
        lines.append(f"- {row['card_id']} | faction={row['faction']} | {row['name']} | role={row['role']} | win_rate={row['win_rate']:.4f} | delta={row['delta_vs_global']:+.4f} | play_rate={row['play_rate']:.4f} | dead_rate={row['dead_rate']:.4f}")

    lines.extend(['', 'dead_card_detection:'])
    for row in dead_cards:
        lines.append(f"- {row['card_id']} | faction={row['faction']} | {row['name']} | play_rate={row['play_rate']:.4f} | dead_rate={row['dead_rate']:.4f} | block_proxy={row['block_proxy']:.2f}")

    lines.extend(['', 'sample_runs:'])
    for run in all_runs[:9]:
        lines.append(f"- {run.run_id} | archetype={run.archetype} | win={run.win} | act_reached={run.act_reached} | turns={run.turn_count} | damage_taken={run.damage_taken_total} | cards_played={run.cards_played_total} | dead_cards={len(run.dead_cards_seen)}")

    lines.extend(['', 'measurable_conclusion:'])
    lines.append('- All three playable archetypes should target a stable run win rate band near 0.45-0.65 in deterministic local tests.')
    lines.append('- Cards with high dead_rate and low play_rate are redesign candidates before manual balance tuning.')
    lines.append('- Overperformers with high delta_vs_global and high play_rate are first nerf candidates.')
    lines.append('- Underperformers with low delta_vs_global and high dead_rate are first buff/rework candidates.')

    return write_text_report(REPORT_PATH, 'chakana_studio archetype run balance', lines)
