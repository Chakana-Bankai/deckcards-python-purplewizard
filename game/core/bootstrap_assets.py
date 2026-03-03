"""Generate optional placeholder assets so game runs OOTB."""

from __future__ import annotations

import math
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
            v = int(32767 * volume * math.sin((2 * math.pi * hz * i) / rate))
            buf.extend(struct.pack("<h", v))
        wav.writeframes(bytes(buf))


def ensure_placeholder_assets(card_ids: list[str], enemy_ids: list[str]) -> None:
    a_dir = assets_dir()
    _write_png(a_dir / "sprites/player/player.png", 96, 96, (88, 70, 140))
    _write_png(a_dir / "sprites/cards/_placeholder.png", 160, 220, (64, 48, 110))
    _write_png(a_dir / "sprites/enemies/_placeholder.png", 120, 120, (95, 55, 95))
    for cid in card_ids:
        _write_png(a_dir / f"sprites/cards/{cid}.png", 160, 220, (78, 52, 132))
    for eid in enemy_ids:
        _write_png(a_dir / f"sprites/enemies/{eid}.png", 120, 120, (102, 64, 84))

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
