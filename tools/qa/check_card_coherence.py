from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.services.card_coherence import validate_cards_coherence


def main() -> int:
    cards = load_json(data_dir() / "cards.json", default=[])
    if not isinstance(cards, list):
        print("[card_coherence] invalid cards payload")
        return 1
    report = validate_cards_coherence(cards)
    print(f"[card_coherence] checked={report['checked']} errors={report['errors']} warnings={report['warnings']}")
    if report["issues"]:
        print(json.dumps(report["issues"][:20], ensure_ascii=False, indent=2))
    return 0 if report["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

