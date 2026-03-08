from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.services.combat_content_validator import validate_combat_content_lock


def main() -> int:
    cards = load_json(data_dir() / "cards.json", default=[])
    relics = load_json(data_dir() / "relics.json", default=[])
    codex_cards = load_json(data_dir() / "codex_cards_lore_set1.json", default={})
    codex_relics = load_json(data_dir() / "codex_relics_lore_set1.json", default={})
    lang_es = load_json(data_dir() / "lang" / "es.json", default={})
    lang_en = load_json(data_dir() / "lang" / "en.json", default={})

    report = validate_combat_content_lock(cards, relics, codex_cards, codex_relics, lang_es=lang_es, lang_en=lang_en)
    print(
        f"[combat_content_lock] status={report.get('status')} cards={report.get('cards')} "
        f"relics={report.get('relics')} issues={len(report.get('issues', []))} warnings={len(report.get('warnings', []))}"
    )
    if report.get("issues"):
        print(json.dumps(report["issues"][:25], ensure_ascii=False, indent=2))
    if report.get("warnings"):
        print(json.dumps(report["warnings"][:25], ensure_ascii=False, indent=2))
    return 0 if not report.get("issues") else 2


if __name__ == "__main__":
    raise SystemExit(main())
