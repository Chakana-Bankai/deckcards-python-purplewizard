from __future__ import annotations


def infer_card_role(card_def) -> str:
    """Infer semantic role for a card from explicit role, tags and effects."""
    definition = card_def or {}
    explicit = str(getattr(definition, "role", None) or definition.get("role", "")).strip().lower()
    valid = {"attack", "defense", "energy", "control", "ritual", "combo"}
    if explicit in valid:
        return explicit

    tags = {str(t).strip().lower() for t in (getattr(definition, "tags", None) or definition.get("tags", []) or [])}
    effects = list(getattr(definition, "effects", None) or definition.get("effects", []) or [])
    effect_types = {str(e.get("type", "")).strip().lower() for e in effects if isinstance(e, dict)}

    if "ritual" in tags or "ritual_trama" in effect_types:
        return "ritual"
    if "attack" in tags or "damage" in effect_types:
        if "draw" in effect_types or "copy_last_played" in effect_types:
            return "combo"
        return "attack"
    if "energy" in tags or any(t in effect_types for t in {"energy", "gain_mana", "gain_mana_next_turn"}):
        return "energy"
    if "block" in tags or any(t in effect_types for t in {"block", "gain_block", "heal"}):
        return "defense"
    if "draw" in tags or "scry" in tags or any(t in effect_types for t in {"draw", "scry", "weaken_enemy", "copy_last_played"}):
        return "control"
    return "combo"


def summarize_card_effect(card_def, card_instance=None, ctx=None) -> dict:
    definition = getattr(card_instance, "definition", None) or card_def or {}
    effects = list(getattr(definition, "effects", None) or definition.get("effects", []) or [])
    tags = list(getattr(definition, "tags", None) or definition.get("tags", []) or [])
    text_key = getattr(definition, "text_key", None) or definition.get("text_key", "")

    stats = {
        "damage": 0,
        "block": 0,
        "rupture": 0,
        "draw": 0,
        "harmony_delta": 0,
        "energy_delta": 0,
        "scry": 0,
        "ritual": 0,
        "gold": 0,
        "xp": 0,
        "exhaust": 0,
        "retain": 0,
        "consume_harmony": 0,
    }

    for ef in effects:
        if not isinstance(ef, dict):
            continue
        typ = str(ef.get("type", "")).lower()
        amount = int(ef.get("amount", 0) or 0)
        if typ == "damage":
            stats["damage"] += amount
        elif typ in {"block", "gain_block"}:
            stats["block"] += amount
        elif typ in {"rupture", "apply_break", "break"}:
            stats["rupture"] += max(1, amount)
        elif typ == "draw":
            stats["draw"] += amount
        elif typ in {"energy", "gain_mana", "gain_mana_next_turn"}:
            stats["energy_delta"] += amount
        elif typ == "scry":
            stats["scry"] += amount
        elif typ == "exhaust_self":
            stats["exhaust"] += 1
        elif typ == "retain":
            stats["retain"] += max(1, amount)
        elif typ == "harmony_delta":
            stats["harmony_delta"] += amount
        elif typ == "consume_harmony":
            stats["consume_harmony"] += max(1, amount)
        elif typ == "ritual_trama":
            stats["ritual"] += max(1, amount)
            stats["harmony_delta"] += 1
        elif typ == "gain_gold":
            stats["gold"] += max(0, amount)
        elif typ == "gain_xp":
            stats["xp"] += max(0, amount)

    lines = []
    if stats["damage"] > 0:
        lines.append(f"Dano: {stats['damage']}")
    if stats["block"] > 0:
        lines.append(f"Bloqueo: {stats['block']}")
    if stats["rupture"] > 0:
        lines.append(f"Ruptura: {stats['rupture']}")
    if stats["draw"] > 0:
        lines.append(f"Roba: {stats['draw']}")
    if stats["scry"] > 0:
        lines.append(f"Prever: {stats['scry']}")
    if stats["energy_delta"] != 0:
        sign = "+" if stats["energy_delta"] > 0 else ""
        lines.append(f"Energia: {sign}{stats['energy_delta']}")
    if stats["harmony_delta"] > 0:
        lines.append(f"Armonia: +{stats['harmony_delta']}")
    if stats["consume_harmony"] > 0:
        lines.append(f"Consume Armonia: {stats['consume_harmony']}")
    if stats["gold"] > 0:
        lines.append(f"Oro: +{stats['gold']}")
    if stats["xp"] > 0:
        lines.append(f"XP: +{stats['xp']}")
    if stats["exhaust"] > 0:
        lines.append("Se agota al usar")
    if stats["retain"] > 0:
        lines.append("Retener: permanece en mano")

    if not lines:
        lines = ["Efecto: ritual o utilidad"]

    header = "Efecto: " + lines[0]
    return {
        "header": header,
        "lines": lines[:5],
        "stats": stats,
        "tags": tags,
        "text_key": text_key,
        "role": infer_card_role(definition),
    }
