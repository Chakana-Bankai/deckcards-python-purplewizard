from __future__ import annotations

"""Spiritual bestiary resolver for lore-aligned entity visual profiles."""

from copy import deepcopy
from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json

_BESTIARY_CACHE: dict[str, object] = {"stamp": None, "payload": None}


def _safe_id(value: object) -> str:
    return str(value or "").strip().lower()


def _source_stamp(base: Path) -> tuple[str, int]:
    path = base / "spiritual_bestiary.json"
    try:
        return str(path), int(path.stat().st_mtime_ns)
    except Exception:
        return str(path), -1


def _build_indexes(payload: dict) -> dict:
    entities = payload.get("entities") if isinstance(payload, dict) else []
    entities = entities if isinstance(entities, list) else []

    by_id: dict[str, dict] = {}
    alias_to_id: dict[str, str] = {}
    for raw in entities:
        if not isinstance(raw, dict):
            continue
        eid = _safe_id(raw.get("id"))
        if not eid:
            continue
        entity = dict(raw)
        by_id[eid] = entity
        alias_to_id[eid] = eid
        for alias in list(raw.get("aliases", []) or []):
            aid = _safe_id(alias)
            if aid:
                alias_to_id[aid] = eid

    return {"by_id": by_id, "alias_to_id": alias_to_id}


def load_spiritual_bestiary(base: Path | None = None) -> dict:
    base = base or data_dir()
    stamp = _source_stamp(base)
    if _BESTIARY_CACHE.get("stamp") == stamp and isinstance(_BESTIARY_CACHE.get("payload"), dict):
        return deepcopy(_BESTIARY_CACHE["payload"])

    payload = load_json(base / "spiritual_bestiary.json", default={})
    if not isinstance(payload, dict):
        payload = {}
    payload["_index"] = _build_indexes(payload)

    _BESTIARY_CACHE["stamp"] = stamp
    _BESTIARY_CACHE["payload"] = deepcopy(payload)
    return payload


def _fallback_profile(entity_id: str, biome: str = "", tier: str = "", kind: str = "enemy") -> dict:
    tier_key = _safe_id(tier)
    biome_key = _safe_id(biome)
    kind_key = _safe_id(kind)

    if tier_key == "boss" or kind_key == "boss":
        return {
            "id": entity_id,
            "kind": "boss",
            "faction": "archons",
            "world": "uku_pacha",
            "motif": "archon",
            "palette": "crimson_ritual",
            "energy": "supreme_fracture",
        }
    if biome_key in {"hanan", "hanan_mountains"}:
        return {
            "id": entity_id,
            "kind": "enemy",
            "faction": "guardians",
            "world": "hanan_pacha",
            "motif": "guardian",
            "palette": "gold_cyan",
            "energy": "celestial",
        }
    if biome_key in {"kay", "kaypacha", "kay_valley"}:
        return {
            "id": entity_id,
            "kind": "enemy",
            "faction": "oracles",
            "world": "kay_pacha",
            "motif": "oracle",
            "palette": "violet_cyan",
            "energy": "living_ritual",
        }
    return {
        "id": entity_id,
        "kind": "enemy",
        "faction": "demons",
        "world": "uku_pacha",
        "motif": "demon",
        "palette": "red_black",
        "energy": "corruption",
    }


def resolve_entity_profile(entity_id: str, biome: str = "", tier: str = "", kind: str = "enemy", base: Path | None = None) -> dict:
    payload = load_spiritual_bestiary(base=base)
    index = payload.get("_index") if isinstance(payload, dict) else {}
    by_id = index.get("by_id") if isinstance(index, dict) else {}
    alias_to_id = index.get("alias_to_id") if isinstance(index, dict) else {}

    lookup_id = _safe_id(entity_id)
    canonical_id = alias_to_id.get(lookup_id, "") if isinstance(alias_to_id, dict) else ""
    row = by_id.get(canonical_id) if canonical_id and isinstance(by_id, dict) else None
    if isinstance(row, dict):
        resolved = dict(row)
        resolved.setdefault("id", canonical_id)
        return resolved

    return _fallback_profile(entity_id=entity_id, biome=biome, tier=tier, kind=kind)
