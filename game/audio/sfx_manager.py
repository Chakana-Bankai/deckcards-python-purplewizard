from __future__ import annotations

from game.audio.audio_engine import get_audio_engine


class SFXManager:
    """Compatibility wrapper around AudioEngine for legacy SFX callers."""

    def __init__(self):
        self.engine = get_audio_engine()
        self.master_volume = 0.7
        self.stinger_volume = 0.8

    def set_volume(self, value: float):
        self.master_volume = max(0.0, min(1.0, float(value)))
        self.engine.set_sfx_volume(self.master_volume)

    def set_stinger_volume(self, value: float):
        self.stinger_volume = max(0.0, min(1.0, float(value)))
        if hasattr(self.engine, "set_stinger_volume"):
            self.engine.set_stinger_volume(self.stinger_volume)

    def play(self, name: str):
        self.engine.play_sfx(name)
