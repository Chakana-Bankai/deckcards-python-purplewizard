from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.combat.combat_state import CombatState
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.services.deck_integrity import audit_and_repair_deck_piles


def main() -> int:
    cards = load_json(data_dir() / "cards.json", default=[])
    enemies = load_json(data_dir() / "enemies" / "enemies_30.json", default=[])

    card_ids = [str(c.get("id")) for c in cards if isinstance(c, dict) and c.get("id")]
    if len(card_ids) < 12:
        print("[deck_audit] insufficient cards for simulation")
        return 2

    run_state = {
        "player": {
            "hp": 60,
            "max_hp": 60,
            "block": 0,
            "energy": 3,
            "rupture": 0,
            "statuses": {},
            "harmony_current": 0,
            "harmony_max": 10,
            "harmony_ready_threshold": 6,
        },
        "deck": list(card_ids[:20]),
        "relics": [],
    }

    rng = SeededRNG(1337)
    enemy_id = next((str(e.get("id")) for e in enemies if isinstance(e, dict) and e.get("id")), "dummy")
    state = CombatState(rng, run_state, [enemy_id], cards_data=cards, enemies_data=enemies)
    expected = len(state.draw_pile) + len(state.hand) + len(state.discard_pile) + len(state.exhaust_pile)

    issues = []
    for turn in range(1, 9):
        plays = 0
        safety = 20
        while safety > 0 and state.result is None:
            safety -= 1
            if not state.hand:
                break
            playable_index = None
            target_idx = 0 if state.enemies and getattr(state.enemies[0], "alive", False) else None
            for i, card in enumerate(list(state.hand)):
                if int(card.cost or 0) <= int(state.player.get("energy", 0) or 0):
                    playable_index = i
                    break
            if playable_index is None:
                break
            state.play_card(playable_index, target_idx)
            plays += 1
            rep = audit_and_repair_deck_piles(state.draw_pile, state.hand, state.discard_pile, state.exhaust_pile, hand_max=state.hand_max, expected_total=expected)
            if rep.get("issues"):
                issues.extend([f"turn{turn}:play:{x}" for x in rep["issues"] if str(x).startswith("missing_cards_detected")])
        if state.result is not None:
            break
        state.end_turn()
        rep = audit_and_repair_deck_piles(state.draw_pile, state.hand, state.discard_pile, state.exhaust_pile, hand_max=state.hand_max, expected_total=expected)
        if rep.get("issues"):
            issues.extend([f"turn{turn}:end:{x}" for x in rep["issues"] if str(x).startswith("missing_cards_detected")])

    counts = {
        "draw": len(state.draw_pile),
        "hand": len(state.hand),
        "discard": len(state.discard_pile),
        "exhaust": len(state.exhaust_pile),
    }
    total = sum(counts.values())
    print(
        f"[deck_audit] result={state.result or 'ongoing'} turns={state.turn} "
        f"draw={counts['draw']} hand={counts['hand']} discard={counts['discard']} exhaust={counts['exhaust']} total={total} expected={expected} issues={len(issues)}"
    )
    if issues:
        print(issues[:12])
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
