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


def curated_assets_dir() -> Path:
    return assets_dir() / "curated"


def curated_avatars_dir() -> Path:
    return curated_assets_dir() / "avatars"


def curated_audio_dir() -> Path:
    return curated_assets_dir() / "audio"


def fonts_dir() -> Path:
    return assets_dir() / "fonts"


def sprites_dir() -> Path:
    return assets_dir() / "sprites"


def sprite_category_dir(category: str) -> Path:
    return sprites_dir() / str(category or "").strip().lower()


def visual_dir() -> Path:
    return game_dir() / "visual"


def visual_generated_dir() -> Path:
    return visual_dir() / "generated"


def visual_generated_category_dir(category: str) -> Path:
    return visual_generated_dir() / str(category or "").strip().lower()


def audio_dir() -> Path:
    return game_dir() / "audio"


def audio_generated_dir() -> Path:
    return audio_dir() / "generated"


def audio_generated_category_dir(category: str) -> Path:
    return audio_generated_dir() / str(category or "").strip().lower()


def assets_archive_dir() -> Path:
    return project_root() / "assets" / "_archive"


def art_reference_dir() -> Path:
    return project_root() / "assets" / "art_reference"
