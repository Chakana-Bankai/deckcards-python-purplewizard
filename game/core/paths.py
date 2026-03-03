"""Path helpers independent of cwd."""

from __future__ import annotations

from pathlib import Path


def game_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    return game_dir().parent


def data_dir() -> Path:
    return game_dir() / "data"


def assets_dir() -> Path:
    return game_dir() / "assets"


def lang_dir() -> Path:
    return data_dir() / "lang"
