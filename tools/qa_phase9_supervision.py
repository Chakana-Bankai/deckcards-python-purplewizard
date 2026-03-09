from __future__ import annotations

import hashlib
import io
import json
import random
import statistics
import sys
from contextlib import redirect_stdout
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.combat.combat_state import CombatState
from game.core.paths import assets_dir, data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.main import MAP_TEMPLATE
from game.ui.system.icons import icon_for_effect


@dataclass
class SimResult:
    archetype: str
    boss: bool
    win: bool
    turns: int
    damage_done: int
    card_usage: dict[str, int] = field(default_factory=dict)


def _norm_card(c: dict, set_id: str) -> dict:
    row = dict(c)
    row.setdefault("set", set_id)
    row.setdefault("name", row.get("name_key", row.get("id", "")))
    row.setdefault("type", row.get("role", ""))
    row.setdefault("lore", row.get("lore_text", ""))
    row.setdefault("art", row.get("artwork", row.get("id", "")))
    return row


def _load_sets() -> tuple[list[dict], list[dict], list[dict]]:
    base_raw = load_json(data_dir() / "cards.json", default=[])
    hip_raw = load_json(data_dir() / "cards_hiperboria.json", default={})

    base = [_norm_card(c, "base") for c in (base_raw if isinstance(base_raw, list) else []) if isinstance(c, dict)]
    hip_cards = []
    if isinstance(hip_raw, dict):
        hip_cards = [_norm_card(c, "hiperboria") for c in list(hip_raw.get("cards", []) or []) if isinstance(c, dict)]

    combined = [dict(c) for c in base] + [dict(c) for c in hip_cards]
    return base, hip_cards, combined


def _card_required_issues(cards: list[dict]) -> list[str]:
    issues = []
    req = ("id", "name", "set", "archetype", "type", "cost", "effects", "lore", "art")
    for c in cards:
        cid = str(c.get("id", "?"))
        for k in req:
            v = c.get(k)
            if k == "effects":
                if not isinstance(v, list) or not v:
                    issues.append(f"{cid}:missing_{k}")
            elif k == "cost":
                try:
                    int(v)
                except Exception:
                    issues.append(f"{cid}:invalid_cost")
            else:
                if not str(v or "").strip():
                    issues.append(f"{cid}:missing_{k}")
    return issues


def _duplicate_logic(cards: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        effects = []
        for e in list(c.get("effects", []) or []):
            if isinstance(e, dict):
                effects.append((str(e.get("type", "")).lower(), int(e.get("amount", 0) or 0)))
        sig = (
            str(c.get("set", "")),
            str(c.get("archetype", "")),
            int(c.get("cost", 0) or 0),
            tuple(sorted(set(effects))),
            tuple(sorted(str(t).lower() for t in list(c.get("tags", []) or []))),
        )
        groups[str(sig)].append(str(c.get("id", "")))
    return {k: v for k, v in groups.items() if len(v) > 1}


def _hash_file(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        while True:
            b = f.read(8192)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _visual_duplicates(cards: list[dict]) -> tuple[int, int]:
    cards_dir = assets_dir() / "sprites" / "cards"
    missing = 0
    by_hash: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        aid = str(c.get("art", c.get("id", "")) or c.get("id", ""))
        p = cards_dir / f"{aid}.png"
        if not p.exists():
            missing += 1
            continue
        by_hash[_hash_file(p)].append(str(c.get("id", "")))
    dup = sum(len(v) - 1 for v in by_hash.values() if len(v) > 1)
    return dup, missing


def _icon_issues(cards: list[dict]) -> tuple[int, dict[str, int]]:
    missing = 0
    by_type = Counter()
    for c in cards:
        for e in list(c.get("effects", []) or []):
            if not isinstance(e, dict):
                continue
            et = str(e.get("type", "")).strip().lower()
            if not et:
                continue
            icon = icon_for_effect(et)
            if icon == "unknown":
                missing += 1
                by_type[et] += 1
    return missing, dict(by_type)


def _text_overflow_count(cards: list[dict]) -> int:
    pygame.font.init()
    font = pygame.font.Font(None, 20)
    lore_font = pygame.font.Font(None, 18)
    # Approximate safe widths for normal card layout.
    eff_w = 280
    lore_w = 280
    bad = 0
    for c in cards:
        eff = str(c.get("effect_text", c.get("text_key", "")) or "")
        lore = str(c.get("lore", c.get("lore_text", "")) or "")
        if eff and font.size(eff)[0] > eff_w * 2:
            bad += 1
        if lore and lore_font.size(lore)[0] > lore_w * 2:
            bad += 1
    return bad


def _make_deck(archetype: str, base: list[dict], hip: list[dict], rng: random.Random) -> list[str]:
    b = [c for c in base if str(c.get("archetype", "")).lower() == archetype]
    h = [c for c in hip if str(c.get("archetype", "")).lower() == archetype]
    rng.shuffle(b)
    rng.shuffle(h)
    picked = [str(c.get("id")) for c in (b[:12] + h[:8]) if c.get("id")]
    pool = [str(c.get("id")) for c in (b + h) if c.get("id")]
    while len(picked) < 20 and pool:
        picked.append(rng.choice(pool))
    return picked[:20]


def _pick_enemy(enemies: list[dict], bosses: list[dict], rng: random.Random, boss: bool) -> tuple[str, int]:
    if boss:
        b = [e for e in bosses if isinstance(e, dict) and e.get("id")]
        if not b:
            b = [e for e in enemies if str(e.get("tier", "")).lower() == "boss" and e.get("id")]
        if b:
            row = rng.choice(b)
            hpv = row.get("hp", [160, 200])
            hp = int((hpv[0] + hpv[-1]) / 2) if isinstance(hpv, list) else int(hpv or 180)
            return str(row.get("id")), max(1, hp)
    normal = [e for e in enemies if str(e.get("tier", "common")).lower() in {"common", "normal", "elite"} and e.get("id")]
    if not normal:
        normal = [e for e in enemies if e.get("id")]
    row = rng.choice(normal)
    hpv = row.get("hp", [40, 60])
    hp = int((hpv[0] + hpv[-1]) / 2) if isinstance(hpv, list) else int(hpv or 50)
    return str(row.get("id")), max(1, hp)




def _normalize_effects_for_sim(cards: list[dict]) -> list[dict]:
    out = []
    for c in cards:
        row = dict(c)
        effs = []
        for e in list(row.get("effects", []) or []):
            if not isinstance(e, dict):
                continue
            ee = dict(e)
            et = str(ee.get("type", "")).lower()
            if et == "damage_plus_rupture":
                if "base" not in ee:
                    ee["base"] = int(ee.get("amount", 0) or 0)
                if "per_rupture" not in ee:
                    ee["per_rupture"] = 1
            effs.append(ee)
        row["effects"] = effs
        out.append(row)
    return out


def _drain_actions(st: CombatState, max_steps: int = 96) -> None:
    """Resolve queued combat actions for offline simulations."""
    steps = 0
    while steps < max_steps and getattr(getattr(st, "queue", None), "queue", []):
        st.update(0.016)
        steps += 1


def _simulate_one(archetype: str, seed: int, boss: bool, cards_all: list[dict], base: list[dict], hip: list[dict], enemies: list[dict], bosses: list[dict]) -> SimResult:
    rng_py = random.Random(seed)
    deck = _make_deck(archetype, base, hip, rng_py)
    enemy_id, enemy_hp = _pick_enemy(enemies, bosses, rng_py, boss)

    run_state = {
        "player": {
            "hp": 70,
            "max_hp": 70,
            "block": 0,
            "energy": 3,
            "rupture": 0,
            "statuses": {},
            "harmony_current": 0,
            "harmony_max": 10,
            "harmony_ready_threshold": 6,
        },
        "deck": list(deck),
        "relics": [],
    }
    rng = SeededRNG(seed)
    merged_enemies = [dict(e) for e in enemies if isinstance(e, dict)] + [dict(e) for e in bosses if isinstance(e, dict)]
    for e in merged_enemies:
        if str(e.get("id")) == enemy_id:
            e["hp"] = [enemy_hp, enemy_hp]

    sim_cards = _normalize_effects_for_sim(cards_all)
    st = CombatState(rng, run_state, [enemy_id], cards_data=sim_cards, enemies_data=merged_enemies)
    usage_counter: Counter = Counter()

    start_enemy_hp = sum(int(getattr(e, "max_hp", 0) or 0) for e in list(st.enemies or []))
    max_turns = 36 if boss else 20
    while st.result is None and int(st.turn) <= max_turns:
        acted = False
        safety = 24
        while safety > 0 and st.result is None:
            safety -= 1
            playable = []
            for i, card in enumerate(list(st.hand)):
                if int(card.cost or 0) <= int(st.player.get("energy", 0) or 0):
                    dmg = 0
                    for eff in list(getattr(card.definition, "effects", []) or []):
                        if isinstance(eff, dict) and str(eff.get("type", "")).lower() in {"damage", "damage_plus_rupture"}:
                            dmg += int(eff.get("amount", 0) or 0)
                    playable.append((dmg, -int(card.cost or 0), i))
            if not playable:
                break
            playable.sort(reverse=True)
            _, _, idx = playable[0]
            try:
                card_id = ""
                try:
                    card_id = str(getattr(getattr(st.hand[idx], "definition", None), "id", "") or "")
                except Exception:
                    card_id = ""
                st.play_card(idx, 0)
                if card_id:
                    usage_counter[card_id] += 1
                _drain_actions(st)
                acted = True
            except Exception:
                # QA simulation must continue even with malformed legacy effect payloads.
                break
        if st.result is not None:
            break
        st.end_turn()
        _drain_actions(st)
        if not acted and not st.hand and not st.draw_pile and not st.discard_pile:
            break

    end_enemy_hp = sum(max(0, int(getattr(e, "hp", 0) or 0)) for e in list(st.enemies or []))
    dmg_done = max(0, start_enemy_hp - end_enemy_hp)
    return SimResult(
        archetype=archetype,
        boss=bool(boss),
        win=(str(st.result) == "victory"),
        turns=max(1, int(st.turn or 1)),
        damage_done=int(dmg_done),
        card_usage=dict(usage_counter),
    )


def _map_distribution() -> dict:
    counts = Counter()
    for col in list(MAP_TEMPLATE or []):
        types = list(col.get("types", []) or [])
        for t in types:
            counts[str(t).lower()] += 1
    combats = counts.get("combat", 0) + counts.get("challenge", 0) + counts.get("elite", 0)
    return {
        "combats_like": int(combats),
        "events": int(counts.get("event", 0)),
        "relic": int(counts.get("relic", 0)),
        "shop": int(counts.get("shop", 0)),
        "boss": int(counts.get("boss", 0)),
        "sanctuary": int(counts.get("sanctuary", 0)),
        "raw": dict(counts),
    }


def _localization_issues() -> dict:
    es = load_json(data_dir() / "lang" / "es.json", default={})
    en = load_json(data_dir() / "lang" / "en.json", default={})
    if not isinstance(es, dict):
        es = {}
    if not isinstance(en, dict):
        en = {}

    mojibake = [k for k, v in es.items() if isinstance(v, str) and ("Ã" in v or "�" in v)]
    same_as_en = [k for k, v in es.items() if isinstance(v, str) and k in en and isinstance(en[k], str) and v.strip() == en[k].strip() and len(v.strip()) > 3]
    return {"mojibake": len(mojibake), "same_as_en": len(same_as_en), "keys_mojibake": mojibake[:12], "keys_same": same_as_en[:12]}


def _audio_intro_checks() -> dict:
    bgm = load_json(data_dir() / "bgm_manifest.json", default={})
    am = load_json((Path(__file__).resolve().parents[1] / "game" / "audio" / "audio_manifest.json"), default={})
    studio_manifest = load_json(data_dir() / "studio_intro_manifest.json", default={})

    required_ctx = {"menu", "shop", "boss", "victory"}
    bgm_keys = set(bgm.keys()) if isinstance(bgm, dict) else set()

    stingers_dir = Path(__file__).resolve().parents[1] / "game" / "audio" / "generated" / "stingers"
    stingers = {p.stem for p in stingers_dir.glob("*.wav")}
    required_stingers = {"combat_start", "boss_reveal", "harmony_ready", "seal_ready", "relic_gain", "pack_open", "level_up", "victory", "defeat"}

    intro_path = Path(__file__).resolve().parents[1] / "game" / "ui" / "screens" / "studio_intro.py"
    intro_txt = intro_path.read_text(encoding="utf-8", errors="replace") if intro_path.exists() else ""

    return {
        "bgm_context_ok": sorted(required_ctx.intersection(bgm_keys)),
        "bgm_context_missing": sorted(required_ctx - bgm_keys),
        "stingers_ok": sorted(required_stingers.intersection(stingers)),
        "stingers_missing": sorted(required_stingers - stingers),
        "audio_manifest_exists": isinstance(am, dict) and bool(am),
        "intro_duration": float(studio_manifest.get("duration", 0) or 0),
        "intro_has_logo": "CHAKANA STUDIO" in intro_txt,
        "intro_cosmic_bg": "surface.fill((2, 2, 4))" in intro_txt,
    }


def run_phase9_report() -> dict:
    pygame.font.init()

    base, hip, cards = _load_sets()
    enemies = load_json(data_dir() / "enemies" / "enemies_30.json", default=[])
    bosses = load_json(data_dir() / "enemies" / "bosses_3.json", default=[])
    relics = load_json(data_dir() / "relics.json", default=[])

    ids = [str(c.get("id", "")) for c in cards]
    unique_ids = len(set(ids))
    dup_id_count = len(ids) - unique_ids

    required_issues = _card_required_issues(cards)
    duplicate_logic = _duplicate_logic(cards)
    duplicate_visual_cards, art_failures = _visual_duplicates(cards)
    missing_kpi_icons, missing_icon_types = _icon_issues(cards)
    overflow_count = _text_overflow_count(cards)

    # Archetype simulations: 10 runs each minimum.
    archetypes = ["cosmic_warrior", "harmony_guardian", "oracle_of_fate"]
    per_arch: dict[str, dict] = {}
    arch_results: list[SimResult] = []
    seed = 9100
    for a in archetypes:
        sims: list[SimResult] = []
        for i in range(10):
            boss = (i % 4 == 3)
            with redirect_stdout(io.StringIO()):
                sims.append(_simulate_one(a, seed + i, boss, cards, base, hip, enemies, bosses))
        seed += 97
        arch_results.extend(sims)
        turns = [r.turns for r in sims if not r.boss]
        boss_turns = [r.turns for r in sims if r.boss]
        dmg = [r.damage_done for r in sims]
        boss_wins = [1 for r in sims if r.boss and r.win]
        boss_total = max(1, len([r for r in sims if r.boss]))
        per_arch[a] = {
            "avg_damage": round(statistics.mean(dmg), 2) if dmg else 0.0,
            "avg_turns_combat": round(statistics.mean(turns), 2) if turns else 0.0,
            "avg_turns_boss": round(statistics.mean(boss_turns), 2) if boss_turns else 0.0,
            "boss_win_rate": round(sum(boss_wins) / boss_total, 3),
        }

    # Global simulate_run(50)
    global_runs: list[SimResult] = []
    rng = random.Random(9601)
    for i in range(50):
        a = archetypes[i % len(archetypes)]
        boss = rng.random() < 0.22
        with redirect_stdout(io.StringIO()):
            global_runs.append(_simulate_one(a, 10000 + i, boss, cards, base, hip, enemies, bosses))

    turns_battle = [r.turns for r in global_runs if not r.boss]
    turns_boss = [r.turns for r in global_runs if r.boss]
    boss_total = len(turns_boss)
    boss_wins = sum(1 for r in global_runs if r.boss and r.win)

    # Deck integrity via existing tool logic equivalence: do one explicit audit signal.
    from tools.check_deck_system import main as deck_check_main

    with redirect_stdout(io.StringIO()):
        deck_rc = int(deck_check_main())

    # Relic integrity checks.
    relic_errors = 0
    for r in (relics if isinstance(relics, list) else []):
        if not isinstance(r, dict):
            relic_errors += 1
            continue
        if not r.get("id") or not r.get("name_key") or not r.get("text_key"):
            relic_errors += 1

    map_dist = _map_distribution()
    loc = _localization_issues()
    audio = _audio_intro_checks()

    report = {
        "cards_checked_total": len(cards),
        "cards_checked_base": len(base),
        "cards_checked_hiperboria": len(hip),
        "invalid_cards": len(required_issues),
        "duplicate_logic_cards": sum(len(v) - 1 for v in duplicate_logic.values()),
        "duplicate_visual_cards": int(duplicate_visual_cards),
        "avg_turns_battle": round(statistics.mean(turns_battle), 2) if turns_battle else 0.0,
        "avg_turns_boss": round(statistics.mean(turns_boss), 2) if turns_boss else 0.0,
        "boss_win_rate": round((boss_wins / boss_total), 3) if boss_total else 0.0,
        "relic_errors": int(relic_errors),
        "art_failures": int(art_failures),
        "localization_issues": int(loc.get("mojibake", 0) + loc.get("same_as_en", 0)),
        "deck_check_rc": deck_rc,
        "missing_kpi_icons": int(missing_kpi_icons),
        "effect_text_overflow_risk": int(overflow_count),
        "map_distribution": map_dist,
        "archetype_simulation": per_arch,
        "audio_intro": audio,
        "required_field_issues_sample": required_issues[:30],
        "missing_icon_types": missing_icon_types,
    }
    return report


def write_report(report: dict) -> Path:
    out = Path("docs") / "QA_PHASE9_SUPERVISION_EXPANDED.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Phase 9 QA Supervision Expanded")
    lines.append("")
    lines.append("## Metrics")
    for k in [
        "cards_checked_total",
        "cards_checked_base",
        "cards_checked_hiperboria",
        "invalid_cards",
        "duplicate_logic_cards",
        "duplicate_visual_cards",
        "avg_turns_battle",
        "avg_turns_boss",
        "boss_win_rate",
        "relic_errors",
        "art_failures",
        "localization_issues",
        "missing_kpi_icons",
        "effect_text_overflow_risk",
        "deck_check_rc",
    ]:
        lines.append(f"- `{k}`: {report.get(k)}")

    lines.append("")
    lines.append("## Archetype Simulation (10 each)")
    for a, row in report.get("archetype_simulation", {}).items():
        lines.append(f"- `{a}`: avg_damage={row.get('avg_damage')} avg_turns_combat={row.get('avg_turns_combat')} avg_turns_boss={row.get('avg_turns_boss')} boss_win_rate={row.get('boss_win_rate')}")

    lines.append("")
    lines.append("## Map Distribution")
    md = report.get("map_distribution", {})
    lines.append(f"- combats_like={md.get('combats_like')} events={md.get('events')} relic={md.get('relic')} shop={md.get('shop')} boss={md.get('boss')} sanctuary={md.get('sanctuary')}")

    lines.append("")
    lines.append("## Audio and Intro")
    ai = report.get("audio_intro", {})
    lines.append(f"- bgm_context_missing={ai.get('bgm_context_missing')}")
    lines.append(f"- stingers_missing={ai.get('stingers_missing')}")
    lines.append(f"- intro_duration={ai.get('intro_duration')} intro_has_logo={ai.get('intro_has_logo')} intro_cosmic_bg={ai.get('intro_cosmic_bg')}")

    lines.append("")
    lines.append("## Issues Sample")
    for it in report.get("required_field_issues_sample", [])[:20]:
        lines.append(f"- {it}")

    lines.append("")
    lines.append("## Missing Icon Types")
    miss = report.get("missing_icon_types", {})
    if miss:
        for k, v in sorted(miss.items(), key=lambda kv: kv[1], reverse=True)[:20]:
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Raw JSON")
    lines.append("```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    lines.append("```")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    report = run_phase9_report()
    path = write_report(report)
    print(f"[qa_phase9] report={path}")
    print(json.dumps({k: report[k] for k in [
        "cards_checked_total",
        "cards_checked_base",
        "cards_checked_hiperboria",
        "invalid_cards",
        "duplicate_logic_cards",
        "duplicate_visual_cards",
        "avg_turns_battle",
        "avg_turns_boss",
        "boss_win_rate",
        "relic_errors",
        "art_failures",
        "localization_issues",
    ]}, ensure_ascii=False, indent=2))

    # Soft pass criteria for supervision phase; failures are reported, not hard-crash.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())













