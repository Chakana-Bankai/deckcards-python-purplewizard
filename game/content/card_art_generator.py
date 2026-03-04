from __future__ import annotations

import json
import zlib
from collections import deque
from pathlib import Path

import pygame

from game.art.gen_art32 import seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION, generate
from game.core.paths import assets_dir, data_dir


class PromptBuilder:
    def family_for(self, card: dict) -> str:
        tags = set(card.get("tags", []))
        if "attack" in tags:
            return "attack"
        if "block" in tags or "defense" in tags:
            return "defense"
        if "draw" in tags or "scry" in tags or "control" in tags:
            return "control"
        return "spirit"

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        ctype = self.family_for(card)
        prompt = f"chakana card::{cid}::{ctype} layered sacred geometry with glyph focus"
        return {
            "id": cid,
            "card_type": ctype,
            "family": ctype,
            "prompt_text": prompt,
        }


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.generated_count = 0
        self.replaced_count = 0
        self.version_seed = GEN_CARD_ART_VERSION
        self._recent_hashes: deque[int] = deque(maxlen=5)

    def _placeholder(self, card_id: str) -> pygame.Surface:
        out = pygame.Surface((320, 220), flags=pygame.SRCALPHA, depth=32)
        out.fill((18, 14, 28, 255))
        pygame.draw.circle(out, (180, 150, 220), (160, 110), 42, 2)
        pygame.draw.line(out, (180, 150, 220), (132, 88), (188, 132), 2)
        pygame.draw.line(out, (180, 150, 220), (188, 88), (132, 132), 2)
        pygame.draw.rect(out, (92, 78, 130), out.get_rect(), 2)
        f = pygame.font.SysFont("consolas", 16)
        out.blit(f.render(card_id[:24], True, (220, 215, 236)), (10, 194))
        return out

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only", family: str | None = None, symbol: str | None = None, prompt: str = ""):
        path = self.out_dir / f"{card_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return {"card_id": card_id, "path": str(path), "generator_used": "existing", "hash16": None, "prompt": prompt}

        card_type = family or ("attack" if "attack" in tags else "defense" if ("block" in tags or "defense" in tags) else "control" if ("draw" in tags or "scry" in tags or "control" in tags) else "spirit")
        seed = seed_from_id(card_id, GEN_CARD_ART_VERSION)
        result = generate(card_id, card_type, prompt, seed, path)
        h = int(result.get("hash16", 0))
        if any(abs(h - prev) < 220 for prev in self._recent_hashes):
            result = generate(card_id, card_type, prompt, seed + 991, path)
            h = int(result.get("hash16", 0))
        self._recent_hashes.append(h)
        if not path.exists():
            pygame.image.save(self._placeholder(card_id), str(path))
            result = {"card_id": card_id, "path": str(path), "generator_used": "placeholder", "hash16": 0, "prompt": prompt}
        self.generated_count += 1
        return result


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    pb = PromptBuilder()
    payload = {}
    for c in cards:
        cid = c.get("id", "unknown")
        entry = pb.build_entry(c)
        entry["seed"] = seed_from_id(cid, GEN_CARD_ART_VERSION)
        entry["prompt_hash"] = zlib.crc32(entry["prompt_text"].encode("utf-8")) & 0xFFFFFFFF
        payload[cid] = entry
    (data_dir() / "card_prompts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir() / "card_prompts.txt").write_text("\n".join(f"{k}: {v['prompt_text']}" for k, v in payload.items()), encoding="utf-8")
    (data_dir() / "prompt_manifest.json").write_text(json.dumps({"generator_version": GEN_CARD_ART_VERSION, "count": len(payload)}, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir() / "art_manifest_cards.json").write_text(json.dumps({"generator_version": GEN_CARD_ART_VERSION, "count": len(payload)}, ensure_ascii=False, indent=2), encoding="utf-8")
