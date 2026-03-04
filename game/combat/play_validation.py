from __future__ import annotations


def can_play_card(card, player_state: dict, combat_state) -> tuple[bool, str]:
    if card is None:
        return False, "Sin carta seleccionada"

    energy = int(player_state.get("energy", 0) or 0)
    cost = int(getattr(card, "cost", getattr(getattr(card, "definition", None), "cost", 0)) or 0)
    extra_cost = 1 if bool(getattr(combat_state, "harmony_chaos_pending", False)) else 0

    statuses = player_state.get("statuses", {}) if isinstance(player_state.get("statuses", {}), dict) else {}
    if int(statuses.get("stun", 0) or 0) > 0:
        return False, "Aturdido: no puedes jugar cartas"
    if int(statuses.get("silence", 0) or 0) > 0:
        tags = list(getattr(getattr(card, "definition", None), "tags", []) or [])
        if "ritual" in tags or "magic" in tags:
            return False, "Silencio: carta ritual/mágica bloqueada"

    if energy < (cost + extra_cost):
        return False, f"Energía insuficiente ({energy}/{cost + extra_cost})"

    target_kind = getattr(getattr(card, "definition", None), "target", "enemy")
    enemies = [e for e in getattr(combat_state, "enemies", []) if getattr(e, "alive", False)]
    if target_kind == "enemy" and not enemies:
        return False, "Sin objetivo enemigo"

    effects = list(getattr(getattr(card, "definition", None), "effects", []) or [])
    consume_harmony = 0
    for ef in effects:
        if not isinstance(ef, dict):
            continue
        if str(ef.get("type", "")).lower() == "consume_harmony":
            consume_harmony += max(1, int(ef.get("amount", 1) or 1))
    if consume_harmony > 0:
        cur = int(player_state.get("harmony_current", 0) or 0)
        if cur < consume_harmony:
            return False, f"Armonía insuficiente ({cur}/{consume_harmony})"

    return True, "OK"
