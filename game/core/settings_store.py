from __future__ import annotations

import json
from pathlib import Path

from game.core.paths import project_root

SETTINGS_PATH = project_root() / "settings.json"

DEFAULT_SETTINGS = {
    "sfx_volume": 0.7,
    "music_volume": 0.55,
    "music_muted": False,
    "timer_on": False,
    "turn_time": 30,
}


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        out = DEFAULT_SETTINGS.copy()
        out.update({k: data.get(k, v) for k, v in DEFAULT_SETTINGS.items()})
        return out
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(data: dict) -> None:
    out = DEFAULT_SETTINGS.copy()
    out.update({k: data.get(k, v) for k, v in DEFAULT_SETTINGS.items()})
    SETTINGS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
