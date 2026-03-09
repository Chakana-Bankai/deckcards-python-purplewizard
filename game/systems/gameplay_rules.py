from __future__ import annotations

from typing import Iterable


DEFAULT_PLAYER_RULES = {
    "player_hp": 60,
    "energy_per_turn": 3,
    "player_combat_deck_size": 30,
    "starting_hand": 5,
    "draw_per_turn": 5,
    "hand_limit": 10,
}


def normalized_combat_deck(deck_ids: Iterable[str], fallback_card_id: str, target_size: int) -> list[str]:
    """Return a deterministic combat deck list with a minimum target size.

    This keeps run-level deck composition intact while safely padding short decks
    for combat-only flow requirements.
    """
    src = [str(x) for x in list(deck_ids or []) if str(x).strip()]
    if not src:
        src = [str(fallback_card_id)]
    target = max(1, int(target_size or 1))
    if len(src) >= target:
        return src[:]

    out = src[:]
    idx = 0
    while len(out) < target:
        out.append(src[idx % len(src)])
        idx += 1
    return out
