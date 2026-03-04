from __future__ import annotations


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
        elif typ == "rupture":
            stats["rupture"] += amount
        elif typ == "draw":
            stats["draw"] += amount
        elif typ in {"energy", "gain_mana"}:
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
            stats["damage"] += max(8, amount)
            stats["harmony_delta"] += 1
        elif typ == "double_block_cap":
            stats["block"] += max(4, amount // 2)

    lines = []
    if stats["damage"] > 0:
        lines.append(f"Daño: {stats['damage']}")
    if stats["block"] > 0:
        lines.append(f"Bloqueo: {stats['block']}")
    if stats["rupture"] > 0:
        lines.append(f"Ruptura: {stats['rupture']}")
    if stats["draw"] > 0:
        lines.append(f"Roba: {stats['draw']}")
    if stats["scry"] > 0:
        lines.append(f"Prever (Scry): mira {stats['scry']}, elige 1")
    if stats["energy_delta"] != 0:
        sign = "+" if stats["energy_delta"] > 0 else ""
        lines.append(f"Energía: {sign}{stats['energy_delta']}")
    if stats["harmony_delta"] > 0:
        lines.append(f"Armonía: +{stats['harmony_delta']}")
    if stats["consume_harmony"] > 0:
        lines.append(f"Consume Armonía: {stats['consume_harmony']}")
    if stats["exhaust"] > 0:
        lines.append("Se agota al usar")
    if stats["retain"] > 0:
        lines.append("Retener: permanece en mano")

    if not lines:
        lines = ["Efecto: Ritual (ver descripción)"]

    header = "Efecto: " + (lines[0] if lines else "Ritual")
    return {
        "header": header,
        "lines": lines[:4],
        "stats": stats,
        "tags": tags,
        "text_key": text_key,
    }
