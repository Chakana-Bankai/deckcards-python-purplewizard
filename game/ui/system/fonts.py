"""Centralized font loading with UTF-8 friendly fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pygame


_FONT_CACHE: Dict[Tuple[str, int], pygame.font.Font] = {}
_WARNED_FALLBACK: set[Tuple[str, str]] = set()


def _fonts_root() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "fonts"


def _fallback_chain(name: str):
    # Engine-safe: avoid OS/system font dependency for deterministic visual identity.
    _ = name
    return []


def _warn(name: str, size: int, reason: str):
    reason_key = str(reason).split(":", 1)[0]
    key = (name, reason_key)
    if key in _WARNED_FALLBACK:
        return
    _WARNED_FALLBACK.add(key)
    print(f"[fonts] warning: fallback font name={name} size={size} reason={reason}")


def _candidates(root: Path) -> dict[str, tuple[Path, ...]]:
    # New personalized pipeline first, legacy names second.
    return {
        "title": (root / "chakana_title.ttf", root / "title.ttf"),
        "ui": (root / "chakana_ui.ttf", root / "chakana_pixel.ttf", root / "ui.ttf"),
        "lore": (root / "chakana_lore.ttf", root / "lore.ttf"),
        "mono": (root / "chakana_mono.ttf", root / "mono.ttf", root / "chakana_ui.ttf"),
    }


def get_font(name: str, size: int) -> pygame.font.Font:
    """Load a named font safely with system fallback and cache."""
    if not pygame.font.get_init():
        pygame.font.init()
    key = (name, int(size))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    root = _fonts_root()
    font = None
    for path in _candidates(root).get(name, ()):
        try:
            if path.exists():
                font = pygame.font.Font(str(path), int(size))
                break
            _warn(name, size, f"missing_file:{path.name}")
        except Exception as exc:
            _warn(name, size, f"font_load_error:{path.name}:{exc}")
            font = None

    if font is None:
        # No system-font probing: go directly to pygame default fallback.
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
