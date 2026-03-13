from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game" / "data"
ASSETS = ROOT / "game" / "assets"


def _load_cards() -> list[dict]:
    out: list[dict] = []
    for path in (DATA / "cards.json", DATA / "cards_hiperboria.json", DATA / "cards_arconte.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("cards", []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                out.append(dict(row))
    dedup: dict[str, dict] = {}
    for row in out:
        dedup[str(row["id"])] = row
    return list(dedup.values())


def _seed_for(key: str) -> int:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return int(h, 16)


def _write_wav(path: Path, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 22050
    seconds = 2.0
    n = int(sample_rate * seconds)
    f1 = 220 + (seed % 180)
    f2 = 110 + ((seed // 7) % 100)
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


def _rebuild_card_manifest(cards: list[dict]) -> tuple[int, int]:
    cards_dir = ASSETS / "sprites" / "cards"
    valid_ids = {str(card.get("id", "")).strip() for card in cards if str(card.get("id", "")).strip()}
    removed = 0
    for path in cards_dir.glob("*.png"):
        if path.stem in valid_ids:
            continue
        path.unlink()
        removed += 1

    items: dict[str, dict] = {}
    for cid in sorted(valid_ids):
        path = cards_dir / f"{cid}.png"
        if not path.exists():
            continue
        items[cid] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "mode": "existing",
        }
    manifest = {"items": items}
    (DATA / "art_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(items), removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic explicit regeneration tool.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--missing_only", action="store_true", help="Regenerate only missing assets (default).")
    group.add_argument("--force", action="store_true", help="Regenerate all supported assets.")
    args = parser.parse_args()

    mode = "force" if args.force else "missing_only"
    cards = sorted(_load_cards(), key=lambda c: str(c.get("id", "")))
    if not cards:
        print("[regen_assets] no cards found in game/data/cards.json")
        return 0

    manifest_cards, removed_cards = _rebuild_card_manifest(cards)

    bgm_manifest = DATA / "bgm_manifest.json"
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

    print(
        f"[regen_assets] mode={mode} card_art=preserved manifest_cards={manifest_cards} "
        f"cards_removed={removed_cards} music_written={written_music}"
    )
    print(
        "[regen_assets] card art regeneration disabled here; use "
        "'python -m tools.assets.regenerate_premium_card_batch --engine direct_single_pass ...' for template-based card art."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
