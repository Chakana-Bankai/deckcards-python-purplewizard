from __future__ import annotations

from game.audio.audio_engine import get_audio_engine


class MusicManager:
    """Compatibility wrapper around AudioEngine for legacy callers."""

    def __init__(self):
        self.engine = get_audio_engine()
        self.volume = 0.5
        self.muted = False
        self.current_key = None
        self.current_path = None
        self.status = "stopped"

    def set_volume(self, value: float):
        self.volume = max(0.0, min(1.0, float(value)))
        self.engine.set_music_volume(self.volume)

    def set_muted(self, muted: bool):
        self.muted = bool(muted)
        self.engine.set_muted(self.muted)

    def play_for(self, key: str):
        self.current_key = str(key or "menu")
        self.engine.play_context(self.current_key)
        self.current_path = self.engine.current_path
        self.status = self.engine.status

    def tick(self):
        self.engine.tick()
        self.status = self.engine.status
        self.current_path = self.engine.current_path

    def debug_state(self) -> str:
        return self.engine.debug_state()
