from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPRITE_ROOT = ROOT / "game" / "assets" / "sprites" / "cards"
OUTPUT_PATH = ROOT / "data" / "cards" / "card_manifest.json"
MAPPING_PATH = ROOT / "data" / "cards" / "card_id_mapping.json"

SOURCE_DATASETS = [
    ROOT / "game" / "data" / "cards.json",
    ROOT / "game" / "data" / "cards_arconte.json",
    ROOT / "game" / "data" / "cards_hiperboria.json",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dataset_cards(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("cards"), list):
        return payload["cards"]
    raise ValueError(f"Unsupported card dataset shape in {payload!r}")


def normalize_set_name(raw_set: str) -> str:
    lowered = (raw_set or "").strip().lower()
    if lowered == "hiperborea":
        return "hiperboria"
    return lowered


def main() -> None:
    mapping_payload = load_json(MAPPING_PATH)
    mapping_by_canonical = {
        record["canonical_id"]: record
        for record in mapping_payload.get("records", [])
    }

    cards: list[dict[str, Any]] = []
    set_counts: Counter[str] = Counter()
    archetype_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    cards_by_set: defaultdict[str, list[str]] = defaultdict(list)

    for dataset_path in SOURCE_DATASETS:
        payload = load_json(dataset_path)
        for card in dataset_cards(payload):
            canonical_id = card["id"]
            mapping = mapping_by_canonical.get(canonical_id, {})
            normalized_set = normalize_set_name(card.get("set") or mapping.get("set", ""))
            artwork = card.get("artwork", canonical_id)
            sprite_filename = f"{artwork}.png"
            sprite_path = SPRITE_ROOT / sprite_filename
            source_dataset = str(dataset_path.relative_to(ROOT)).replace("\\", "/")

            entry = {
                "id": canonical_id,
                "canonical_id": canonical_id,
                "legacy_id": card.get("legacy_id", mapping.get("legacy_id")),
                "set": normalized_set,
                "source_dataset": source_dataset,
                "name": card.get("name") or card.get("name_es"),
                "name_key": card.get("name_key"),
                "artwork": artwork,
                "legacy_artwork": card.get(
                    "legacy_artwork",
                    mapping.get("legacy_artwork"),
                ),
                "sprite_path": str(sprite_path.relative_to(ROOT)).replace("\\", "/"),
                "sprite_exists": sprite_path.exists(),
                "archetype": card.get("archetype"),
                "role": card.get("role"),
                "rarity": card.get("rarity"),
                "cost": card.get("cost"),
                "target": card.get("target"),
                "direction": card.get("direction"),
                "family": card.get("family"),
                "author": card.get("author"),
                "taxonomy": card.get("taxonomy"),
                "tags": card.get("tags", []),
                "effects": card.get("effects", []),
                "effect_text": card.get("effect_text") or card.get("text_key"),
                "text_key": card.get("text_key"),
                "lore_text": card.get("lore_text"),
                "source_order": card.get("order"),
                "mapping_source_dataset": mapping.get("source_dataset"),
            }

            cards.append(entry)
            set_counts[normalized_set] += 1
            archetype_counts[entry["archetype"]] += 1
            role_counts[entry["role"]] += 1
            source_counts[source_dataset] += 1
            cards_by_set[normalized_set].append(canonical_id)

    cards.sort(key=lambda item: item["id"])

    output = {
        "version": "chakana_card_manifest_v2",
        "id_scheme": "SET-ARCHETYPE-TYPE-NAME",
        "count": len(cards),
        "source_datasets": [
            str(path.relative_to(ROOT)).replace("\\", "/") for path in SOURCE_DATASETS
        ],
        "mapping_file": str(MAPPING_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sets": dict(sorted(set_counts.items())),
        "archetypes": dict(sorted(archetype_counts.items())),
        "roles": dict(sorted(role_counts.items())),
        "sources": dict(sorted(source_counts.items())),
        "cards_by_set": dict(sorted(cards_by_set.items())),
        "cards": cards,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()

