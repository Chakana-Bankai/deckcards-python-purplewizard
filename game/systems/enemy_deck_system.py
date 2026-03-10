from __future__ import annotations

from typing import Any

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.systems.enemy_intent_deck import build_enemy_intent_deck


ENEMY_DECK_ALIAS = {
    "voidling": "void_acolyte",
    "ink_mite": "void_acolyte",
    "whisper_mask": "corrupt_mage",
    "rift_hound": "archon_guard",
    "mirror_scribe": "corrupt_mage",
    "grief_larva": "void_acolyte",
    "violet_thief": "corrupt_mage",
    "stone_sentinel": "archon_guard",
    "inverse_weaver": "boss_archon",
}


ENEMY_CARD_NAME_MAP = {
    "void strike": "Golpe del Vacio",
    "shadow hex": "Hexe Sombrio",
    "corrupt shield": "Escudo Corrupto",
    "entropy bite": "Mordida Entropica",
    "void choke": "Asfixia del Vacio",
    "umbral drain": "Drenaje Umbral",
    "arcane rust": "Oxido Arcano",
    "void bolt": "Rayo del Vacio",
    "dark ward": "Guardia Oscura",
    "entropy mark": "Marca Entropica",
    "control field": "Campo de Control",
    "hex surge": "Oleada Hex",
    "guardian wall": "Muro del Guardian",
    "crimson lance": "Lanza Carmesi",
    "archon order": "Mandato del Arconte",
    "rupture wave": "Ola de Ruptura",
    "null decree": "Decreto Nulo",
    "abyssal hymn": "Himno Abisal",
    "void coronation": "Coronacion del Vacio",
    "black sun": "Sol Negro",
}


def lore_enemy_card_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return "Presagio Arconte"
    low = name.lower()
    if low in ENEMY_CARD_NAME_MAP:
        return ENEMY_CARD_NAME_MAP[low]
    return name.replace("_", " ").title()


def _normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    c = dict(card or {})
    c.setdefault("id", str(c.get("name", "enemy_card")).strip().lower().replace(" ", "_"))
    c["name"] = lore_enemy_card_name(str(c.get("name", c.get("id", "enemy_card"))))
    c.setdefault("intent", "attack")
    if c.get("intent") in {"attack", "defend"} and not isinstance(c.get("value"), list):
        v = int(c.get("value", 6) or 6)
        c["value"] = [v, v]
    return c


def _cards_from_intents(enemy_row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for i, it in enumerate(build_enemy_intent_deck(enemy_row), start=1):
        if not isinstance(it, dict):
            continue
        card = dict(it)
        card.setdefault("id", f"{str(enemy_row.get('id', 'enemy')).lower()}_intent_{i}")
        card["name"] = lore_enemy_card_name(str(it.get("name", it.get("label", card["id"])).strip() or card["id"]))
        out.append(_normalize_card(card))
    return out


def load_enemy_decks() -> dict[str, list[dict[str, Any]]]:
    path = data_dir() / "enemy_decks.json"
    payload = load_json(path, default={})
    rows = payload.get("decks", payload) if isinstance(payload, dict) else {}
    out: dict[str, list[dict[str, Any]]] = {}
    if isinstance(rows, dict):
        for enemy_id, cards in rows.items():
            if not isinstance(cards, list):
                continue
            cooked = [_normalize_card(c) for c in cards if isinstance(c, dict)]
            if cooked:
                out[str(enemy_id).strip().lower()] = cooked
    return out


def resolve_enemy_deck(enemy_row: dict[str, Any], all_decks: dict[str, list[dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    row = dict(enemy_row or {})
    enemy_id = str(row.get("id", "")).strip().lower()
    decks = dict(all_decks or load_enemy_decks())

    if enemy_id in decks:
        return [dict(c) for c in decks[enemy_id]]

    alias = ENEMY_DECK_ALIAS.get(enemy_id, "")
    if alias and alias in decks:
        return [dict(c) for c in decks[alias]]

    return _cards_from_intents(row)
