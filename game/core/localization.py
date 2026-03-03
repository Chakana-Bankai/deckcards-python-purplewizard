"""Localization manager."""

from __future__ import annotations

from game.core.paths import lang_dir
from game.core.safe_io import load_json
from game.settings import DEFAULT_LANG


class LocalizationManager:
    def __init__(self, lang: str = DEFAULT_LANG):
        self.current_lang = lang
        self.translations: dict[str, str] = {}
        self.load(lang)

    def load(self, lang_code: str) -> None:
        path = lang_dir() / f"{lang_code}.json"
        loaded = load_json(path, default={})
        if not loaded and lang_code != DEFAULT_LANG:
            fallback_path = lang_dir() / f"{DEFAULT_LANG}.json"
            loaded = load_json(fallback_path, default={})
            lang_code = DEFAULT_LANG
        self.translations = loaded if isinstance(loaded, dict) else {}
        self.current_lang = lang_code

    def t(self, key: str, **kwargs) -> str:
        raw = self.translations.get(key, key)
        try:
            return str(raw).format(**kwargs)
        except Exception:
            return str(raw)
