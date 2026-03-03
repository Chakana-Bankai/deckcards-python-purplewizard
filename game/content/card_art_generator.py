from __future__ import annotations

import json
import random
import zlib
from pathlib import Path

import pygame

from game.core.paths import assets_dir, data_dir


class PromptBuilder:
    def __init__(self):
        self.design = self._load_design_values()
        self.base_style = self.design.get("PROMPT_BASE_STYLE", "16bit pixel art mystical andean magic card")
        self.type_map = {
            "attack": self.design.get("PROMPT_TYPE_ATTACK", "solar warrior strike"),
            "defense": self.design.get("PROMPT_TYPE_DEFENSE", "obsidian rune ward"),
            "arcane": self.design.get("PROMPT_TYPE_ARCANE", "cosmic portal spell"),
            "ritual": self.design.get("PROMPT_TYPE_RITUAL", "obsidian rune ritual"),
            "curse": self.design.get("PROMPT_TYPE_CURSE", "corrupted void sigil"),
        }
        self.rarity_map = {
            "legendary": self.design.get("PROMPT_RARITY_LEGENDARY", "legendary glowing"),
            "rare": self.design.get("PROMPT_RARITY_RARE", "ancient sacred"),
            "common": self.design.get("PROMPT_RARITY_COMMON", "corrupted void"),
            "uncommon": self.design.get("PROMPT_RARITY_RARE", "ancient sacred"),
            "basic": self.design.get("PROMPT_RARITY_COMMON", "corrupted void"),
        }
        pool = self.design.get("PROMPT_UNIQUE_POOL", "")
        self.details = [x.strip() for x in pool.split("|") if x.strip()] or ["chakana constellation", "condor spirit", "obsidian temple glyph"]
        self.external_prompts = {}
        try:
            data = json.loads((data_dir() / "card_prompts.json").read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.external_prompts = data
        except Exception:
            self.external_prompts = {}

    def _load_design_values(self) -> dict[str, str]:
        path = data_dir() / "design" / "gdd_chakana_purple_wizard.txt"
        vals = {}
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return vals
        for line in raw.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        return vals

    def _card_type(self, card: dict) -> str:
        tags = set(card.get("tags", []))
        if "curse" in tags:
            return "curse"
        if "ritual" in tags:
            return "ritual"
        if "arcane" in tags or "rupture" in tags:
            return "arcane"
        if "skill" in tags or "defense" in tags:
            return "defense"
        return "attack"

    def _mechanics_keyword(self, card: dict) -> str:
        eff = " ".join(e.get("type", "") for e in card.get("effects", []))
        src = f"{card.get('id','')} {eff}".lower()
        if "energy" in src:
            return "mana burst"
        if "draw" in src or "scry" in src:
            return "deck manipulation"
        if "block" in src:
            return "guardia sigil"
        if "debuff" in src or "status" in src:
            return "maldición weave"
        if "rupture" in src:
            return "quiebre pulse"
        return "combat focus"

    def build_entry(self, card: dict) -> dict:
        cid = card.get("id", "unknown")
        card_type = self._card_type(card)
        rarity = self.rarity_map.get(card.get("rarity", "common"), self.rarity_map["common"])
        detail = self.details[zlib.crc32(cid.encode("utf-8")) % len(self.details)]
        existing = self.external_prompts.get(cid)
        if isinstance(existing, str) and existing.strip():
            prompt = existing.strip()
        elif isinstance(existing, dict) and existing.get("prompt"):
            prompt = str(existing.get("prompt"))
        else:
            prompt = f"{self.base_style}, {self.type_map[card_type]}, {rarity}, {detail}, {self._mechanics_keyword(card)}"
        return {
            "base_style": self.base_style,
            "type": card_type,
            "rarity": rarity,
            "detail": detail,
            "prompt": prompt,
        }

    def build_enemy_entry(self, enemy: dict) -> dict:
        eid = enemy.get("id", "unknown")
        detail = self.details[zlib.crc32((eid + "enemy").encode("utf-8")) % len(self.details)]
        prompt = f"{self.base_style}, hostile mystic enemy portrait, {detail}, intent readability"
        return {
            "base_style": self.base_style,
            "type": "enemy",
            "rarity": "ancient sacred",
            "detail": detail,
            "prompt": prompt,
        }


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.cache: dict[str, pygame.Surface] = {}
        self.generated_count = 0
        self.replaced_count = 0

    def _variance(self, surf: pygame.Surface) -> float:
        pixels = []
        w, h = surf.get_size()
        for y in range(0, h, max(1, h // 24)):
            for x in range(0, w, max(1, w // 24)):
                pixels.append(surf.get_at((x, y))[:3])
        rs = [p[0] for p in pixels]
        gs = [p[1] for p in pixels]
        bs = [p[2] for p in pixels]
        return float((max(rs) - min(rs)) + (max(gs) - min(gs)) + (max(bs) - min(bs)))

    def _is_uniform(self, path: Path) -> bool:
        try:
            surf = pygame.image.load(str(path)).convert_alpha()
        except Exception:
            return True
        return self._variance(surf) < 70.0

    def _palette(self, rng: random.Random, tags: set[str], rarity: str):
        bg_dark = (20 + rng.randint(0, 20), 12 + rng.randint(0, 18), 38 + rng.randint(0, 30))
        bg_light = (88 + rng.randint(0, 40), 42 + rng.randint(0, 34), 148 + rng.randint(0, 45))
        accent_gold = (210 + rng.randint(0, 30), 174 + rng.randint(0, 24), 78 + rng.randint(0, 18))
        accent_ice = (225, 232, 255)
        if "arcane" in tags or "rupture" in tags:
            bg_light = (102 + rng.randint(0, 36), 56 + rng.randint(0, 28), 176 + rng.randint(0, 40))
        if rarity in {"rare", "legendary"}:
            accent_gold = (232, 198, 98)
        return bg_dark, bg_light, accent_gold, accent_ice

    def _generate_surface(self, card_id: str, tags: list[str], rarity: str) -> pygame.Surface:
        w, h = 360, 500
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(abs(hash(card_id)) & 0xFFFFFFFF)
        tags_set = set(tags)
        bg_dark, bg_light, accent_gold, accent_ice = self._palette(rng, tags_set, rarity)

        for y in range(h):
            t = y / max(1, h - 1)
            col = (
                int(bg_dark[0] * (1 - t) + bg_light[0] * t),
                int(bg_dark[1] * (1 - t) + bg_light[1] * t),
                int(bg_dark[2] * (1 - t) + bg_light[2] * t),
                255,
            )
            pygame.draw.line(surf, col, (0, y), (w, y))

        for i in range(26):
            x = rng.randint(10, w - 10)
            y = rng.randint(10, h - 10)
            r = rng.randint(6, 58)
            color = (accent_gold[0], accent_gold[1], accent_gold[2], rng.randint(20, 68))
            pygame.draw.circle(surf, color, (x, y), r, width=1)

        points = []
        cx, cy = w // 2, h // 2
        for i in range(8):
            ang = (i / 8.0) * 6.28318
            rr = 90 + (18 if i % 2 == 0 else -8)
            points.append((int(cx + rr * pygame.math.Vector2(1, 0).rotate_rad(ang).x), int(cy + rr * pygame.math.Vector2(1, 0).rotate_rad(ang).y)))
        pygame.draw.polygon(surf, (*accent_ice, 45), points, width=2)

        for i in range(48):
            x = rng.randint(0, w - 1)
            y = rng.randint(0, h - 1)
            a = rng.randint(10, 35)
            surf.set_at((x, y), (accent_ice[0], accent_ice[1], accent_ice[2], a))

        if "attack" in tags_set:
            pygame.draw.line(surf, (*accent_gold, 150), (40, h - 100), (w - 40, 80), 4)
        if "skill" in tags_set:
            pygame.draw.circle(surf, (*accent_ice, 120), (cx, cy), 64, width=3)
        if "ritual" in tags_set:
            pygame.draw.rect(surf, (*accent_gold, 100), pygame.Rect(cx - 70, cy - 35, 140, 70), width=2)
        if "curse" in tags_set:
            pygame.draw.line(surf, (220, 70, 110, 170), (60, 60), (w - 60, h - 60), 3)

        border_color = accent_gold if rarity in {"rare", "legendary"} else (170, 130, 220)
        pygame.draw.rect(surf, border_color, surf.get_rect().inflate(-4, -4), width=3, border_radius=18)
        return surf

    def _generate_and_save(self, card_id: str, tags: list[str], rarity: str, path: Path):
        surf = self._generate_surface(card_id, tags, rarity)
        pygame.image.save(surf, str(path))

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only"):
        path = self.out_dir / f"{card_id}.png"
        if mode == "force_regen":
            self._generate_and_save(card_id, tags, rarity, path)
            self.generated_count += 1
            return
        if not path.exists():
            self._generate_and_save(card_id, tags, rarity, path)
            self.generated_count += 1
            return
        if self._is_uniform(path):
            self._generate_and_save(card_id, tags, rarity, path)
            self.replaced_count += 1


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    pb = PromptBuilder()
    card_payload = {c.get("id", "unknown"): pb.build_entry(c) for c in cards}
    _write_if_changed(data_dir() / "card_prompts.json", json.dumps({k: v["prompt"] for k, v in card_payload.items()}, ensure_ascii=False, indent=2))

    if enemies is not None:
        enemy_payload = {e.get("id", "unknown"): pb.build_enemy_entry(e) for e in enemies}
        _write_if_changed(data_dir() / "enemy_prompts.json", json.dumps(enemy_payload, ensure_ascii=False, indent=2))

    txt = "\n".join(f"{k}: {v['prompt']}" for k, v in card_payload.items())
    _write_if_changed(data_dir() / "card_prompts.txt", txt)


def _write_if_changed(path: Path, text: str):
    old = None
    try:
        old = path.read_text(encoding="utf-8")
    except Exception:
        old = None
    if old != text:
        path.write_text(text, encoding="utf-8")
