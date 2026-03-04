from __future__ import annotations

import json
import random

import pygame

from game.art.gen_art32 import chakana_points, palette_for_family, seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION, render_card
from game.core.paths import assets_dir, data_dir


class PromptBuilder:
    def family_for(self, card: dict) -> str:
        tags = set(card.get("tags", []))
        if "attack" in tags:
            return "crimson_chaos"
        if "block" in tags or "defense" in tags:
            return "emerald_spirit"
        if "draw" in tags or "scry" in tags or "control" in tags:
            return "azure_cosmic"
        return "violet_arcane"

    def symbol_for(self, card: dict) -> str:
        rng = random.Random(seed_from_id(card.get("id", "unknown"), GEN_CARD_ART_VERSION))
        tags = set(card.get("tags", []))
        if "attack" in tags:
            return rng.choice(["sword", "axe", "puma"])
        if "block" in tags or "defense" in tags:
            return rng.choice(["mask", "tree", "rune_stone"])
        if "draw" in tags or "scry" in tags or "control" in tags:
            return rng.choice(["orb", "portal", "condor"])
        return rng.choice(["staff", "orb", "portal"])

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        fam = self.family_for(card)
        sym = self.symbol_for(card)
        return {
            "id": cid,
            "family": fam,
            "symbol": sym,
            "palette": palette_for_family(fam),
            "prompt_text": f"pixel card {fam} {sym}",
        }


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.generated_count = 0
        self.replaced_count = 0
        self.version_seed = GEN_CARD_ART_VERSION

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
        fam = family or ("crimson_chaos" if "attack" in tags else "emerald_spirit" if "block" in tags else "azure_cosmic" if "draw" in tags or "scry" in tags else "violet_arcane")
        sym = symbol or ("sword" if "attack" in tags else "tree" if "block" in tags else "orb")
        surf = render_card(card_id, fam, sym)
        if self._is_suspicious_white(surf):
            surf = self._placeholder(card_id)
        pygame.image.save(surf.convert_alpha(), str(path))
        self.generated_count += 1


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    pb = PromptBuilder()
    payload = {}
    for c in cards:
        payload[c.get("id", "unknown")] = pb.build_entry(c)
    (data_dir() / "card_prompts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir() / "card_prompts.txt").write_text("\n".join(f"{k}: {v['prompt_text']}" for k, v in payload.items()), encoding="utf-8")
    (data_dir() / "prompt_manifest.json").write_text(json.dumps({"generator_version": GEN_CARD_ART_VERSION, "count": len(payload)}, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir() / "art_manifest_cards.json").write_text(json.dumps({"generator_version": GEN_CARD_ART_VERSION, "count": len(payload)}, ensure_ascii=False, indent=2), encoding="utf-8")
