from __future__ import annotations

import json
import os
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.main import App
from game.combat.combat_state import CombatState
from game.combat.play_validation import REASON_HAND_FULL, can_play


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _first_enemy_id(app: App) -> str:
    if isinstance(getattr(app, "enemies_data", None), list):
        for e in app.enemies_data:
            if isinstance(e, dict) and e.get("id"):
                return str(e["id"])
    return "dummy"


def _advance_until(app: App, target: str, steps: int = 40) -> bool:
    for _ in range(max(1, steps)):
        cur = app.sm.current
        if cur and cur.__class__.__name__ == target:
            return True
        if cur is None:
            return False
        cur.update(0.20)
    cur = app.sm.current
    return bool(cur and cur.__class__.__name__ == target)


def test_overflow_to_discard(app: App) -> tuple[bool, dict]:
    app.start_run_with_deck(["strike"] * 30)
    st = CombatState(app.rng, app.run_state, [_first_enemy_id(app)], cards_data=app._combat_card_catalog(), enemies_data=app.enemies_data)
    st.hand_max = 5
    while len(st.hand) < st.hand_max and st.draw_pile:
        st.hand.append(st.draw_pile.pop())
    before = {"hand": len(st.hand), "discard": len(st.discard_pile), "draw": len(st.draw_pile)}
    st.draw(3)
    after = {"hand": len(st.hand), "discard": len(st.discard_pile), "draw": len(st.draw_pile)}
    ok = after["hand"] <= st.hand_max and after["discard"] >= before["discard"]
    return ok, {"before": before, "after": after, "hand_max": st.hand_max}


def test_reshuffle_flow(app: App) -> tuple[bool, dict]:
    app.start_run_with_deck(["strike"] * 30)
    st = CombatState(app.rng, app.run_state, [_first_enemy_id(app)], cards_data=app._combat_card_catalog(), enemies_data=app.enemies_data)
    while st.draw_pile:
        st.discard_pile.append(st.draw_pile.pop())
    before = {"draw": len(st.draw_pile), "discard": len(st.discard_pile), "hand": len(st.hand)}
    st.draw(1)
    after = {"draw": len(st.draw_pile), "discard": len(st.discard_pile), "hand": len(st.hand)}
    ok = before["draw"] == 0 and before["discard"] > 0 and after["hand"] >= 1
    return ok, {"before": before, "after": after}


def _pick_first_combat_node(app: App) -> dict | None:
    run_map = list((app.run_state or {}).get("map", []) or [])
    for col in run_map:
        if not isinstance(col, list):
            continue
        for node in col:
            if not isinstance(node, dict):
                continue
            if str(node.get("state", "")).lower() == "available" and str(node.get("type", "")).lower() in {"combat", "challenge", "elite", "boss"}:
                return node
    return None


def test_retry_flow(app: App) -> tuple[bool, dict]:
    app.start_run_with_deck(["strike", "defend"] * 15)
    node = _pick_first_combat_node(app)
    if not isinstance(node, dict):
        return False, {"error": "no_available_combat_node"}

    app.select_map_node(node)
    entered = _advance_until(app, "CombatScreen")

    app.goto_end(victory=False)
    retried = app.retry_current_combat()
    reached = _advance_until(app, "CombatScreen")
    now = app.sm.current.__class__.__name__ if app.sm.current else "None"

    ok = bool(entered and retried and reached and app.current_combat is not None)
    return ok, {"entered": entered, "retried": retried, "reached": reached, "screen": now, "has_combat": bool(app.current_combat is not None)}


def test_play_validation_not_blocked_by_hand_full(app: App) -> tuple[bool, dict]:
    app.start_run_with_deck(["strike"] * 30)
    st = CombatState(app.rng, app.run_state, [_first_enemy_id(app)], cards_data=app._combat_card_catalog(), enemies_data=app.enemies_data)
    st.hand_max = 5
    while len(st.hand) < 6 and st.draw_pile:
        st.hand.append(st.draw_pile.pop())
    card = st.hand[0] if st.hand else None
    ok_code, reason, msg = can_play(card, st)
    ok = bool(ok_code or reason != REASON_HAND_FULL)
    return ok, {"ok_code": ok_code, "reason": reason, "msg": msg, "hand": len(st.hand), "hand_max": st.hand_max}


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()

    tests = {
        "overflow_to_discard": test_overflow_to_discard(app),
        "reshuffle_flow": test_reshuffle_flow(app),
        "retry_flow": test_retry_flow(app),
        "play_validation_not_hand_full_block": test_play_validation_not_blocked_by_hand_full(app),
    }

    summary = {k: _status(v[0]) for k, v in tests.items()}
    overall = "PASS" if all(v[0] for v in tests.values()) else "FAIL"

    payload = {
        "overall": overall,
        "summary": summary,
        "details": {k: v[1] for k, v in tests.items()},
    }

    lines = [
        "CHAKANA PHASE 1 - GAMEPLAY BLOCKER REPORT",
        "=" * 48,
        f"overall={overall}",
        "",
        "Checks",
        f"- overflow_to_discard: {summary.get('overflow_to_discard', 'FAIL')}",
        f"- reshuffle_flow: {summary.get('reshuffle_flow', 'FAIL')}",
        f"- retry_flow: {summary.get('retry_flow', 'FAIL')}",
        f"- play_validation_not_hand_full_block: {summary.get('play_validation_not_hand_full_block', 'FAIL')}",
        "",
        "Details",
    ]
    for k, data in payload["details"].items():
        lines.append(f"- {k}: {json.dumps(data, ensure_ascii=False)}")

    report_path = Path("reports/validation/gameplay_blocker_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload["report"] = str(report_path)
    return payload


if __name__ == "__main__":
    out = run()
    print("[qa_phase1] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))
