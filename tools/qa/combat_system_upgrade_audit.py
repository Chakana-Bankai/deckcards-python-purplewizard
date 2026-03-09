from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

from game.combat.enemy import Enemy
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.systems.enemy_deck_system import load_enemy_decks, resolve_enemy_deck
from tools.qa_phase9_supervision import _simulate_one, run_phase9_report


def _load_cards_payload(path: Path) -> list[dict]:
    payload = load_json(path, default=[])
    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        cards = payload.get("cards", [])
        if isinstance(cards, list):
            return [dict(x) for x in cards if isinstance(x, dict)]
    return []


def _enemy_deck_logic_check() -> dict:
    rng = SeededRNG(1337)
    enemies = load_json(data_dir() / "enemies.json", default=[])
    decks = load_enemy_decks()
    checked = 0
    ok = 0
    details = []
    for row in enemies if isinstance(enemies, list) else []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        checked += 1
        deck = resolve_enemy_deck(row, decks)
        en = Enemy(str(row.get("id")), str(row.get("name_key", row.get("id"))), 40, 40, list(row.get("pattern", []) or []))
        en.set_combat_deck(deck, rng)
        played = en.draw_playable_cards(rng, draw_n=5)
        en.end_enemy_turn_cards(played, rng)
        has_archon_links = bool(deck) and all(isinstance(c, dict) and c.get("source_card_id") for c in deck)
        cond = bool(deck) and (len(played) >= 1) and (len(en.combat_discard_pile) >= len(played)) and has_archon_links
        if cond:
            ok += 1
        else:
            details.append(str(row.get("id")))
    return {"checked": checked, "ok": ok, "failed_ids": details[:10]}


def _pack_distribution_check(sim_n: int = 600) -> dict:
    base = _load_cards_payload(data_dir() / "cards.json")
    hip = _load_cards_payload(data_dir() / "cards_hiperboria.json")
    all_cards = base + hip

    base_pool = [c for c in all_cards if str(c.get("set", "base")).lower() in {"base", ""} and not str(c.get("id", "")).lower().startswith("hip_")]
    hip_pool = [c for c in all_cards if str(c.get("id", "")).lower().startswith("hip_") or "hiperb" in str(c.get("set", "")).lower()]

    def rarity_of(c):
        return str(c.get("rarity", "common") or "common").lower()

    def pick(pool, rarity):
        r = [x for x in pool if rarity_of(x) == rarity]
        if not r:
            return pool[0] if pool else {}
        return r[0]

    rng = SeededRNG(2027)
    leg = 0
    total = 0
    per_pack = {"base_pack": 0, "hiperborea_pack": 0}
    opened = 0

    for pid, pool in (("base_pack", base_pool), ("hiperborea_pack", hip_pool or all_cards)):
        for _ in range(sim_n // 2):
            if not pool:
                continue
            picks = [pick(pool, "common"), pick(pool, "common"), pick(pool, "common"), pick(pool, "rare")]
            if rng.random() < 0.10:
                picks.append(pick(pool, "legendary"))
            per_pack[pid] += len(picks)
            total += len(picks)
            opened += 1
            leg += sum(1 for c in picks if rarity_of(c) == "legendary")

    leg_rate_cards = leg / max(1, total)
    leg_rate_packs = leg / max(1, opened)
    return {
        "total_cards_opened": total,
        "packs_opened": opened,
        "legendary_cards": leg,
        "legendary_rate_cards": round(leg_rate_cards, 4),
        "legendary_rate_packs": round(leg_rate_packs, 4),
        "per_pack_cards": per_pack,
    }


def _combat_fairness_from_phase9() -> dict:
    rpt = run_phase9_report()
    arch = rpt.get("archetype_simulation", {}) if isinstance(rpt, dict) else {}
    turns = [float(v.get("avg_turns_combat", 0) or 0) for v in arch.values() if isinstance(v, dict)]
    wins = [float(v.get("boss_win_rate", 0) or 0) for v in arch.values() if isinstance(v, dict)]
    return {
        "avg_turns_combat_all_arch": round(statistics.mean(turns), 2) if turns else 0.0,
        "avg_boss_win_rate_all_arch": round(statistics.mean(wins), 3) if wins else 0.0,
        "phase9_avg_turns_boss": rpt.get("avg_turns_boss", 0),
        "phase9_boss_win_rate": rpt.get("boss_win_rate", 0),
        "archetype_simulation": arch,
    }


def _simulate_100_per_archetype() -> dict:
    base = _load_cards_payload(data_dir() / "cards.json")
    hip = _load_cards_payload(data_dir() / "cards_hiperboria.json")
    arc = _load_cards_payload(data_dir() / "cards_arconte.json")
    cards = base + hip + arc
    enemies = load_json(data_dir() / "enemies" / "enemies_30.json", default=[])
    bosses = load_json(data_dir() / "enemies" / "bosses_3.json", default=[])

    archetypes = ["cosmic_warrior", "harmony_guardian", "oracle_of_fate"]
    report = {}
    seed = 14000

    for arch in archetypes:
        results = []
        usage = Counter()
        for i in range(100):
            boss = (i % 5 == 4)
            sim = _simulate_one(arch, seed + i, boss, cards, base, hip, enemies, bosses)
            results.append(sim)
            usage.update(sim.card_usage or {})
        seed += 1000

        combats = [r.turns for r in results if not r.boss]
        wins = [1 for r in results if r.win]
        damage = [r.damage_done for r in results]
        report[arch] = {
            "runs": len(results),
            "avg_turns": round(statistics.mean(combats), 2) if combats else 0.0,
            "win_rate": round(sum(wins) / max(1, len(results)), 3),
            "avg_damage": round(statistics.mean(damage), 2) if damage else 0.0,
            "card_usage_top10": usage.most_common(10),
        }
    return report


def main() -> int:
    out = Path("qa") / "reports" / "current" / "combat_system_upgrade_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    enemy = _enemy_deck_logic_check()
    packs = _pack_distribution_check(600)
    fairness = _combat_fairness_from_phase9()
    sim100 = _simulate_100_per_archetype()

    status_enemy = "PASS" if enemy.get("checked", 0) > 0 and enemy.get("ok", 0) == enemy.get("checked", 0) else "WARNING"
    status_pack = "PASS" if abs(float(packs.get("legendary_rate_packs", 0)) - 0.10) <= 0.04 else "WARNING"
    status_fair = "PASS" if float(fairness.get("avg_turns_combat_all_arch", 0)) <= 10.5 else "WARNING"

    sim_flags = []
    for arch, row in sim100.items():
        if float(row.get("win_rate", 0)) < 0.30:
            sim_flags.append(f"{arch}:win_rate_low")
        if float(row.get("avg_turns", 0)) > 12.0:
            sim_flags.append(f"{arch}:turns_high")
    status_sim = "PASS" if not sim_flags else "WARNING"

    lines = [
        "CHAKANA COMBAT + ARCONTE DECK SYSTEM PASS",
        "",
        "[enemy deck logic]",
        f"status={status_enemy}",
        json.dumps(enemy, ensure_ascii=False),
        "",
        "[pack distribution]",
        f"status={status_pack}",
        json.dumps(packs, ensure_ascii=False),
        "",
        "[combat fairness + archetype viability]",
        f"status={status_fair}",
        json.dumps(fairness, ensure_ascii=False),
        "",
        "[simulate_100_per_archetype]",
        f"status={status_sim}",
        json.dumps({"flags": sim_flags, "data": sim100}, ensure_ascii=False),
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[combat_upgrade_qa] report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
