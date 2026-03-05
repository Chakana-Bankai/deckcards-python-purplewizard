from __future__ import annotations

import json
<<<<<<< ours
=======
import shutil
from pathlib import Path
>>>>>>> theirs

from game.core.paths import data_dir
from game.core.safe_io import load_json

SETTINGS_PATH = data_dir() / "settings.json"
<<<<<<< ours
=======
DEFAULT_SETTINGS_PATH = data_dir() / "settings.default.json"
>>>>>>> theirs

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
    "dev_reset_autogen_on_boot": False,
    "fx_vignette": True,
    "fx_scanlines": False,
    "fx_glow": True,
    "fx_particles": True,
    "force_regen_art": False,
    "detail_panel": False,
}


def _normalize(raw: dict) -> dict:
<<<<<<< ours
    data = DEFAULT_SETTINGS.copy()
    data.update(raw or {})
    # backward compatibility
    if "timer_on" in raw:
        data["turn_timer_enabled"] = bool(raw.get("timer_on"))
    if "turn_time" in raw:
        data["turn_timer_seconds"] = int(raw.get("turn_time") or 30)
    if "music_mute" in raw and "music_muted" not in raw:
        data["music_muted"] = bool(raw.get("music_mute"))
=======
    source = raw if isinstance(raw, dict) else {}
    data = DEFAULT_SETTINGS.copy()
    data.update(source)
    # backward compatibility
    if "timer_on" in source:
        data["turn_timer_enabled"] = bool(source.get("timer_on"))
    if "turn_time" in source:
        data["turn_timer_seconds"] = int(source.get("turn_time") or 30)
    if "music_mute" in source and "music_muted" not in source:
        data["music_muted"] = bool(source.get("music_mute"))
>>>>>>> theirs
    data["music_mute"] = bool(data.get("music_muted", False))
    return data


<<<<<<< ours
def ensure_settings_file() -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_SETTINGS.copy()
    loaded = load_json(SETTINGS_PATH, default={})
    normalized = _normalize(loaded if isinstance(loaded, dict) else {})
    SETTINGS_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized
=======
def _ensure_default_settings_file() -> None:
    DEFAULT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_SETTINGS_PATH.exists():
        return
    DEFAULT_SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_settings_file() -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_default_settings_file()

    if not SETTINGS_PATH.exists():
        try:
            shutil.copyfile(DEFAULT_SETTINGS_PATH, SETTINGS_PATH)
        except Exception:
            SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = load_json(SETTINGS_PATH, default={})
    return _normalize(loaded if isinstance(loaded, dict) else {})
>>>>>>> theirs


def load_settings() -> dict:
    return ensure_settings_file()


def save_settings(data: dict) -> None:
<<<<<<< ours
=======
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
>>>>>>> theirs
    normalized = _normalize(data if isinstance(data, dict) else {})
    SETTINGS_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
