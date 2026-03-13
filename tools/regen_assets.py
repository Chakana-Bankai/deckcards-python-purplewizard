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

import pygame

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game" / "data"
ASSETS = ROOT / "game" / "assets"


def _load_cards() -> list[dict]:
    out: list[dict] = []
    candidates = [
        DATA / "cards.json",
        DATA / "cards_hiperboria.json",
        DATA / "cards_arconte.json",
    ]
    for path in candidates:
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


def _read_prompt(card: dict) -> str:
    cid = str(card.get("id", "")).strip()
    prompt_path = ROOT / "data" / "prompts" / "cards" / f"{cid}.txt"
    if prompt_path.exists():
        try:
            return prompt_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return str(card.get("text_key") or card.get("name_key") or cid)


def _palette_for_card(label: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    low = str(label or "").lower()
    if "hyp-" in low or "hiper" in low:
        return (230, 242, 255), (118, 206, 255), (212, 182, 104)
    if "arc-" in low or "archon" in low or "arconte" in low:
        return (58, 34, 74), (201, 62, 101), (18, 12, 28)
    if "oracle" in low:
        return (46, 68, 122), (120, 208, 255), (22, 28, 54)
    if "guide" in low or "guard" in low:
        return (42, 96, 102), (229, 196, 104), (18, 42, 46)
    return (88, 52, 126), (224, 176, 92), (22, 18, 42)


def _write_png(path: Path, seed: int, label: str) -> None:
    w, h = 1920, 1080
    rng = random.Random(seed)
    base, accent, deep = _palette_for_card(label)
    surf = pygame.Surface((w, h))
    for y in range(h):
        mix = y / max(1, h - 1)
        row_color = (
            int(deep[0] * (1.0 - mix) + base[0] * mix),
            int(deep[1] * (1.0 - mix) + base[1] * mix),
            int(deep[2] * (1.0 - mix) + base[2] * mix),
        )
        pygame.draw.line(surf, row_color, (0, y), (w, y))

    halo = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(6):
        radius = int(h * (0.16 + i * 0.08))
        alpha = max(18, 82 - i * 10)
        cx = int(w * (0.26 + i * 0.11))
        cy = int(h * (0.22 + i * 0.09))
        pygame.draw.circle(halo, (*accent, alpha), (cx, cy), radius)
    surf.blit(halo, (0, 0))

    ribbons = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(14):
        y = int((i + 1) * h / 15)
        wobble = int(math.sin((i + 1) * 0.7 + seed) * 60)
        points = [
            (0, y + wobble),
            (int(w * 0.33), y - 40 - wobble // 2),
            (int(w * 0.66), y + 36 + wobble // 3),
            (w, y - wobble),
        ]
        pygame.draw.lines(ribbons, (*accent, 38), False, points, 8)
    surf.blit(ribbons, (0, 0))

    sigils = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(18):
        rw = rng.randint(120, 280)
        rh = rng.randint(28, 88)
        rx = rng.randint(60, w - rw - 60)
        ry = rng.randint(50, h - rh - 50)
        pygame.draw.rect(sigils, (*base, rng.randint(26, 52)), pygame.Rect(rx, ry, rw, rh), border_radius=18)
        pygame.draw.rect(sigils, (*accent, rng.randint(20, 44)), pygame.Rect(rx + 10, ry + 8, max(30, rw - 20), max(16, rh - 16)), 2, border_radius=14)
    surf.blit(sigils, (0, 0))

    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(path))


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


def _prune_stale_card_assets(valid_ids: set[str]) -> int:
    cards_dir = ASSETS / "sprites" / "cards"
    removed = 0
    for path in cards_dir.glob("*.png"):
        if path.stem in valid_ids:
            continue
        path.unlink()
        removed += 1
    return removed


def _rewrite_card_manifest(path: Path, items: dict[str, dict]) -> None:
    payload = {"items": items}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _regenerate_card_art(cards: list[dict], mode: str) -> tuple[int, int]:
    from game.content.card_art_generator import export_prompts

    export_prompts(cards)
    valid_ids = {str(card.get("id", "")).strip() for card in cards if str(card.get("id", "")).strip()}
    removed = _prune_stale_card_assets(valid_ids) if mode == "force" else 0
    manifest_items: dict[str, dict] = {}
    written_cards = 0

    for card in cards:
        cid = str(card.get("id", "")).strip()
        if not cid:
            continue
        out_png = ASSETS / "sprites" / "cards" / f"{cid}.png"
        if mode == "missing_only" and out_png.exists():
            manifest_items[cid] = {
                "path": str(out_png.relative_to(ROOT)).replace("\\", "/"),
                "mode": mode,
            }
            continue
        prompt = _read_prompt(card)
        seed = _seed_for(f"card::{cid}::{prompt}")
        _write_png(out_png, seed, cid)
        manifest_items[cid] = {
            "path": str(out_png.relative_to(ROOT)).replace("\\", "/"),
            "mode": mode,
        }
        written_cards += 1

    _rewrite_card_manifest(DATA / "art_manifest.json", manifest_items)
    return written_cards, removed


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

    bgm_manifest = DATA / "bgm_manifest.json"
    written_cards, removed_cards = _regenerate_card_art(cards, mode)

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

    print(f"[regen_assets] mode={mode} cards_written={written_cards} cards_removed={removed_cards} music_written={written_music}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
