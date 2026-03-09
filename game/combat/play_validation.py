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
    REASON_NO_ENERGY: "EnergÃƒÂ­a insuficiente",
    REASON_NO_TARGET: "Requiere objetivo",
    REASON_CONDITION_FAIL: "CondiciÃƒÂ³n de carta no cumplida",
    REASON_STATE_LOCK: "Bloqueada por estado",
    REASON_HAND_FULL: "Mano llena",
    REASON_OTHER: "No se puede jugar",
}


def reason_to_es(reason_code: str, detail: str = "") -> str:
    base = _REASON_ES.get(reason_code or REASON_OTHER, _REASON_ES[REASON_OTHER])
    if detail:
        return f"{base}: {detail}"
    return base




def _effective_cost(card, player_state: dict) -> int:
    _ = player_state
    return max(0, int(getattr(card, "cost", getattr(getattr(card, "definition", None), "cost", 0)) or 0))


def _harmony_need(card) -> int:
    effects = list(getattr(getattr(card, "definition", None), "effects", []) or [])
    need = 0
    for ef in effects:
        if not isinstance(ef, dict):
            continue
        if str(ef.get("type", "")).lower() == "consume_harmony":
            need += max(1, int(ef.get("amount", 1) or 1))
    return need


def can_play(card, ctx) -> tuple[bool, str, str]:
    player_state = getattr(ctx, "player", None)
    if not isinstance(player_state, dict):
        player_state = {}

    if card is None:
        return False, REASON_OTHER, reason_to_es(REASON_OTHER)

    energy = int(player_state.get("energy", 0) or 0)
    cost = _effective_cost(card, player_state)

    statuses = player_state.get("statuses", {}) if isinstance(player_state.get("statuses", {}), dict) else {}
    if int(statuses.get("stun", 0) or 0) > 0:
        return False, REASON_STATE_LOCK, reason_to_es(REASON_STATE_LOCK, "Aturdida")
    if int(statuses.get("silence", 0) or 0) > 0:
        tags = list(getattr(getattr(card, "definition", None), "tags", []) or [])
        if "ritual" in tags or "magic" in tags:
            return False, REASON_STATE_LOCK, reason_to_es(REASON_STATE_LOCK, "Silencio")

    if energy < cost:
        return False, REASON_NO_ENERGY, reason_to_es(REASON_NO_ENERGY, f"{energy}/{cost}")

    target_kind = getattr(getattr(card, "definition", None), "target", "enemy")
    enemies = [e for e in getattr(ctx, "enemies", []) if getattr(e, "alive", False)]
    if target_kind == "enemy" and not enemies:
        return False, REASON_NO_TARGET, reason_to_es(REASON_NO_TARGET)

    need_harmony = _harmony_need(card)
    if need_harmony > 0:
        cur = int(player_state.get("harmony_current", 0) or 0)
        if cur < need_harmony:
            return False, REASON_CONDITION_FAIL, f"Requiere Armonia {need_harmony}"
    return True, REASON_OK, reason_to_es(REASON_OK)


def can_play_card(card, player_state: dict, combat_state) -> tuple[bool, str, str]:
    _ = player_state
    return can_play(card, combat_state)
