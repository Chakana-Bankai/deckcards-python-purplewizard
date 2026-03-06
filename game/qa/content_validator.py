from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from game.combat.card import CardDef, CardInstance
from game.combat.play_validation import can_play
from game.ui.components.card_effect_summary import summarize_card_effect


def validate_content(cards_data: list[dict], assets_root: Path) -> dict:
    issues = []
    seen = set()
    summary_ok = 0
    can_play_ok = 0
    placeholders = 0

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

        summary = summarize_card_effect(c)
        lines = [ln for ln in summary.get("lines", []) if isinstance(ln, str) and ln.strip()]
        if lines and not lines[0].lower().startswith("efecto: ritual"):
            summary_ok += 1
        else:
            issues.append(f"weak_summary:{cid}")

        try:
            card = CardInstance(CardDef(**c))
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

    status = "OK" if not issues else "WARN"
    return {
        "status": status,
        "cards": len(cards_data),
        "summary_ok": summary_ok,
        "can_play_ok": can_play_ok,
        "placeholders": placeholders,
        "issues": issues[:24],
    }
