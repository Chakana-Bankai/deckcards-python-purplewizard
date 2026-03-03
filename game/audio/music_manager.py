from __future__ import annotations

from pathlib import Path
import pygame

from game.core.paths import assets_dir


class MusicManager:
    def __init__(self):
        self.volume = 0.55
        self.muted = False
        self.current_key = None
        self.current_path = None
        self.status = "stopped"
        music_dir = assets_dir() / "music"
        self.tracks = {
            "menu": [music_dir / "menu.ogg", music_dir / "menu.wav"],
            "map": [music_dir / "map.ogg", music_dir / "map.wav"],
            "combat": [music_dir / "combat.ogg", music_dir / "combat.wav"],
            "event": [music_dir / "event.ogg", music_dir / "event.wav"],
            "boss": [music_dir / "boss.ogg", music_dir / "boss.wav"],
        }

    def set_volume(self, value: float):
        self.volume = max(0.0, min(1.0, value))
        pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def set_muted(self, muted: bool):
        self.muted = muted
        pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)

    def _find_track(self, key: str) -> Path | None:
        for candidate in self.tracks.get(key, []):
            if candidate.exists():
                return candidate
        return None

    def play_for(self, key: str):
        if key == self.current_key:
            return
        self.current_key = key
        path = self._find_track(key)
        if not path:
            self.current_path = None
            self.status = "missing"
            print(f"[audio] BGM missing for {key}")
            pygame.mixer.music.fadeout(250)
            return
        self.current_path = path.name
        try:
            pygame.mixer.music.fadeout(250)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
            pygame.mixer.music.play(-1, fade_ms=700)
            self.status = "playing"
            print(f"[audio] BGM -> {key} ({path.name})")
        except Exception as exc:
            self.status = f"error:{exc}"
            print(f"[audio] BGM error: {exc}")

    def debug_state(self) -> str:
        return f"{self.current_key or '-'} {self.current_path or 'missing'} {self.status} vol={self.volume:.2f}"
