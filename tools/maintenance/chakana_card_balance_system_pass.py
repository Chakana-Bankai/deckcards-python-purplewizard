from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "game" / "data"


RARITY_TARGET = {
    "common": 30,
    "uncommon": 20,
    "rare": 7,
    "legendary": 3,
}


def _load_cards(path: Path) -> tuple[object, list[dict], str]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload, [dict(x) for x in payload if isinstance(x, dict)], "list"
    if isinstance(payload, dict):
        cards = payload.get("cards", [])
        if isinstance(cards, list):
            return payload, [dict(x) for x in cards if isinstance(x, dict)], "cards"
    return payload, [], "unknown"


def _save_cards(path: Path, payload: object, cards: list[dict], kind: str) -> None:
    if kind == "list":
        out = cards
    elif kind == "cards" and isinstance(payload, dict):
        out = dict(payload)
        out["cards"] = cards
    else:
        out = payload
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rarity_score(card: dict) -> int:
    score = 0
    effects = list(card.get("effects", []) or [])
    for e in effects:
        if not isinstance(e, dict):
            continue
        et = str(e.get("type", "")).lower()
        score += int(e.get("amount", 0) or 0)
        score += int(e.get("stacks", 0) or 0)
        if et in {"draw", "gain_energy", "ritual_trama", "copy_last_card", "copy_card_played"}:
            score += 2
        if et in {"damage_plus_rupture", "multi_attack", "execute", "kill", "double_damage"}:
            score += 4
    score += int(card.get("cost", 0) or 0)
    rid = str(card.get("rarity", "")).lower()
    if rid == "legendary":
        score += 10
    elif rid == "rare":
        score += 7
    elif rid == "uncommon":
        score += 4
    return score


def _ensure_rarity_distribution(cards: list[dict]) -> None:
    ordered = sorted(cards, key=lambda c: (_rarity_score(c), str(c.get("id", ""))), reverse=True)
    for i, c in enumerate(ordered):
        if i < RARITY_TARGET["legendary"]:
            c["rarity"] = "legendary"
        elif i < RARITY_TARGET["legendary"] + RARITY_TARGET["rare"]:
            c["rarity"] = "rare"
        elif i < RARITY_TARGET["legendary"] + RARITY_TARGET["rare"] + RARITY_TARGET["uncommon"]:
            c["rarity"] = "uncommon"
        else:
            c["rarity"] = "common"


def _taxonomy_guess(card: dict) -> str:
    rarity = str(card.get("rarity", "common")).lower()
    tags = {str(t).lower() for t in list(card.get("tags", []) or [])}
    effects = {str(e.get("type", "")).lower() for e in list(card.get("effects", []) or []) if isinstance(e, dict)}
    if rarity in {"legendary", "rare"}:
        return "payoff"
    if "draw" in effects or "scry" in effects or "retain" in effects or "combo" in tags:
        return "bridge"
    return "engine"


def _ensure_taxonomy_distribution(cards: list[dict]) -> None:
    by_arch: dict[str, list[dict]] = defaultdict(list)
    for c in cards:
        arch = str(c.get("archetype", "")).strip().lower() or "neutral"
        by_arch[arch].append(c)

    for arch_cards in by_arch.values():
        n = len(arch_cards)
        if n <= 0:
            continue
        target_engine = int(round(n * 0.50))
        target_bridge = int(round(n * 0.30))
        target_payoff = max(0, n - target_engine - target_bridge)

        ordered = sorted(arch_cards, key=lambda c: (_rarity_score(c), str(c.get("id", ""))), reverse=True)

        for c in ordered:
            c["taxonomy"] = _taxonomy_guess(c)

        for i, c in enumerate(ordered):
            if i < target_payoff:
                c["taxonomy"] = "payoff"
            elif i < target_payoff + target_bridge:
                c["taxonomy"] = "bridge"
            else:
                c["taxonomy"] = "engine"


def _ensure_lore_line(cards: list[dict], set_id: str) -> None:
    for c in cards:
        base = (
            "La Chakana sostiene el balance cosmico ante los Arcontes y el eco de Hiperborea."
            if set_id != "arconte"
            else "Los Arcontes tuercen la Chakana para romper el balance cosmico y profanar Hiperborea."
        )
        c["lore_text"] = str(c.get("lore_text", "")).strip() or base
        low = c["lore_text"].lower()
        need = ["chakana", "hiperb", "arcont", "balance"]
        if not all(k in low for k in need):
            c["lore_text"] = base


def _normalize_set(path: Path, set_id: str) -> dict:
    payload, cards, kind = _load_cards(path)
    cards = [dict(c) for c in cards]
    if len(cards) != 60:
        return {"set": set_id, "path": str(path), "status": "warning", "reason": f"expected_60_found_{len(cards)}"}
    _ensure_rarity_distribution(cards)
    _ensure_taxonomy_distribution(cards)
    _ensure_lore_line(cards, set_id)
    _save_cards(path, payload, cards, kind)

    rar = Counter(str(c.get("rarity", "")).lower() for c in cards)
    tax = Counter(str(c.get("taxonomy", "")).lower() for c in cards)
    by_arch = {}
    arch_map: dict[str, Counter] = defaultdict(Counter)
    for c in cards:
        arch = str(c.get("archetype", "")).strip().lower() or "neutral"
        arch_map[arch][str(c.get("taxonomy", "")).lower()] += 1
    for arch, cnt in arch_map.items():
        by_arch[arch] = dict(cnt)
    return {
        "set": set_id,
        "path": str(path),
        "status": "ok",
        "rarity": dict(rar),
        "taxonomy": dict(tax),
        "taxonomy_by_archetype": by_arch,
    }


def _regen_arconte_codex() -> dict:
    src = json.loads((DATA / "cards_arconte.json").read_text(encoding="utf-8-sig"))
    cards = list(src.get("cards", []) or []) if isinstance(src, dict) else []
    out_cards = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id", ""))
        if not cid:
            continue
        out_cards.append(
            {
                "id": cid,
                "name": str(c.get("name_es") or c.get("name_key") or cid),
                "set": "arconte",
                "archetype": str(c.get("archetype", "archon_war")),
                "rarity": str(c.get("rarity", "common")),
                "role": str(c.get("role", "control")),
                "gameplay_text": str(c.get("text_es") or c.get("text_key") or ""),
                "lore_text": str(c.get("lore_text", "")),
                "tags": list(c.get("tags", []) or []),
            }
        )
    payload = {
        "set_id": "arconte",
        "set_name": "Arconte",
        "total_cards": len(out_cards),
        "cards": out_cards,
    }
    path = DATA / "codex_cards_arconte.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "cards": len(out_cards)}


def _link_enemy_decks_to_archon_pool() -> dict:
    path = DATA / "enemy_decks.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    decks = payload.get("decks", {}) if isinstance(payload, dict) else {}
    if not isinstance(decks, dict):
        return {"status": "warning", "reason": "invalid_enemy_decks"}
    archon_ids = [f"arc_{i:03d}" for i in range(1, 61)]
    ptr = 0
    updated = 0
    for _enemy_id, rows in decks.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            row["source_set"] = "arconte"
            row["source_card_id"] = archon_ids[ptr % len(archon_ids)]
            ptr += 1
            updated += 1
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok", "updated_cards": updated}


def main() -> int:
    report = {
        "sets": [],
        "codex_arconte": {},
        "enemy_deck_linking": {},
    }
    report["sets"].append(_normalize_set(DATA / "cards.json", "base"))
    report["sets"].append(_normalize_set(DATA / "cards_hiperboria.json", "hiperboria"))
    report["sets"].append(_normalize_set(DATA / "cards_arconte.json", "arconte"))
    report["codex_arconte"] = _regen_arconte_codex()
    report["enemy_deck_linking"] = _link_enemy_decks_to_archon_pool()

    out = ROOT / "qa" / "reports" / "current" / "chakana_card_balance_system_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["CHAKANA CARD BALANCE SYSTEM PASS", "", json.dumps(report, ensure_ascii=False, indent=2)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[card_balance] report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
