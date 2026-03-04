from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, add_rune_strokes, apply_fake_glow, chakana_points, dither, draw_sacred_geometry_bg, draw_symbol, final_grade, palette_for_family, seed_from_id
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
        rng = random.Random(seed_from_id(card.get("id", "unknown"), GEN_ART_VERSION))
        tags = set(card.get("tags", []))
        if "attack" in tags:
            return rng.choice(["sword", "axe", "puma"])
        if "block" in tags or "defense" in tags:
            return rng.choice(["mask", "rune_stone", "tree"])
        if "draw" in tags or "scry" in tags or "control" in tags:
            return rng.choice(["orb", "condor", "rune_stone"])
        return rng.choice(["portal", "staff", "orb"])

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        fam = self.family_for(card)
        sym = self.symbol_for(card)
        return {
            "id": cid,
            "family": fam,
            "symbol": sym,
            "palette": palette_for_family(fam),
            "notes_es": f"{card.get('name_es', cid)} vibra en {fam}",
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
        low_w, low_h = 128, 96
        out_w, out_h = 320, 220
        low = pygame.Surface((low_w, low_h), flags=pygame.SRCALPHA, depth=32)
        low.fill((22, 16, 34, 255))
        pal = palette_for_family(family)
        draw_sacred_geometry_bg(low, pal, rng)
        draw_symbol(low, symbol, rng)
        add_rune_strokes(low, rng)
        dither(low, 0.14)
        apply_fake_glow(low, pal[3], 2)
        final_grade(low)

        out = pygame.Surface((out_w, out_h), flags=pygame.SRCALPHA, depth=32)
        out.fill((18, 14, 28, 255))
        up = pygame.transform.scale(low, (out_w, out_h))
        out.blit(up, (0, 0))
        pygame.draw.rect(out, (0, 0, 0, 52), out.get_rect(), 8)
        return out

    def _is_suspicious_white(self, surf: pygame.Surface) -> bool:
        w, h = surf.get_size()
        pts = [(w // 4, h // 4), (w // 2, h // 2), (3 * w // 4, 3 * h // 4), (w // 3, 2 * h // 3), (2 * w // 3, h // 3)]
        white = 0
        for x, y in pts:
            c = surf.get_at((int(x), int(y)))
            if c.r > 240 and c.g > 240 and c.b > 240:
                white += 1
        return white / max(1, len(pts)) >= 0.8

    def _placeholder(self, card_id: str) -> pygame.Surface:
        out = pygame.Surface((320, 220), flags=pygame.SRCALPHA, depth=32)
        out.fill((30, 22, 46, 255))
        pts = chakana_points((160, 110), 46, 0.35)
        pygame.draw.polygon(out, (196, 158, 246), pts, 4)
        return out

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only", family: str | None = None, symbol: str | None = None):
        path = self.out_dir / f"{card_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return
        fam = family or ("solar_gold" if "attack" in tags else "emerald_spirit" if "block" in tags else "azure_cosmic" if "draw" in tags or "scry" in tags else "violet_arcane")
        sym = symbol or ("sword" if "attack" in tags else "tree" if "block" in tags else "orb")
        surf = self._render(card_id, fam, sym)
        if self._is_suspicious_white(surf):
            surf = self._render(card_id, "violet_arcane", "portal")
        if self._is_suspicious_white(surf):
            surf = self._placeholder(card_id)
        final = surf.convert_alpha()
        pygame.image.save(final, str(path))
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
