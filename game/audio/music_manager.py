from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

import pygame

from game.core.bootstrap_assets import synth_ambient_music
from game.core.paths import assets_dir, data_dir


class MusicManager:
    def __init__(self):
        self.volume = 0.5
        self.muted = False
        self.current_key = None
        self.current_path = None
        self.status = "stopped"
        self.current_bpm = 0
        self.current_section = "-"
        self.current_seconds = 0.0
        self._checked_silence: set[str] = set()
        self._manifest = self._load_manifest()
        music_dir = assets_dir() / "music"
        self.tracks = {
            "menu": [music_dir / "menu.ogg", music_dir / "menu.wav"],
            "map_kaypacha": [music_dir / "map_kaypacha.ogg", music_dir / "map_kaypacha.wav"],
            "map_forest": [music_dir / "map_forest.ogg", music_dir / "map_forest.wav"],
            "map_umbral": [music_dir / "map_umbral.ogg", music_dir / "map_umbral.wav"],
            "map_hanan": [music_dir / "map_hanan.ogg", music_dir / "map_hanan.wav"],
            "combat_kaypacha": [music_dir / "combat_kaypacha.ogg", music_dir / "combat_kaypacha.wav"],
            "combat_forest": [music_dir / "combat_forest.ogg", music_dir / "combat_forest.wav"],
            "combat_umbral": [music_dir / "combat_umbral.ogg", music_dir / "combat_umbral.wav"],
            "combat_hanan": [music_dir / "combat_hanan.ogg", music_dir / "combat_hanan.wav"],
            "event": [music_dir / "event.ogg", music_dir / "event.wav"],
            "victory": [music_dir / "victory.ogg", music_dir / "victory.wav"],
            "chest": [music_dir / "chest.ogg", music_dir / "chest.wav"],
            "boss": [music_dir / "boss.ogg", music_dir / "boss.wav"],
            "ending": [music_dir / "ending.ogg", music_dir / "ending.wav"],
        }

    def _load_manifest(self) -> dict:
        path = data_dir() / "bgm_manifest.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

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
            vals = samples[::n_channels] if n_channels > 1 else samples
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
            print(f"[audio] BGM silent: {key} (using existing file)")
            print(f"[audio] BGM silent: {key} (regenerated)")
            synth_ambient_music(path, key, force=True)

        return path

    def _ensure_track(self, key: str) -> Path:
        path = self._find_track(key)
        if path is None:
            generated = assets_dir() / "music" / f"{key}.wav"
            synth_ambient_music(generated, key, force=True)
            print(f"[audio] BGM missing: {key} (generated placeholder)")
            generated = assets_dir() / ".cache" / "music" / f"{key}.wav"
            generated.parent.mkdir(parents=True, exist_ok=True)
            synth_ambient_music(generated, key, force=True)
            print(f"[audio] BGM missing: {key} (generated cache placeholder)")
            self._manifest = self._load_manifest()
            return generated
        return self._ensure_audible_wav(key, path)

    def play_for(self, key: str):
        self.tick()
        if key == self.current_key and pygame.mixer.music.get_busy():
            return
        self.current_key = key
        path = self._ensure_track(key)
        self.current_path = path.name
        self.current_bpm = int(self._manifest.get(key, {}).get("bpm", 0) or 0)
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(800)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.0 if self.muted else self.volume)
            pygame.mixer.music.play(-1, fade_ms=900)
            self.status = "playing" if pygame.mixer.music.get_busy() else "started"
            self.current_seconds = 0.0
            self.current_section = "A"
            print(f"[audio] BGM play: track={key}, vol={self.volume:.2f}, mute={self.muted}, ok")
        except Exception as exc:
            self.status = f"error:{exc}"
            print(f"[audio] BGM error: {exc}")

    def tick(self):
        pos_ms = pygame.mixer.music.get_pos() if pygame.mixer.get_init() else -1
        self.current_seconds = max(0.0, pos_ms / 1000.0) if pos_ms >= 0 else 0.0
        meta = self._manifest.get(self.current_key or "", {})
        intro_bars = int(meta.get("intro_bars", meta.get("bars_a", 8)) or 8)
        bpm = float(meta.get("bpm", self.current_bpm or 100) or 100)
        if bpm <= 0:
            self.current_section = "-"
            return
        bar_sec = 4 * (60.0 / bpm)
        self.current_section = "intro" if self.current_seconds < intro_bars * bar_sec else "loop"

    def debug_state(self) -> str:
        self.tick()
        busy = pygame.mixer.music.get_busy() if pygame.mixer.get_init() else False
        return f"track={self.current_key or '-'} sec={self.current_seconds:05.1f} section={self.current_section} bpm={self.current_bpm or '-'} vol={self.volume:.2f} playing={busy} mute={self.muted}"
