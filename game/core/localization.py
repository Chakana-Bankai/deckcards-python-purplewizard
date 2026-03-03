"""Localization manager."""

from __future__ import annotations

import json
from pathlib import Path

from game.settings import DATA_DIR, DEFAULT_LANG


class LocalizationManager:
    def __init__(self, lang: str = DEFAULT_LANG):
        self.current_lang = lang
        self.translations: dict[str, str] = {}
        self.load(lang)

    def load(self, lang_code: str) -> None:
        path = Path(DATA_DIR) / "lang" / f"{lang_code}.json"
        if path.exists():
            self.translations = json.loads(path.read_text(encoding="utf-8"))
            self.current_lang = lang_code
        else:
            print(f"[loc] missing lang file: {path}")

    def t(self, key: str, **kwargs) -> str:
        raw = self.translations.get(key, key)
        try:
            return raw.format(**kwargs)
        except Exception:
            return raw
