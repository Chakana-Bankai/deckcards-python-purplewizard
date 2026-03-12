from __future__ import annotations

import io
import json
import random
import statistics
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from dataclasses import dataclass, field

from game.cards.card_dna_registry import load_card_dna_catalog, load_combat_card_payloads
from game.combat.combat_state import CombatState
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from tools.lib.common import ROOT, write_text_report

SIM_COUNT = 1000
BOSS_RATE = 0.18
NORMAL_MAX_TURNS = 20
BOSS_MAX_TURNS = 28
ACTION_DRAIN_STEPS = 96
REPORT_PATH = ROOT / 'reports' / 'qa' / 'card_balance_1000_report.txt'


@dataclass
class SimResult:
    seed: int
    card_anchor: str
    archetype: str
    deck_archetype: str
    boss: bool
    win: bool
    turns: int
    damage_done: int
    player_damage_taken: int
    deck: list[str] = field(default_factory=list)
    card_usage: dict[str, int] = field(default_factory=dict)


EFFECT_ALIAS = {
    'block': 'shield',
    'gain_block': 'shield',
    'gain_mana': 'buff',
    'gain_mana_next_turn': 'buff',
    'apply_status': 'debuff',
    'damage_plus_rupture': 'damage',
}


def _normalize_effect_type(effect_type: str) -> str:
    key = str(effect_type or '').strip().lower()
    return EFFECT_ALIAS.get(key, key or 'unknown')


def _estimate_card_value(card: dict) -> dict[str, int]:
    out = {
        'damage': 0,
        'shield': 0,
        'heal': 0,
        'buff': 0,
        'debuff': 0,
        'draw': 0,
        'summon': 0,
        'ritual': 0,
    }
    for effect in list(card.get('effects', []) or []):
        if not isinstance(effect, dict):
            continue
        eff_type = _normalize_effect_type(effect.get('type', ''))
        amount = int(effect.get('amount', effect.get('base', 0)) or 0)
        if eff_type in out:
            out[eff_type] += amount if amount > 0 else 1
        elif eff_type in {'scry', 'retain', 'copy_last_played', 'copy_next_played'}:
            out['buff'] += max(1, amount)
        elif eff_type in {'break', 'vulnerable', 'weak', 'frail'}:
            out['debuff'] += max(1, amount)
    return out


def _normalize_effects_for_sim(cards: list[dict]) -> list[dict]:
    out = []
    for card in cards:
        row = dict(card)
        effects = []
        for effect in list(row.get('effects', []) or []):
            if not isinstance(effect, dict):
                continue
            cooked = dict(effect)
            if str(cooked.get('type', '')).lower() == 'damage_plus_rupture':
                cooked.setdefault('base', int(cooked.get('amount', 0) or 0))
                cooked.setdefault('per_rupture', 1)
            effects.append(cooked)
        row['effects'] = effects
        out.append(row)
    return out


def _drain_actions(state: CombatState, max_steps: int = ACTION_DRAIN_STEPS) -> None:
    steps = 0
    while steps < max_steps and getattr(getattr(state, 'queue', None), 'queue', []):
        state.update(0.016)
        steps += 1


def _pick_enemy(enemies: list[dict], bosses: list[dict], rng: random.Random, boss: bool) -> tuple[str, int]:
    if boss:
        pool = [row for row in bosses if isinstance(row, dict) and row.get('id')]
        if not pool:
            pool = [row for row in enemies if str(row.get('tier', '')).lower() == 'boss' and row.get('id')]
        if pool:
            row = rng.choice(pool)
            hpv = row.get('hp', [160, 200])
            hp = int((hpv[0] + hpv[-1]) / 2) if isinstance(hpv, list) else int(hpv or 180)
            return str(row.get('id')), max(1, hp)
    pool = [row for row in enemies if isinstance(row, dict) and row.get('id')]
    row = rng.choice(pool)
    hpv = row.get('hp', [40, 60])
    hp = int((hpv[0] + hpv[-1]) / 2) if isinstance(hpv, list) else int(hpv or 50)
    return str(row.get('id')), max(1, hp)


def _build_deck(anchor_card_id: str, cards_by_id: dict[str, dict], catalog_cards: dict, rng: random.Random) -> list[str]:
    anchor_entry = catalog_cards[anchor_card_id]
    visual_archetype = anchor_entry.visual.archetype
    deck_archetype = anchor_entry.gameplay.deck_archetype or visual_archetype
    role = anchor_entry.gameplay.gameplay_role
    same_arch = [cid for cid, entry in catalog_cards.items() if (entry.gameplay.deck_archetype or entry.visual.archetype) == deck_archetype and cid != anchor_card_id]
    support_pool = [cid for cid, entry in catalog_cards.items() if (entry.gameplay.deck_archetype or entry.visual.archetype) == deck_archetype and entry.gameplay.gameplay_role in {'support', 'controller', 'tank', 'summoner'} and cid != anchor_card_id]
    same_role = [cid for cid, entry in catalog_cards.items() if (entry.gameplay.deck_archetype or entry.visual.archetype) == deck_archetype and entry.gameplay.gameplay_role == role and cid != anchor_card_id]

    rng.shuffle(same_arch)
    rng.shuffle(support_pool)
    rng.shuffle(same_role)

    picked = [anchor_card_id]
    for pool, take in ((same_arch, 11), (same_role, 4), (support_pool, 4)):
        for cid in pool:
            if cid in picked:
                continue
            picked.append(cid)
            if len([x for x in picked if x in pool or x == anchor_card_id]) >= take + 1 and pool is same_arch:
                pass
            if len(picked) >= 20:
                break
        if len(picked) >= 20:
            break

    if len(picked) < 20:
        rest = [cid for cid in cards_by_id.keys() if cid not in picked]
        rng.shuffle(rest)
        picked.extend(rest[: 20 - len(picked)])
    return picked[:20]


def _simulate_one(seed: int, anchor_card_id: str, cards_all: list[dict], cards_by_id: dict[str, dict], catalog_cards: dict, enemies: list[dict], bosses: list[dict]) -> SimResult:
    rng_py = random.Random(seed)
    deck = _build_deck(anchor_card_id, cards_by_id, catalog_cards, rng_py)
    boss = rng_py.random() < BOSS_RATE
    enemy_id, enemy_hp = _pick_enemy(enemies, bosses, rng_py, boss)

    run_state = {
        'player': {
            'hp': 70,
            'max_hp': 70,
            'block': 0,
            'energy': 3,
            'rupture': 0,
            'statuses': {},
            'harmony_current': 0,
            'harmony_max': 10,
            'harmony_ready_threshold': 6,
        },
        'deck': list(deck),
        'relics': [],
    }
    rng = SeededRNG(seed)
    merged_enemies = [dict(row) for row in enemies if isinstance(row, dict)] + [dict(row) for row in bosses if isinstance(row, dict)]
    for row in merged_enemies:
        if str(row.get('id')) == enemy_id:
            row['hp'] = [enemy_hp, enemy_hp]

    state = CombatState(rng, run_state, [enemy_id], cards_data=cards_all, enemies_data=merged_enemies)
    usage_counter: Counter[str] = Counter()

    start_enemy_hp = sum(int(getattr(enemy, 'max_hp', 0) or 0) for enemy in list(state.enemies or []))
    start_player_hp = int(state.player.get('hp', 0) or 0)
    max_turns = BOSS_MAX_TURNS if boss else NORMAL_MAX_TURNS
    while state.result is None and int(state.turn) <= max_turns:
        acted = False
        safety = 24
        while safety > 0 and state.result is None:
            safety -= 1
            playable = []
            for idx, card in enumerate(list(state.hand)):
                if int(card.cost or 0) > int(state.player.get('energy', 0) or 0):
                    continue
                damage = 0
                shield = 0
                buff = 0
                for effect in list(getattr(card.definition, 'effects', []) or []):
                    if not isinstance(effect, dict):
                        continue
                    eff_type = _normalize_effect_type(effect.get('type', ''))
                    amount = int(effect.get('amount', effect.get('base', 0)) or 0)
                    if eff_type == 'damage':
                        damage += amount
                    elif eff_type == 'shield':
                        shield += amount
                    elif eff_type in {'buff', 'heal', 'draw'}:
                        buff += max(1, amount)
                playable.append((damage, shield, buff, -int(card.cost or 0), idx))
            if not playable:
                break
            playable.sort(reverse=True)
            _, _, _, _, idx = playable[0]
            try:
                card_id = str(getattr(getattr(state.hand[idx], 'definition', None), 'id', '') or '')
                state.play_card(idx, 0)
                if card_id:
                    usage_counter[card_id] += 1
                _drain_actions(state)
                acted = True
            except Exception:
                break
        if state.result is not None:
            break
        state.end_turn()
        _drain_actions(state)
        if not acted and not state.hand and not state.draw_pile and not state.discard_pile:
            break

    end_enemy_hp = sum(max(0, int(getattr(enemy, 'hp', 0) or 0)) for enemy in list(state.enemies or []))
    return SimResult(
        seed=seed,
        card_anchor=anchor_card_id,
        archetype=catalog_cards[anchor_card_id].visual.archetype,
        deck_archetype=(catalog_cards[anchor_card_id].gameplay.deck_archetype or catalog_cards[anchor_card_id].visual.archetype),
        boss=boss,
        win=(str(state.result) == 'victory'),
        turns=max(1, int(state.turn or 1)),
        damage_done=max(0, start_enemy_hp - end_enemy_hp),
        player_damage_taken=max(0, start_player_hp - int(state.player.get('hp', 0) or 0)),
        deck=list(deck),
        card_usage=dict(usage_counter),
    )


def run(*, dry_run: bool = False) -> Path:
    catalog = load_card_dna_catalog()
    catalog_cards = catalog.cards
    combat_payloads = _normalize_effects_for_sim(load_combat_card_payloads())
    cards_by_id = {str(card.get('id')): card for card in combat_payloads if isinstance(card, dict) and card.get('id')}
    enemies = load_json(data_dir() / 'enemies' / 'enemies_30.json', default=[])
    bosses = load_json(data_dir() / 'enemies' / 'bosses_3.json', default=[])

    seeds = list(range(12000, 12000 + (32 if dry_run else SIM_COUNT)))
    card_ids = list(catalog_cards.keys())
    runs: list[SimResult] = []
    per_card = defaultdict(lambda: {
        'appearances': 0,
        'wins_when_present': 0,
        'turns_total': 0,
        'plays': 0,
        'damage_est': 0,
        'shield_est': 0,
        'heal_est': 0,
        'buff_est': 0,
        'debuff_est': 0,
        'draw_est': 0,
        'summon_est': 0,
        'ritual_est': 0,
        'boss_appearances': 0,
        'boss_wins': 0,
    })
    effect_presence = Counter()
    effect_played = Counter()

    for idx, seed in enumerate(seeds):
        anchor_card_id = card_ids[idx % len(card_ids)]
        with redirect_stdout(io.StringIO()):
            result = _simulate_one(seed, anchor_card_id, combat_payloads, cards_by_id, catalog_cards, enemies, bosses)
        runs.append(result)
        for card_id in result.deck:
            row = per_card[card_id]
            row['appearances'] += 1
            row['turns_total'] += result.turns
            if result.win:
                row['wins_when_present'] += 1
            if result.boss:
                row['boss_appearances'] += 1
                if result.win:
                    row['boss_wins'] += 1
            for effect in catalog_cards[card_id].gameplay.action_types:
                effect_presence[str(effect)] += 1
        for card_id, plays in result.card_usage.items():
            row = per_card[card_id]
            row['plays'] += plays
            estimate = _estimate_card_value(cards_by_id[card_id])
            row['damage_est'] += estimate['damage'] * plays
            row['shield_est'] += estimate['shield'] * plays
            row['heal_est'] += estimate['heal'] * plays
            row['buff_est'] += estimate['buff'] * plays
            row['debuff_est'] += estimate['debuff'] * plays
            row['draw_est'] += estimate['draw'] * plays
            row['summon_est'] += estimate['summon'] * plays
            row['ritual_est'] += estimate['ritual'] * plays
            for effect in catalog_cards[card_id].gameplay.action_types:
                effect_played[str(effect)] += plays

    total_runs = len(runs)
    wins = sum(1 for row in runs if row.win)
    boss_runs = [row for row in runs if row.boss]
    global_win_rate = wins / max(1, total_runs)
    avg_turns = statistics.mean([row.turns for row in runs]) if runs else 0.0
    avg_damage_done = statistics.mean([row.damage_done for row in runs]) if runs else 0.0
    avg_player_damage = statistics.mean([row.player_damage_taken for row in runs]) if runs else 0.0

    scored_cards = []
    for card_id, stats in per_card.items():
        appearances = max(1, stats['appearances'])
        win_rate = stats['wins_when_present'] / appearances
        play_rate = stats['plays'] / appearances
        avg_turns_present = stats['turns_total'] / appearances
        pressure_score = (
            stats['damage_est'] * 1.00
            + stats['shield_est'] * 0.72
            + stats['heal_est'] * 0.85
            + stats['buff_est'] * 0.55
            + stats['debuff_est'] * 0.60
            + stats['draw_est'] * 0.95
            + stats['summon_est'] * 1.15
            + stats['ritual_est'] * 0.80
        ) / appearances
        card = catalog_cards[card_id]
        scored_cards.append({
            'card_id': card_id,
            'name': card.lore.name,
            'archetype': card.visual.archetype,
            'deck_archetype': card.gameplay.deck_archetype or card.visual.archetype,
            'role': card.gameplay.gameplay_role,
            'rarity': card.rarity,
            'appearances': appearances,
            'win_rate_when_present': round(win_rate, 4),
            'play_rate': round(play_rate, 4),
            'avg_turns_when_present': round(avg_turns_present, 3),
            'pressure_score': round(pressure_score, 3),
            'delta_vs_global': round(win_rate - global_win_rate, 4),
            'boss_win_rate': round(stats['boss_wins'] / max(1, stats['boss_appearances']), 4),
            'action_types': list(card.gameplay.action_types),
        })

    appearance_values = [row['appearances'] for row in scored_cards]
    stable_cards = [row for row in scored_cards if row['appearances'] >= max(3, total_runs // 40)]
    archetype_summary = defaultdict(lambda: {'cards': 0, 'appearances': 0, 'win_rate_sum': 0.0, 'play_rate_sum': 0.0, 'pressure_sum': 0.0})
    for row in scored_cards:
        bucket = archetype_summary[row['deck_archetype']]
        bucket['cards'] += 1
        bucket['appearances'] += row['appearances']
        bucket['win_rate_sum'] += row['win_rate_when_present']
        bucket['play_rate_sum'] += row['play_rate']
        bucket['pressure_sum'] += row['pressure_score']
    overperformers = sorted(stable_cards, key=lambda row: (row['delta_vs_global'], row['pressure_score'], row['play_rate']), reverse=True)[:12]
    underperformers = sorted(stable_cards, key=lambda row: (row['delta_vs_global'], row['pressure_score'], row['play_rate']))[:12]
    low_use = sorted(stable_cards, key=lambda row: (row['play_rate'], row['pressure_score']))[:12]

    lines = [
        'card_balance_1000_report',
        f'dry_run={dry_run}',
        f'simulations={total_runs}',
        f'unique_cards={len(catalog_cards)}',
        f'global_win_rate={global_win_rate:.4f}',
        f'avg_turns={avg_turns:.2f}',
        f'avg_enemy_damage_done={avg_damage_done:.2f}',
        f'avg_player_damage_taken={avg_player_damage:.2f}',
        f'boss_win_rate={sum(1 for row in boss_runs if row.win) / max(1, len(boss_runs)):.4f}',
        f'min_card_appearances={min(appearance_values) if appearance_values else 0}',
        f'max_card_appearances={max(appearance_values) if appearance_values else 0}',
        f'median_card_appearances={statistics.median(appearance_values) if appearance_values else 0}',
        '',
        'archetype_summary:',
    ]
    for archetype, bucket in sorted(archetype_summary.items()):
        cards_n = max(1, bucket['cards'])
        lines.append(
            f"- {archetype}: cards={bucket['cards']} avg_win_rate={bucket['win_rate_sum']/cards_n:.4f} avg_play_rate={bucket['play_rate_sum']/cards_n:.3f} avg_pressure={bucket['pressure_sum']/cards_n:.2f}"
        )

    lines.extend(['', 'top_effect_presence:'])
    for effect, count in effect_presence.most_common(12):
        lines.append(f'- {effect}: present={count} played={effect_played.get(effect, 0)}')

    lines.extend(['', 'overperformers:'])
    for row in overperformers:
        lines.append(f"- {row['card_id']} | visual={row['archetype']} | deck={row['deck_archetype']} | {row['name']} | role={row['role']} | win_rate={row['win_rate_when_present']:.4f} | delta={row['delta_vs_global']:+.4f} | play_rate={row['play_rate']:.3f} | pressure={row['pressure_score']:.2f}")

    lines.extend(['', 'underperformers:'])
    for row in underperformers:
        lines.append(f"- {row['card_id']} | visual={row['archetype']} | deck={row['deck_archetype']} | {row['name']} | role={row['role']} | win_rate={row['win_rate_when_present']:.4f} | delta={row['delta_vs_global']:+.4f} | play_rate={row['play_rate']:.3f} | pressure={row['pressure_score']:.2f}")

    lines.extend(['', 'low_use_cards:'])
    for row in low_use:
        lines.append(f"- {row['card_id']} | visual={row['archetype']} | deck={row['deck_archetype']} | {row['name']} | role={row['role']} | play_rate={row['play_rate']:.3f} | action_types={','.join(row['action_types'])}")

    lines.extend(['', 'measurable_conclusion:'])
    lines.append('- Cards with delta_vs_global >= +0.080 and pressure_score above median are candidates for nerf review.')
    lines.append('- Cards with delta_vs_global <= -0.080 and play_rate <= 0.120 are candidates for buff or redesign review.')
    lines.append('- Effects with high presence but low played count indicate dead-text or low-activation design.')
    lines.append('- First patch target should come from the intersection of overperformers/underperformers with stable appearance counts.')

    lines.extend(['', 'sample_card_metrics:'])
    for row in sorted(stable_cards, key=lambda item: (-item['appearances'], item['card_id']))[:24]:
        lines.append(f"- {row['card_id']} | visual={row['archetype']} | deck={row['deck_archetype']} | appear={row['appearances']} | win_rate={row['win_rate_when_present']:.4f} | play_rate={row['play_rate']:.3f} | pressure={row['pressure_score']:.2f}")

    return write_text_report(REPORT_PATH, 'chakana_studio balance qa 1000', lines)
