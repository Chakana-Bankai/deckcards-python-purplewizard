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
        self.palette_groups = {
            "attack": "solar gold",
            "defense": "emerald nature",
            "energy": "azure cosmic",
            "control": "violet arcane",
            "ritual": "obsidian void",
            "chaos": "crimson chaos",
            "arcane": "azure cosmic",
            "curse": "crimson chaos",
            "oracle": "moon opal",
            "storm": "storm cyan",
            "earth": "andes umber",
            "blood": "ruby dusk",
        }
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
        fam = card.get("family")
        if fam in {"attack","defense","energy","control","ritual","chaos"}:
            return {"energy":"arcane","control":"arcane","chaos":"curse"}.get(fam, fam)
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
        palette = self.palette_groups.get(card.get("family", card_type), self.palette_groups.get(card_type, "violet arcane"))
        detail = self.details[zlib.crc32(cid.encode("utf-8")) % len(self.details)]
        existing = self.external_prompts.get(cid)
        if isinstance(existing, str) and existing.strip():
            prompt = existing.strip()
        elif isinstance(existing, dict) and existing.get("prompt"):
            prompt = str(existing.get("prompt"))
        else:
            prompt = f"{self.base_style}, {self.type_map[card_type]}, {rarity}, palette {palette}, {detail}, {self._mechanics_keyword(card)}"
        return {
            "base_style": self.base_style,
            "type": card_type,
            "rarity": rarity,
            "palette": palette,
            "detail": detail,
            "prompt": prompt,
        }

    def build_enemy_entry(self, enemy: dict) -> dict:
        eid = enemy.get("id", "unknown")
        detail = self.details[zlib.crc32((eid + "enemy").encode("utf-8")) % len(self.details)]
        palette = "obsidian void"
        prompt = f"{self.base_style}, hostile mystic enemy portrait, {detail}, intent readability"
        return {
            "base_style": self.base_style,
            "type": "enemy",
            "rarity": "ancient sacred",
            "palette": palette,
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
        palettes = {
            "violet_arcane": ((26, 18, 52), (110, 78, 180), (238, 214, 160)),
            "solar_gold": ((40, 24, 18), (172, 118, 36), (246, 224, 152)),
            "emerald_spirit": ((14, 30, 24), (54, 140, 110), (206, 240, 210)),
            "crimson_chaos": ((38, 10, 18), (152, 42, 60), (252, 188, 168)),
            "azure_cosmic": ((14, 24, 48), (62, 122, 186), (192, 224, 255)),
            "obsidian_void": ((12, 12, 16), (62, 62, 86), (210, 210, 230)),
        }
        key = "violet_arcane"
        if "attack" in tags: key = "solar_gold"
        elif "skill" in tags or "block" in tags: key = "emerald_spirit"
        elif "ritual" in tags: key = "obsidian_void"
        elif "curse" in tags: key = "crimson_chaos"
        elif "draw" in tags or "scry" in tags: key = "azure_cosmic"
        dark, light, accent = palettes[key]
        if rarity in {"rare", "legendary"}:
            accent = tuple(min(255, c + 16) for c in accent)
        return dark, light, accent, (230, 236, 255)

    def _generate_surface(self, card_id: str, tags: list[str], rarity: str) -> pygame.Surface:
        w, h = 360, 500
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(zlib.crc32(card_id.encode("utf-8")) & 0xFFFFFFFF)
        tags_set = set(tags)
        bg_dark, bg_light, accent_gold, accent_ice = self._palette(rng, tags_set, rarity)

        # 32-bit style gradient + dithering
        for y in range(h):
            t = y / max(1, h - 1)
            col = (
                int(bg_dark[0] * (1 - t) + bg_light[0] * t),
                int(bg_dark[1] * (1 - t) + bg_light[1] * t),
                int(bg_dark[2] * (1 - t) + bg_light[2] * t),
                255,
            )
            pygame.draw.line(surf, col, (0, y), (w, y))
        for y in range(0, h, 2):
            for x in range((y // 2) % 2, w, 2):
                c = surf.get_at((x, y)); surf.set_at((x, y), (max(0, c.r - 7), max(0, c.g - 7), max(0, c.b - 7), 255))

        # sacred geometry rosette
        cx, cy = w // 2, h // 2
        for i in range(10):
            rr = 30 + i * 10
            pygame.draw.circle(surf, (*accent_ice, 18 + i * 2), (cx, cy), rr, width=1)

        # procedural symbols
        sym = ["sword", "staff", "cup", "axe", "tree", "orb", "mask", "condor", "puma", "portal", "rune"]
        if "attack" in tags_set: choice = "sword"
        elif "ritual" in tags_set: choice = "portal"
        elif "draw" in tags_set or "scry" in tags_set: choice = "orb"
        elif "block" in tags_set or "skill" in tags_set: choice = "tree"
        elif "curse" in tags_set: choice = "mask"
        else: choice = sym[zlib.crc32((card_id+"sym").encode("utf-8")) % len(sym)]

        col = (*accent_gold, 220)
        if choice == "sword":
            pygame.draw.line(surf, col, (cx - 70, cy + 90), (cx + 70, cy - 80), 8)
        elif choice == "staff":
            pygame.draw.line(surf, col, (cx, cy - 100), (cx, cy + 100), 10); pygame.draw.circle(surf, col, (cx, cy - 115), 18)
        elif choice == "cup":
            pygame.draw.rect(surf, col, pygame.Rect(cx - 46, cy - 20, 92, 48), border_radius=10, width=6)
        elif choice == "axe":
            pygame.draw.line(surf, col, (cx - 10, cy - 100), (cx + 20, cy + 110), 8); pygame.draw.polygon(surf, col, [(cx-50,cy-40),(cx+30,cy-80),(cx+10,cy+10)])
        elif choice == "tree":
            pygame.draw.line(surf, col, (cx, cy + 90), (cx, cy - 20), 8); pygame.draw.circle(surf, col, (cx, cy - 55), 46, width=6)
        elif choice == "orb":
            pygame.draw.circle(surf, col, (cx, cy), 60, width=7)
        elif choice == "mask":
            pygame.draw.ellipse(surf, col, pygame.Rect(cx - 60, cy - 80, 120, 160), width=7)
        elif choice == "condor":
            pygame.draw.polygon(surf, col, [(cx-100,cy),(cx,cy-50),(cx+100,cy),(cx,cy+10)], width=6)
        elif choice == "puma":
            pygame.draw.lines(surf, col, False, [(cx-90,cy+40),(cx-40,cy-20),(cx+20,cy-10),(cx+80,cy+30)], 7)
        elif choice == "portal":
            pygame.draw.rect(surf, col, pygame.Rect(cx - 70, cy - 90, 140, 180), width=6)
        elif choice == "rune":
            pygame.draw.line(surf, col, (cx-60,cy-60), (cx+60,cy+60), 7); pygame.draw.line(surf, col, (cx+60,cy-60), (cx-60,cy+60), 7)

        # runes overlay
        for _ in range(16):
            x = rng.randint(24, w - 24); y = rng.randint(24, h - 24)
            pygame.draw.rect(surf, (*accent_ice, 100), pygame.Rect(x, y, 6, 12), width=1)

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
    _write_if_changed(data_dir() / "card_prompts.json", json.dumps(card_payload, ensure_ascii=False, indent=2))

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
