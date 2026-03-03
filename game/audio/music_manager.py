from __future__ import annotations

from pathlib import Path
import pygame

from game.core.paths import assets_dir


class MusicManager:
    def __init__(self):
        self.volume = 0.55
        self.muted = False
        self.current_key = None
        self.tracks = {
            "menu": assets_dir() / "music" / "map.ogg",
            "map": assets_dir() / "music" / "map.ogg",
            "combat": assets_dir() / "music" / "combat.ogg",
            "event": assets_dir() / "music" / "event.ogg",
            "boss": assets_dir() / "music" / "boss.ogg",
        }

    def set_volume(self, value: float):
        self.volume = max(0.0, min(1.0, value))
        pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def set_muted(self, muted: bool):
        self.muted = muted
        pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def play_for(self, key: str):
        if key == self.current_key:
            return
        self.current_key = key
        path: Path | None = self.tracks.get(key)
        if not path or not path.exists():
            pygame.mixer.music.fadeout(250)
            return
        try:
            pygame.mixer.music.fadeout(250)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
            pygame.mixer.music.play(-1, fade_ms=500)
        except Exception:
            pass
