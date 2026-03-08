from __future__ import annotations

from typing import Any


def _card_key(card: Any) -> tuple[str, str]:
    cid = str(getattr(getattr(card, "definition", None), "id", "?"))
    iid = str(getattr(card, "instance_id", ""))
    if iid:
        return (cid, iid)
    return (cid, str(id(card)))


def audit_and_repair_deck_piles(
    draw_pile: list,
    hand: list,
    discard_pile: list,
    exhaust_pile: list,
    *,
    hand_max: int,
    expected_total: int | None = None,
) -> dict:
    """Audit and repair basic deck-pile integrity in-place.

    Repairs are conservative:
    - remove duplicated card instances across piles (keep first occurrence by priority)
    - move hand overflow to discard
    - trim excess cards from discard/draw if total unexpectedly exceeds expected_total
    """
    issues: list[str] = []
    repaired = False

    piles = [
        ("hand", hand),
        ("draw", draw_pile),
        ("discard", discard_pile),
        ("exhaust", exhaust_pile),
    ]

    seen: set[tuple[str, str]] = set()
    for name, pile in piles:
        i = 0
        while i < len(pile):
            key = _card_key(pile[i])
            if key in seen:
                pile.pop(i)
                repaired = True
                issues.append(f"duplicate_instance_removed:{name}:{key[0]}")
                continue
            seen.add(key)
            i += 1

    if len(hand) > int(hand_max):
        overflow = hand[int(hand_max):]
        del hand[int(hand_max):]
        discard_pile.extend(overflow)
        repaired = True
        issues.append(f"hand_overflow_fixed:{len(overflow)}")

    total_now = len(draw_pile) + len(hand) + len(discard_pile) + len(exhaust_pile)
    expected = total_now if expected_total is None else int(expected_total)

    if total_now > expected:
        extra = total_now - expected
        while extra > 0 and discard_pile:
            discard_pile.pop()
            extra -= 1
            repaired = True
        while extra > 0 and draw_pile:
            draw_pile.pop()
            extra -= 1
            repaired = True
        while extra > 0 and exhaust_pile:
            exhaust_pile.pop()
            extra -= 1
            repaired = True
        issues.append(f"total_overflow_trimmed:{total_now - expected}")

    total_after = len(draw_pile) + len(hand) + len(discard_pile) + len(exhaust_pile)
    if total_after < expected:
        issues.append(f"missing_cards_detected:{expected - total_after}")

    return {
        "ok": len([x for x in issues if x.startswith("missing_cards_detected")]) == 0,
        "repaired": repaired,
        "issues": issues,
        "counts": {
            "draw": len(draw_pile),
            "hand": len(hand),
            "discard": len(discard_pile),
            "exhaust": len(exhaust_pile),
            "total": total_after,
            "expected": expected,
        },
    }
