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
        if raw == key:
            raw = self._humanize_missing_key(str(key or ""))
        try:
            rendered = str(raw).format(**kwargs)
        except Exception:
            rendered = str(raw)
        return self._normalize_display_text(rendered)

    def _normalize_display_text(self, text: str) -> str:
        out = str(text or "")
        fixes = {
            "C?dice": "Códice",
            "Codice Sagrado": "Códice Sagrado",
            "C?dice Sagrado": "Códice Sagrado",
            "Vac?o": "Vacío",
            "vac?o": "vacío",
            "geometr?a": "geometría",
            "presi?n": "presión",
            "profecia": "profecía",
            "profec?a": "profecía",
            "armonia": "armonía",
            "armon?a": "armonía",
            "civilizacion": "civilización",
            "civilizaci?n": "civilización",
            "Oraculo": "Oráculo",
            "Or?culo": "Oráculo",
            "oraculo": "oráculo",
            "or?culo": "oráculo",
        }
        for bad, good in fixes.items():
            out = out.replace(bad, good)
        return out

    def _humanize_missing_key(self, key: str) -> str:
        k = str(key or "").strip()
        if not k:
            return ""
        low = k.lower()
        if " " in k:
            return k

        fixed = {
            "menu_play": "Iniciar Travesia",
            "menu_continue": "Continuar Travesia",
            "menu_codex": "C\u00f3dice Sagrado",
            "menu_settings": "Ajustes",
            "menu_back": "Volver",
            "intent_attack": "Golpe Ritual",
            "intent_defend": "Velo Protector",
            "intent_debuff": "Influencia Oscura",
            "intent_buff": "Bendicion Arcana",
            "draw": "Revelacion",
            "discard": "Ecos",
            "damage": "Impacto",
            "energy": "Energia",
            "buff": "Bendicion",
            "debuff": "Maldicion",
        }
        if low in fixed:
            return fixed[low]

        if low.startswith("enemy_") and low.endswith("_name"):
            core = low.removeprefix("enemy_").removesuffix("_name").replace("_", " ").title()
            return core
        if low.startswith("relic_") and low.endswith("_name"):
            core = low.removeprefix("relic_").removesuffix("_name").replace("_", " ").title()
            return core
        if low.startswith("card_") and low.endswith("_name"):
            core = low.removeprefix("card_").removesuffix("_name").replace("_", " ").title()
            return core

        if low.startswith("hip_"):
            toks = low.split("_")
            roman = ""
            if toks and toks[-1].isdigit():
                idx = int(toks[-1])
                roman_map = {
                    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
                    6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
                    11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
                    16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
                }
                roman = roman_map.get(idx, str(idx))
                toks = toks[:-1]
            core = " ".join(toks[1:]).replace("cosmic warrior", "Guerrero Cosmico").replace("harmony guardian", "Guardian de Armonia").replace("oracle of fate", "Oraculo del Destino").replace("_", " ")
            core = core.title()
            return f"{core} de Hiperborea {roman}".strip()

        if "_" in k:
            return k.replace("_", " ").title()
        return k
