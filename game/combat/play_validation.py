from __future__ import annotations


REASON_OK = "OK"
REASON_NO_ENERGY = "NO_ENERGY"
REASON_NO_TARGET = "NO_TARGET"
REASON_CONDITION_FAIL = "CONDITION_FAIL"
REASON_STATE_LOCK = "STATE_LOCK"
REASON_HAND_FULL = "HAND_FULL"
REASON_OTHER = "OTHER"

_REASON_ES = {
    REASON_OK: "OK",
    REASON_NO_ENERGY: "Energía insuficiente",
    REASON_NO_TARGET: "Sin objetivo enemigo",
    REASON_CONDITION_FAIL: "Condición de carta no cumplida",
    REASON_STATE_LOCK: "Estado bloqueado",
    REASON_HAND_FULL: "Mano llena",
    REASON_OTHER: "No se puede jugar",
}


def reason_to_es(reason_code: str, detail: str = "") -> str:
    base = _REASON_ES.get(reason_code or REASON_OTHER, _REASON_ES[REASON_OTHER])
    if detail:
        return f"{base}: {detail}"
    return base


def can_play(card, ctx) -> tuple[bool, str]:
    player_state = getattr(ctx, "player", None)
    if not isinstance(player_state, dict):
        player_state = {}

    if card is None:
        return False, REASON_OTHER

    energy = int(player_state.get("energy", 0) or 0)
    cost = int(getattr(card, "cost", getattr(getattr(card, "definition", None), "cost", 0)) or 0)
    extra_cost = 1 if bool(getattr(ctx, "harmony_chaos_pending", False)) else 0

    statuses = player_state.get("statuses", {}) if isinstance(player_state.get("statuses", {}), dict) else {}
    if int(statuses.get("stun", 0) or 0) > 0:
        return False, REASON_STATE_LOCK
    if int(statuses.get("silence", 0) or 0) > 0:
        tags = list(getattr(getattr(card, "definition", None), "tags", []) or [])
        if "ritual" in tags or "magic" in tags:
            return False, REASON_STATE_LOCK

    if energy < (cost + extra_cost):
        return False, REASON_NO_ENERGY

    target_kind = getattr(getattr(card, "definition", None), "target", "enemy")
    enemies = [e for e in getattr(ctx, "enemies", []) if getattr(e, "alive", False)]
    if target_kind == "enemy" and not enemies:
        return False, REASON_NO_TARGET

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
            return False, REASON_CONDITION_FAIL

    if len(getattr(ctx, "hand", [])) > int(getattr(ctx, "hand_max", 6)):
        return False, REASON_HAND_FULL

    return True, REASON_OK


def can_play_card(card, player_state: dict, combat_state) -> tuple[bool, str]:
    ok, code = can_play(card, combat_state)
    if ok:
        return True, "OK"

    detail = ""
    if code == REASON_NO_ENERGY:
        energy = int(player_state.get("energy", 0) or 0)
        cost = int(getattr(card, "cost", getattr(getattr(card, "definition", None), "cost", 0)) or 0)
        extra_cost = 1 if bool(getattr(combat_state, "harmony_chaos_pending", False)) else 0
        detail = f"{energy}/{cost + extra_cost}"
    elif code == REASON_CONDITION_FAIL:
        effects = list(getattr(getattr(card, "definition", None), "effects", []) or [])
        need = sum(max(1, int(ef.get("amount", 1) or 1)) for ef in effects if isinstance(ef, dict) and str(ef.get("type", "")).lower() == "consume_harmony")
        cur = int(player_state.get("harmony_current", 0) or 0)
        if need > 0:
            detail = f"Armonía {cur}/{need}"

    return False, reason_to_es(code, detail)
