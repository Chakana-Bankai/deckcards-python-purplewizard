"""Generate optional placeholder assets so game runs OOTB."""

from __future__ import annotations

import math
import random
import struct
import wave
import zlib
from pathlib import Path

from game.core.paths import assets_dir


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _write_png(path: Path, w: int, h: int, rgb: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    r, g, b = rgb
    row = bytes([0] + [r, g, b] * w)
    data = row * h
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    comp = zlib.compress(data)
    path.write_bytes(PNG_HEADER + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", comp) + _png_chunk(b"IEND", b""))


def _write_wav(path: Path, hz: int = 440, ms: int = 120, volume: float = 0.15) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    rate = 22050
    frames = int(rate * (ms / 1000.0))
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        buf = bytearray()
        for i in range(frames):
            v = int(32767 * volume * math.sin((2 * math.pi * hz * i) / rate)) if volume > 0 else 0
            buf.extend(struct.pack("<h", v))
        wav.writeframes(bytes(buf))


def synth_ambient_music(path: Path, track_key: str, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return

    configs = {
        "menu": (25.0, (130.81, 196.00, 261.63)),
        "map": (28.0, (98.00, 146.83, 220.00)),
        "combat": (26.0, (110.00, 164.81, 246.94)),
        "event": (30.0, (123.47, 174.61, 233.08)),
        "boss": (32.0, (87.31, 130.81, 196.00)),
    }
    duration, freqs = configs.get(track_key, (25.0, (130.81, 196.00, 261.63)))
    rate = 44100
    frames = int(rate * duration)
    rng = random.Random(track_key)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)

        buf = bytearray()
        two_pi = 2.0 * math.pi
        for i in range(frames):
            t = i / rate
            env = 0.65 + 0.35 * math.sin(two_pi * 0.03 * t)
            pad = 0.0
            for idx, f in enumerate(freqs):
                pad += (0.14 - idx * 0.02) * math.sin(two_pi * f * t + idx * 0.7)

            bell = 0.0
            if i % (rate * 2) == 0:
                pass
            bell += 0.06 * math.sin(two_pi * (freqs[2] * 2.0) * t) * (0.5 + 0.5 * math.sin(two_pi * 0.21 * t))

            noise = (rng.random() * 2.0 - 1.0) * 0.012
            left = (pad * env + bell + noise) * 0.85
            right = (pad * env + bell - noise) * 0.85

            lv = max(-1.0, min(1.0, left))
            rv = max(-1.0, min(1.0, right))
            buf.extend(struct.pack("<hh", int(lv * 32767), int(rv * 32767)))

        wav.writeframes(buf)


def ensure_placeholder_assets(card_ids: list[str], enemy_ids: list[str]) -> None:
    a_dir = assets_dir()
    _write_png(a_dir / "sprites/player/player.png", 96, 96, (88, 70, 140))
    _write_png(a_dir / "sprites/cards/_placeholder.png", 320, 220, (64, 48, 110))
    _write_png(a_dir / "sprites/enemies/_placeholder.png", 160, 160, (95, 55, 95))

    sfx = {
        "ui_click": 880,
        "card_pick": 720,
        "card_play": 620,
        "hit": 200,
        "shield": 520,
        "exhaust": 310,
    }
    for name, hz in sfx.items():
        _write_wav(a_dir / f"sfx/{name}.wav", hz=hz)

    ensure_bgm_assets(force_regen=False)


def ensure_bgm_assets(force_regen: bool = False) -> None:
    a_dir = assets_dir()
    for name in ["menu", "map", "combat", "event", "boss", "ending"]:
        synth_ambient_music(a_dir / f"music/{name}.wav", name if name != "ending" else "event", force=force_regen)
