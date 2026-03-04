from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, add_rune_strokes, apply_fake_glow, dither, draw_sacred_geometry_bg, draw_symbol, final_grade, palette_for_family, seed_from_id
from game.core.paths import assets_dir, data_dir


class PromptBuilder:
    def __init__(self):
        self.symbols = ["sword", "staff", "cup", "axe", "tree", "orb", "mask", "condor", "puma", "portal", "rune_stone"]

    def family_for(self, card: dict) -> str:
        direction = str(card.get("direction", "ESTE")).upper()
        if direction == "ESTE":
            return "solar_gold" if card.get("rarity") != "legendary" else "crimson_chaos"
        if direction == "SUR":
            return "emerald_spirit" if card.get("rarity") != "legendary" else "obsidian_void"
        if direction == "NORTE":
            return "azure_cosmic" if card.get("rarity") != "legendary" else "violet_arcane"
        return "violet_arcane" if card.get("rarity") != "legendary" else "azure_cosmic"

    def symbol_for(self, card: dict) -> str:
        tags = set(card.get("tags", []))
        if "attack" in tags:
            return random.choice(["sword", "axe", "puma"])
        if "block" in tags or "defense" in tags:
            return random.choice(["mask", "rune_stone", "tree"])
        if "draw" in tags or "scry" in tags or "control" in tags:
            return random.choice(["orb", "condor", "rune_stone"])
        return random.choice(["portal", "staff", "orb"])

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        rng = random.Random(seed_from_id(cid, GEN_ART_VERSION))
        fam = self.family_for(card)
        sym = self.symbol_for(card)
        note = f"{card.get('name_es', cid)} vibra en {fam}"
        return {
            "id": cid,
            "family": fam,
            "symbol": sym,
            "notes_es": note,
            "prompt_text": f"32-bit pixel mystical card, family {fam}, symbol {sym}, sacred geometry, runes, detailed light",
        }


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.generated_count = 0
        self.replaced_count = 0
        self.version_seed = GEN_ART_VERSION

    def _render(self, card_id: str, family: str, symbol: str) -> pygame.Surface:
        rng = random.Random(seed_from_id(card_id, self.version_seed))
        low = pygame.Surface((128, 96), pygame.SRCALPHA)
        pal = palette_for_family(family)
        for y in range(96):
            t = y / 95.0
            c0, c1 = pal[0], pal[2]
            col = (int(c0[0] * (1 - t) + c1[0] * t), int(c0[1] * (1 - t) + c1[1] * t), int(c0[2] * (1 - t) + c1[2] * t), 255)
            pygame.draw.line(low, col, (0, y), (127, y))
        draw_sacred_geometry_bg(low, rng)
        draw_symbol(low, symbol, rng)
        add_rune_strokes(low, rng)
        dither(low, 0.14)
        apply_fake_glow(low, pal[3], 2)
        final_grade(low)
        return pygame.transform.scale(low, (320, 220))

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only", family: str | None = None, symbol: str | None = None):
        path = self.out_dir / f"{card_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return
        fam = family or ("solar_gold" if "attack" in tags else "emerald_spirit" if "block" in tags else "azure_cosmic" if "draw" in tags or "scry" in tags else "violet_arcane")
        sym = symbol or ("sword" if "attack" in tags else "tree" if "block" in tags else "orb")
        surf = self._render(card_id, fam, sym)
        pygame.image.save(surf, str(path))
        self.generated_count += 1


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    pb = PromptBuilder()
    payload = {}
    for c in cards:
        entry = pb.build_entry(c)
        payload[c.get("id", "unknown")] = entry
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (data_dir() / "card_prompts.json").write_text(text, encoding="utf-8")
    (data_dir() / "card_prompts.txt").write_text("\n".join(f"{k}: {v['prompt_text']}" for k, v in payload.items()), encoding="utf-8")
    (data_dir() / "prompt_manifest.json").write_text(json.dumps({"generator_version": GEN_ART_VERSION, "count": len(payload)}, ensure_ascii=False, indent=2), encoding="utf-8")
