from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
import wave
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game" / "data"
ASSETS = ROOT / "game" / "assets"


def _load_cards() -> list[dict]:
    try:
        cards = json.loads((DATA / "cards.json").read_text(encoding="utf-8"))
        return cards if isinstance(cards, list) else []
    except Exception:
        return []


def _seed_for(key: str) -> int:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return int(h, 16)


def _read_prompt(card: dict) -> str:
    cid = str(card.get("id", "")).strip()
    prompt_path = ROOT / "data" / "prompts" / "cards" / f"{cid}.txt"
    if prompt_path.exists():
        try:
            return prompt_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return str(card.get("text_key") or card.get("name_key") or cid)


def _write_png(path: Path, seed: int, label: str) -> None:
    w, h = 64, 96
    rng = random.Random(seed)
    rows = []
    for y in range(h):
        row = bytearray([0])
        for x in range(w):
            r = (x * 3 + y * 2 + rng.randint(0, 45)) % 256
            g = (x * 2 + y * 4 + rng.randint(0, 35)) % 256
            b = (x + y * 5 + rng.randint(0, 30)) % 256
            row.extend([r, g, b])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(raw, level=9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _write_wav(path: Path, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 22050
    seconds = 2.0
    n = int(sample_rate * seconds)
    rng = random.Random(seed)
    f1 = 220 + (seed % 180)
    f2 = 110 + rng.randint(0, 100)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            val = 0.35 * math.sin(2 * math.pi * f1 * t) + 0.15 * math.sin(2 * math.pi * f2 * t)
            samp = int(max(-1.0, min(1.0, val)) * 32767)
            frames.extend(struct.pack("<h", samp))
        wf.writeframes(bytes(frames))


def _update_manifest(path: Path, key: str, rel_path: str, mode: str) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    items = payload.get("items")
    if not isinstance(items, dict):
        items = {}
        payload["items"] = items
    items[key] = {"path": rel_path, "mode": mode}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic explicit regeneration tool.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--missing_only", action="store_true", help="Regenerate only missing assets (default).")
    group.add_argument("--force", action="store_true", help="Regenerate all assets.")
    args = parser.parse_args()

    mode = "force" if args.force else "missing_only"
    cards = sorted(_load_cards(), key=lambda c: str(c.get("id", "")))

    if not cards:
        print("[regen_assets] no cards found in game/data/cards.json")
        return 0

    art_manifest = DATA / "art_manifest.json"
    bgm_manifest = DATA / "bgm_manifest.json"

    written_cards = 0
    for card in cards:
        cid = str(card.get("id", "")).strip()
        if not cid:
            continue
        _ = _read_prompt(card)  # stable source read requirement
        out_png = ASSETS / "sprites" / "cards" / f"{cid}.png"
        if mode == "missing_only" and out_png.exists():
            continue
        seed = _seed_for(f"card::{cid}")
        _write_png(out_png, seed, cid)
        _update_manifest(art_manifest, cid, str(out_png.relative_to(ROOT)).replace("\\", "/"), mode)
        written_cards += 1

    tracks = ["menu", "map_kaypacha", "combat_kaypacha", "boss", "event"]
    written_music = 0
    for track in sorted(tracks):
        out_wav = ASSETS / "music" / f"{track}.wav"
        if mode == "missing_only" and out_wav.exists():
            continue
        seed = _seed_for(f"track::{track}")
        _write_wav(out_wav, seed)
        _update_manifest(bgm_manifest, track, str(out_wav.relative_to(ROOT)).replace("\\", "/"), mode)
        written_music += 1

    print(f"[regen_assets] mode={mode} cards_written={written_cards} music_written={written_music}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
