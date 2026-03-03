from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pygame

from game.core.bootstrap_assets import synth_ambient_music
from game.core.paths import assets_dir


class MusicManager:
    def __init__(self):
        self.volume = 0.5
        self.muted = False
        self.current_key = None
        self.current_path = None
        self.status = "stopped"
        self._checked_silence: set[str] = set()
        music_dir = assets_dir() / "music"
        self.tracks = {
            "menu": [music_dir / "menu.ogg", music_dir / "menu.wav"],
            "map": [music_dir / "map.ogg", music_dir / "map.wav"],
            "combat": [music_dir / "combat.ogg", music_dir / "combat.wav"],
            "event": [music_dir / "event.ogg", music_dir / "event.wav"],
            "boss": [music_dir / "boss.ogg", music_dir / "boss.wav"],
        }

    def set_volume(self, value: float):
        self.volume = max(0.0, min(1.0, float(value)))
        try:
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
        except Exception:
            pass

    def set_muted(self, muted: bool):
        self.muted = bool(muted)
        try:
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
        except Exception:
            pass

    def _find_track(self, key: str) -> Path | None:
        for candidate in self.tracks.get(key, []):
            if candidate.exists():
                return candidate
        return None

    def _wav_levels(self, path: Path) -> tuple[float, float]:
        try:
            with wave.open(str(path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                n_frames = min(wf.getnframes(), 44100 * 3)
                raw = wf.readframes(n_frames)
            if sampwidth != 2 or not raw:
                return 0.0, 0.0
            count = len(raw) // 2
            samples = struct.unpack("<" + "h" * count, raw)
            if n_channels > 1:
                vals = samples[::n_channels]
            else:
                vals = samples
            if not vals:
                return 0.0, 0.0
            peak = max(abs(v) for v in vals) / 32767.0
            rms = math.sqrt(sum((v / 32767.0) ** 2 for v in vals) / len(vals))
            return rms, peak
        except Exception:
            return 0.0, 0.0

    def _ensure_audible_wav(self, key: str, path: Path) -> Path:
        p = str(path)
        if p in self._checked_silence:
            return path
        self._checked_silence.add(p)
        if path.suffix.lower() != ".wav":
            return path
        rms, peak = self._wav_levels(path)
        if rms < 0.002 or peak < 0.01:
            print(f"[audio] BGM silent: {key} (regenerated)")
            synth_ambient_music(path, key, force=True)
        return path

    def _ensure_track(self, key: str) -> Path:
        path = self._find_track(key)
        if path is None:
            generated = assets_dir() / "music" / f"{key}.wav"
            synth_ambient_music(generated, key, force=True)
            print(f"[audio] BGM missing: {key} (generated placeholder)")
            return generated
        return self._ensure_audible_wav(key, path)

    def play_for(self, key: str):
        if key == self.current_key and pygame.mixer.music.get_busy():
            return
        self.current_key = key
        path = self._ensure_track(key)
        self.current_path = path.name
        try:
            pygame.mixer.music.fadeout(500)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
            pygame.mixer.music.play(-1, fade_ms=700)
            self.status = "playing" if pygame.mixer.music.get_busy() else "started"
            print(f"[audio] BGM play: track={key}, vol={self.volume:.2f}, mute={self.muted}, ok")
        except Exception as exc:
            self.status = f"error:{exc}"
            print(f"[audio] BGM error: {exc}")

    def debug_state(self) -> str:
        busy = pygame.mixer.music.get_busy() if pygame.mixer.get_init() else False
        return f"track={self.current_key or '-'} vol={self.volume:.2f} playing={busy} mute={self.muted} state={self.status}"
