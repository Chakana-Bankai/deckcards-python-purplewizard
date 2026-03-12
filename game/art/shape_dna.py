from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from game.art.dna_loader import CardDnaModel, load_card_dna
from game.core.paths import project_root


@lru_cache(maxsize=1)
def _manifest_cards() -> list[str]:
    path = Path(project_root()) / 'data' / 'cards' / 'card_manifest.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'cards_by_set' in payload:
        out = []
        for ids in payload['cards_by_set'].values():
            out.extend(ids)
        return out
    return []


def load_identity_dataset() -> list[CardDnaModel]:
    return [load_card_dna(card_id) for card_id in _manifest_cards()]


def load_card_shape_dna(card_id: str) -> CardDnaModel:
    return load_card_dna(card_id)


def export_identity_dataset_summary(out_path: Path) -> dict[str, object]:
    dataset = load_identity_dataset()
    summary = {
        'count': len(dataset),
        'archetypes': {},
        'weapon_types': {},
        'energy_types': {},
        'pose_types': {},
    }
    for dna in dataset:
        for key, value in (
            ('archetypes', dna.archetype),
            ('weapon_types', dna.weapon_type),
            ('energy_types', dna.energy_type),
            ('pose_types', dna.pose_type),
        ):
            summary[key][value] = summary[key].get(value, 0) + 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary
