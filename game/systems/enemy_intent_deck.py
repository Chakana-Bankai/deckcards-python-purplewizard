from __future__ import annotations

from typing import Any


def _normalize_intent(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row or {})
    out.setdefault("intent", "attack")
    if out.get("intent") in {"attack", "defend"} and not isinstance(out.get("value"), list):
        v = int(out.get("value", 5) or 5)
        out["value"] = [v, v]
    return out


def infer_enemy_type(enemy_row: dict[str, Any]) -> str:
    tier = str(enemy_row.get("tier", "common")).lower().strip()
    if tier == "boss":
        return "arconte"
    if tier == "elite":
        return "guardian"
    return "criatura"


def infer_ai_profile(intent_deck: list[dict[str, Any]], tier: str) -> str:
    t = str(tier or "common").lower().strip()
    if t == "boss":
        return "control"
    kinds = [str(x.get("intent", "")).lower() for x in list(intent_deck or []) if isinstance(x, dict)]
    atk = kinds.count("attack") + kinds.count("break")
    defn = kinds.count("defend")
    ctrl = kinds.count("debuff") + kinds.count("buff") + kinds.count("channel")
    if defn >= atk and defn >= ctrl:
        return "bulwark"
    if ctrl >= atk:
        return "control"
    return "aggro"


def _synth_attack(pattern: list[dict[str, Any]]) -> dict[str, Any]:
    vals = []
    for it in pattern:
        if str(it.get("intent", "")).lower() == "attack":
            v = it.get("value", [6, 6])
            if isinstance(v, list) and v:
                vals.append(int(v[-1]))
            else:
                vals.append(int(v or 6))
    base = max(5, int(sum(vals) / max(1, len(vals))) if vals else 6)
    return {"intent": "attack", "value": [base, base], "label": f"Preparando: Ataque {base}"}


def _synth_defend(pattern: list[dict[str, Any]]) -> dict[str, Any]:
    vals = []
    for it in pattern:
        if str(it.get("intent", "")).lower() in {"attack", "defend"}:
            v = it.get("value", [6, 6])
            if isinstance(v, list) and v:
                vals.append(int(v[-1]))
            else:
                vals.append(int(v or 6))
    base = max(3, int((sum(vals) / max(1, len(vals))) * 0.7) if vals else 4)
    return {"intent": "defend", "value": [base, base], "label": f"Preparando: Guardia {base}"}


def build_enemy_intent_deck(enemy_row: dict[str, Any]) -> list[dict[str, Any]]:
    existing = enemy_row.get("intent_deck", [])
    if isinstance(existing, list) and existing:
        out = [_normalize_intent(x) for x in existing if isinstance(x, dict)]
        return out if out else []

    pattern = [_normalize_intent(x) for x in list(enemy_row.get("pattern", []) or []) if isinstance(x, dict)]
    if not pattern:
        pattern = [{"intent": "attack", "value": [6, 6], "label": "Preparando: Ataque 6"}]

    deck: list[dict[str, Any]] = []
    for it in pattern:
        deck.append(dict(it))

    kinds = {str(x.get("intent", "")).lower() for x in deck}
    if "attack" not in kinds:
        deck.append(_synth_attack(pattern))
    if "defend" not in kinds:
        deck.append(_synth_defend(pattern))

    tier = str(enemy_row.get("tier", "common")).lower().strip()
    if tier in {"elite", "boss"}:
        deck.append(_synth_attack(pattern))
    if tier == "boss":
        deck.append({"intent": "debuff", "status": "weaken", "stacks": 1, "label": "Canaliza: weaken 1"})

    while len(deck) < 6:
        deck.append(dict(deck[len(deck) % max(1, len(deck))]))
    return deck[:10]
