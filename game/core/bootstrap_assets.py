"""Generate optional placeholder assets so game runs OOTB."""

from __future__ import annotations

import json
import math
import random
import struct
import wave
import zlib
from pathlib import Path

from game.core.paths import assets_dir, data_dir


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
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        buf = bytearray()
        for i in range(frames):
            v = int(32767 * volume * math.sin((2 * math.pi * hz * i) / rate)) if volume > 0 else 0
            buf.extend(struct.pack("<h", v))
        wav.writeframes(bytes(buf))


def _profile(track_key: str):
    profiles = {
        "menu": {"scale": [0, 2, 4, 7, 9], "root": 130.81, "bpm": 92, "a": 12, "b": 10, "character": "ambient"},
        "map": {"scale": [0, 2, 3, 5, 7, 9, 10], "root": 98.0, "bpm": 96, "a": 10, "b": 10, "character": "journey"},
        "combat": {"scale": [0, 2, 3, 5, 7, 8, 10], "root": 110.0, "bpm": 108, "a": 12, "b": 10, "character": "driving"},
        "event": {"scale": [0, 1, 4, 5, 7, 8, 11], "root": 123.47, "bpm": 112, "a": 12, "b": 12, "character": "techno_ritual"},
        "reward": {"scale": [0, 2, 4, 7, 9], "root": 146.83, "bpm": 110, "a": 12, "b": 10, "character": "bright"},
        "boss": {"scale": [0, 1, 3, 5, 7, 8, 10], "root": 87.31, "bpm": 132, "a": 14, "b": 12, "character": "aggressive"},
        "ending": {"scale": [0, 2, 4, 7, 9], "root": 130.81, "bpm": 88, "a": 10, "b": 10, "character": "closure"},
    }
    return profiles.get(track_key, profiles["menu"])


def synth_ambient_music(path: Path, track_key: str, force: bool = False) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return {}

    profile = _profile(track_key)
    scale = profile["scale"]
    root = profile["root"]
    bpm = profile["bpm"]
    bars_a = profile["a"]
    bars_b = profile["b"]
    total_bars = max(16, min(32, bars_a + bars_b))
    bar_beats = 4
    sec_per_beat = 60.0 / bpm
    beats_per_bar = bar_beats
    duration = total_bars * beats_per_bar * sec_per_beat
    rate = 44100
    frames = int(rate * duration)
    rng = random.Random(f"{track_key}:{bpm}:{bars_a}:{bars_b}")

    def freq(deg: int, octv: int = 0):
        return root * (2 ** ((deg + 12 * octv) / 12.0))

    bass_patterns = [
        [0, 0, 4, 0],
        [0, 2, 4, 2],
        [0, 5, 4, 2],
        [0, 3, 5, 2],
    ]
    arp_patterns = [
        [0, 2, 4, 7, 4, 2, 0, 2],
        [0, 4, 7, 9, 7, 4, 2, 0],
        [0, 3, 5, 7, 10, 7, 5, 3],
    ]
    fill_patterns = [
        [0, 1, 0, 1, 0, 0, 1, 1],
        [1, 0, 1, 0, 1, 1, 0, 1],
        [0, 0, 1, 0, 0, 1, 1, 0],
    ]

    character = profile["character"]
    kick_amp = 0.2
    snare_amp = 0.12
    hat_amp = 0.06
    bell_amp = 0.0
    stab_amp = 0.0
    if character == "techno_ritual":
        kick_amp, snare_amp, hat_amp = 0.28, 0.17, 0.1
    elif character == "bright":
        bell_amp = 0.14
        kick_amp, snare_amp = 0.18, 0.1
    elif character == "aggressive":
        kick_amp, snare_amp, hat_amp, stab_amp = 0.32, 0.2, 0.11, 0.16

    two_pi = 2.0 * math.pi
    bar_len = int(rate * beats_per_bar * sec_per_beat)
    beat_len = int(rate * sec_per_beat)
    step8_len = max(1, beat_len // 2)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        buf = bytearray()

        for i in range(frames):
            t = i / rate
            bar = i // bar_len
            beat = (i // beat_len) % beats_per_bar
            step8 = (i // step8_len) % 8
            section = "A" if bar < bars_a else "B"
            variant = (bar // 4) % 4

            bass_seq = bass_patterns[(variant + (0 if section == "A" else 1)) % len(bass_patterns)]
            arp_seq = arp_patterns[(variant + (1 if section == "B" else 0)) % len(arp_patterns)]
            fill_seq = fill_patterns[variant % len(fill_patterns)]

            bass_deg = scale[bass_seq[beat] % len(scale)]
            arp_deg = scale[arp_seq[step8] % len(scale)]
            bass = 0.12 * math.sin(two_pi * freq(bass_deg, -1) * t)
            arp = 0.07 * math.sin(two_pi * freq(arp_deg, 0 if section == "A" else 1) * t)
            pad = 0.06 * math.sin(two_pi * freq(scale[(bar + 2) % len(scale)], -1) * t)

            kick_gate = 1.0 if (i % beat_len) < int(beat_len * 0.16) else 0.0
            snare_hit = 1.0 if beat in {1, 3} and (i % beat_len) < int(beat_len * 0.09) else 0.0
            if character == "techno_ritual" and beat == 2 and (i % beat_len) < int(beat_len * 0.06):
                snare_hit = 1.0
            hat_hit = 1.0 if step8 in {1, 3, 5, 7} else 0.0
            fill_hit = 1.0 if fill_seq[step8] and (bar % 4 == 3) else 0.0

            noise = rng.uniform(-1.0, 1.0)
            kick = kick_amp * kick_gate * math.sin(two_pi * 60 * t)
            snare = snare_amp * snare_hit * noise
            hat = hat_amp * hat_hit * noise * 0.45
            fill = 0.08 * fill_hit * noise

            bell = bell_amp * (1.0 if step8 in {0, 4} else 0.0) * math.sin(two_pi * freq(scale[(step8 + 2) % len(scale)], 1) * t)
            stab = stab_amp * (1.0 if beat in {0, 2} and section == "B" else 0.0) * math.sin(two_pi * freq(scale[(bar + beat) % len(scale)], 0) * t)

            mix = (bass + arp + pad + kick + snare + hat + fill + bell + stab) * 0.84
            pan = 0.08 * math.sin(two_pi * 0.07 * t)
            lv = max(-1.0, min(1.0, mix * (1.0 - pan)))
            rv = max(-1.0, min(1.0, mix * (1.0 + pan)))
            buf.extend(struct.pack("<hh", int(lv * 32767), int(rv * 32767)))

        wav.writeframes(buf)

    return {
        "track": track_key,
        "bpm": bpm,
        "bars_a": bars_a,
        "bars_b": bars_b,
        "total_bars": total_bars,
        "duration": round(duration, 2),
    }


def ensure_placeholder_assets(card_ids: list[str], enemy_ids: list[str]) -> None:
    a_dir = assets_dir()
    _write_png(a_dir / "sprites/player/player.png", 96, 96, (88, 70, 140))
    _write_png(a_dir / "sprites/cards/_placeholder.png", 320, 220, (64, 48, 110))
    _write_png(a_dir / "sprites/enemies/_placeholder.png", 160, 160, (95, 55, 95))

    sfx = {"ui_click": 880, "card_pick": 720, "card_play": 620, "hit": 200, "shield": 520, "exhaust": 310, "whisper": 430}
    for name, hz in sfx.items():
        _write_wav(a_dir / f"sfx/{name}.wav", hz=hz)

    ensure_bgm_assets(force_regen=False)


def ensure_bgm_assets(force_regen: bool = False) -> dict:
    a_dir = assets_dir()
    manifest = {}
    for name in ["menu", "map", "combat", "event", "reward", "boss", "ending"]:
        meta = synth_ambient_music(a_dir / f"music/{name}.wav", name, force=force_regen)
        if meta:
            manifest[name] = meta
    manifest_path = data_dir() / "bgm_manifest.json"
    if manifest:
        existing = {}
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}
        existing.update(manifest)
        manifest_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
