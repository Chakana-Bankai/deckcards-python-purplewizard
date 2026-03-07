"""Centralized font loading with UTF-8 friendly fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pygame


_FONT_CACHE: Dict[Tuple[str, int], pygame.font.Font] = {}
_WARNED_FALLBACK: set[Tuple[str, int]] = set()


def _fonts_root() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "fonts"


def _fallback_chain(name: str):
    if name == "title":
        return ["dejavusans", "arial"]
    if name == "lore":
        return ["dejavuserif", "timesnewroman", "arial"]
    return ["dejavusans", "arial"]


def _warn(name: str, size: int, reason: str):
    key = (name, int(size))
    if key in _WARNED_FALLBACK:
        return
    _WARNED_FALLBACK.add(key)
    print(f"[fonts] warning: fallback font name={name} size={size} reason={reason}")


def get_font(name: str, size: int) -> pygame.font.Font:
    """Load a named font safely with system fallback and cache."""
    if not pygame.font.get_init():
        pygame.font.init()
    key = (name, int(size))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    root = _fonts_root()
    candidates = {
        "title": root / "title.ttf",
        "ui": root / "ui.ttf",
        "lore": root / "lore.ttf",
        "mono": root / "mono.ttf",
    }
    path = candidates.get(name)
    font = None
    if path is not None:
        try:
            if path.exists():
                font = pygame.font.Font(str(path), int(size))
            else:
                _warn(name, size, f"missing_file:{path.name}")
        except Exception as exc:
            _warn(name, size, f"font_load_error:{exc}")
            font = None
    if font is None:
        for fallback in _fallback_chain(name):
            try:
                font = pygame.font.SysFont(fallback, int(size))
                break
            except Exception as exc:
                _warn(name, size, f"sysfont_error:{fallback}:{exc}")
                font = None
    if font is None:
        _warn(name, size, "pygame_default")
        font = pygame.font.Font(None, int(size))

    _FONT_CACHE[key] = font
    return font


def get_title_font(size: int) -> pygame.font.Font:
    return get_font("title", size)


def get_ui_font(size: int) -> pygame.font.Font:
    return get_font("ui", size)


def get_lore_font(size: int) -> pygame.font.Font:
    return get_font("lore", size)

