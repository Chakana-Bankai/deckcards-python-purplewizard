from __future__ import annotations

import json

from game.core.paths import data_dir
from game.core.safe_io import load_json

SETTINGS_PATH = data_dir() / "settings.json"

DEFAULT_SETTINGS = {
    "language": "es",
    "music_volume": 0.5,
    "sfx_volume": 0.7,
    "fullscreen": False,
    "turn_timer_enabled": True,
    "turn_timer_seconds": 20,
    "music_muted": False,
    "music_mute": False,
    "autogen_art_mode": "missing_only",
}


def _normalize(raw: dict) -> dict:
    data = DEFAULT_SETTINGS.copy()
    data.update(raw or {})
    # backward compatibility
    if "timer_on" in raw:
        data["turn_timer_enabled"] = bool(raw.get("timer_on"))
    if "turn_time" in raw:
        data["turn_timer_seconds"] = int(raw.get("turn_time") or 30)
    if "music_mute" in raw and "music_muted" not in raw:
        data["music_muted"] = bool(raw.get("music_mute"))
    data["music_mute"] = bool(data.get("music_muted", False))
    return data


def ensure_settings_file() -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_SETTINGS.copy()
    loaded = load_json(SETTINGS_PATH, default={})
    normalized = _normalize(loaded if isinstance(loaded, dict) else {})
    SETTINGS_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def load_settings() -> dict:
    return ensure_settings_file()


def save_settings(data: dict) -> None:
    normalized = _normalize(data if isinstance(data, dict) else {})
    SETTINGS_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
