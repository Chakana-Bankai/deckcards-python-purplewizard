from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from game.combat.card import CardDef, CardInstance
from game.combat.play_validation import can_play
from game.ui.components.card_effect_summary import summarize_card_effect


VALID_ROLES = {"attack", "defense", "energy", "control", "ritual", "combo"}


def _extract_starter_decks() -> dict[str, list[str]]:
    path = Path("game/ui/screens/path_select.py")
    if not path.exists():
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

    decks = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = []
        vals = []
        for k in node.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.append(k.value)
            else:
                keys.append(None)
        vals = list(node.values)
        if "id" in keys and "deck" in keys:
            try:
                i_id = keys.index("id")
                i_deck = keys.index("deck")
                did = ast.literal_eval(vals[i_id])
                ddeck = ast.literal_eval(vals[i_deck])
                if isinstance(did, str) and isinstance(ddeck, list):
                    decks[did] = [str(x) for x in ddeck if x]
            except Exception:
                continue
    return decks


def _deck_profile(deck_ids: list[str], by_id: dict[str, dict]) -> dict[str, int]:
    profile = {
        "damage": 0,
        "block": 0,
        "draw": 0,
        "scry": 0,
        "ritual": 0,
        "energy": 0,
        "attack_role": 0,
        "defense_role": 0,
        "control_role": 0,
    }
    for cid in deck_ids:
        card = by_id.get(cid)
        if not card:
            continue
        summary = summarize_card_effect(card)
        stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
        role = str(card.get("role", "")).lower()
        profile["damage"] += int(stats.get("damage", 0) or 0)
        profile["block"] += int(stats.get("block", 0) or 0)
        profile["draw"] += int(stats.get("draw", 0) or 0)
        profile["scry"] += int(stats.get("scry", 0) or 0)
        profile["ritual"] += int(stats.get("harmony_delta", 0) or 0)
        profile["energy"] += int(stats.get("energy_delta", 0) or 0)
        if role == "attack":
            profile["attack_role"] += 1
        if role == "defense":
            profile["defense_role"] += 1
        if role == "control":
            profile["control_role"] += 1
    return profile


def validate_content(cards_data: list[dict], assets_root: Path) -> dict:
    issues = []
    seen = set()
    summary_ok = 0
    can_play_ok = 0
    placeholders = 0

    role_counts = {r: 0 for r in VALID_ROLES}

    dummy_ctx = SimpleNamespace(
        player={"energy": 10, "statuses": {}, "harmony_current": 10},
        enemies=[SimpleNamespace(alive=True)],
        harmony_chaos_pending=False,
        hand=[],
        hand_max=6,
    )

    for c in cards_data:
        cid = str(c.get("id", "")).strip()
        if not cid:
            issues.append("missing_id")
            continue
        if cid in seen:
            issues.append(f"duplicate_id:{cid}")
            continue
        seen.add(cid)

        name = str(c.get("name_key", "")).strip()
        if not name or name.startswith("card_"):
            issues.append(f"name_es_missing:{cid}")

        if int(c.get("cost", 0) or 0) < 0:
            issues.append(f"negative_cost:{cid}")

        role = str(c.get("role", "")).strip().lower()
        if role not in VALID_ROLES:
            issues.append(f"invalid_role:{cid}:{role or 'missing'}")
        else:
            role_counts[role] += 1

        summary = summarize_card_effect(c)
        lines = [ln for ln in summary.get("lines", []) if isinstance(ln, str) and ln.strip()]
        has_fallback_line = bool(lines) and lines[0].lower().startswith("efecto: ritual")
        has_text_key = bool(str(c.get("text_key", "")).strip())
        if lines and (not has_fallback_line or has_text_key):
            summary_ok += 1
        else:
            issues.append(f"weak_summary:{cid}")

        try:
            cdef_payload = {
                "id": c.get("id"),
                "name_key": c.get("name_key", c.get("id", "card")),
                "text_key": c.get("text_key", ""),
                "rarity": c.get("rarity", "common"),
                "cost": int(c.get("cost", 0) or 0),
                "target": c.get("target", "enemy"),
                "tags": list(c.get("tags", []) or []),
                "effects": list(c.get("effects", []) or []),
                "role": c.get("role", "combo"),
                "family": c.get("family", "attack"),
                "direction": c.get("direction", "ESTE"),
            }
            card = CardInstance(CardDef(**cdef_payload))
            ok, reason_code, reason_text = can_play(card, dummy_ctx)
            if isinstance(ok, bool) and isinstance(reason_code, str) and isinstance(reason_text, str):
                can_play_ok += 1
            else:
                issues.append(f"can_play_contract:{cid}")
        except Exception:
            issues.append(f"can_play_exception:{cid}")

        p = assets_root / "sprites" / "cards" / f"{cid}.png"
        if not p.exists():
            placeholders += 1

    for role, count in role_counts.items():
        if count <= 0:
            issues.append(f"role_missing_globally:{role}")

    by_id = {str(c.get("id")): c for c in cards_data if isinstance(c, dict) and c.get("id")}
    decks = _extract_starter_decks()
    if decks:
        cw = _deck_profile(decks.get("cosmic_warrior", []), by_id)
        hg = _deck_profile(decks.get("harmony_guardian", []), by_id)
        of = _deck_profile(decks.get("oracle_of_fate", []), by_id)

        if not (cw["damage"] > hg["damage"] and cw["attack_role"] >= 4):
            issues.append("archetype_identity:cosmic_warrior_not_aggressive")
        if not (hg["block"] >= cw["block"] and hg["ritual"] >= 4 and hg["defense_role"] >= 4):
            issues.append("archetype_identity:harmony_guardian_not_scaling")
        if not (of["scry"] + of["draw"] >= cw["scry"] + cw["draw"] and of["control_role"] >= 4):
            issues.append("archetype_identity:oracle_of_fate_not_control")

    status = "OK" if not issues else "WARN"
    return {
        "status": status,
        "cards": len(cards_data),
        "summary_ok": summary_ok,
        "can_play_ok": can_play_ok,
        "placeholders": placeholders,
        "role_counts": role_counts,
        "issues": issues[:40],
    }
