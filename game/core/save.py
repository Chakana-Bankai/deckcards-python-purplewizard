"""Simple JSON save helpers."""

from __future__ import annotations

import json
from pathlib import Path

SAVE_PATH = Path("savegame.json")


def save_run(data: dict) -> None:
    SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_run() -> dict | None:
    if not SAVE_PATH.exists():
        return None
    return json.loads(SAVE_PATH.read_text(encoding="utf-8"))
