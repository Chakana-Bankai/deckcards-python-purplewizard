"""Centralized font loading with UTF-8 friendly fallbacks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

import pygame


_FONT_CACHE: Dict[Tuple[str, int], pygame.font.Font] = {}
_WARNED_FALLBACK: set[Tuple[str, str]] = set()
_DEBUG = str(os.environ.get("CHAKANA_FONT_DEBUG", "0")).strip() in {"1", "true", "yes"}
_FONT_STATS = {
    "loaded": 0,
    "fallback": 0,
    "sources": {},
}


def set_font_debug(enabled: bool):
    global _DEBUG
    _DEBUG = bool(enabled)


def get_font_stats() -> dict:
    return {
        "loaded": int(_FONT_STATS.get("loaded", 0)),
        "fallback": int(_FONT_STATS.get("fallback", 0)),
        "sources": dict(_FONT_STATS.get("sources", {})),
    }


def _fonts_root() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "fonts"


def _warn(name: str, size: int, reason: str):
    reason_key = str(reason).split(":", 1)[0]
    key = (name, reason_key)
    if key in _WARNED_FALLBACK:
        return
    _WARNED_FALLBACK.add(key)
    print(f"[fonts] warning: fallback font name={name} size={size} reason={reason}")


def _debug_loaded(name: str, size: int, source: str):
    _FONT_STATS["loaded"] = int(_FONT_STATS.get("loaded", 0)) + 1
    src = dict(_FONT_STATS.get("sources", {}))
    src[source] = int(src.get(source, 0)) + 1
    _FONT_STATS["sources"] = src
    if _DEBUG:
        print(f"[fonts] loaded name={name} size={size} source={source}")


def _candidates(root: Path) -> dict[str, tuple[Path, ...]]:
    return {
        "title": (root / "chakana_title.ttf", root / "title.ttf"),
        "ui": (root / "chakana_ui.ttf", root / "chakana_pixel.ttf", root / "ui.ttf"),
        "lore": (root / "chakana_lore.ttf", root / "lore.ttf"),
        "mono": (root / "chakana_mono.ttf", root / "mono.ttf", root / "chakana_ui.ttf"),
    }


def get_font(name: str, size: int) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    key = (name, int(size))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    root = _fonts_root()
    font = None
    source = ""
    for path in _candidates(root).get(name, ()):  # prioritized
        try:
            if path.exists():
                font = pygame.font.Font(str(path), int(size))
                source = str(path.name)
                break
            _warn(name, size, f"missing_file:{path.name}")
        except Exception as exc:
            _warn(name, size, f"font_load_error:{path.name}:{exc}")
            font = None

    if font is None:
        _warn(name, size, "pygame_default")
        _FONT_STATS["fallback"] = int(_FONT_STATS.get("fallback", 0)) + 1
        font = pygame.font.Font(None, int(size))
        source = "pygame_default"

    _FONT_CACHE[key] = font
    _debug_loaded(name, size, source)
    return font


def get_title_font(size: int) -> pygame.font.Font:
    return get_font("title", size)


def get_ui_font(size: int) -> pygame.font.Font:
    return get_font("ui", size)


def get_lore_font(size: int) -> pygame.font.Font:
    return get_font("lore", size)
