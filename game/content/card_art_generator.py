from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from game.core.paths import assets_dir, data_dir


class PromptBuilder:
    BASE = (
        "16bit pixel art mystical andean magic card, "
        "chakana geometry integrated subtly, dramatic volumetric lighting, rich colors, deep shadows, trading card art composition"
    )
    TYPE_VARIANTS = {
        "attack": "violent burst of violet lightning tearing through ancient stone, dynamic diagonal composition, sparks and arcane particles, cracked runes glowing",
        "defense": "ethereal violet shield forming from sacred geometric light, calm radiant aura, balanced composition, andean temple background",
        "arcane": "fractured cosmic reality splitting open, glowing sigils floating in void, surreal distortion, neon violet veins, chakana morphing into cosmic geometry",
        "ritual": "ancient andean altar illuminated by violet ritual fire, hooded mage channeling sacred geometry, smoke forming symbolic patterns, gothic cathedral shadows",
        "curse": "corrupted chakana bleeding dark energy, twisted sigils in shadow void, ominous fog, distorted gothic architecture",
    }
    RARITY = {
        "basic": "clear simple composition",
        "common": "clear simple composition",
        "uncommon": "ornate details, layered lighting",
        "rare": "ornate details, layered lighting",
        "legendary": "epic cinematic lighting, highly intricate symbolic design",
    }
    DETAILS = [
        "condor feathers", "wolf spirit", "obsidian altar", "moonlit ruins", "comet trail", "bone talismans", "aurora veil", "temple stairs", "quinoa fields", "andes frost",
        "sun disk", "ink raven", "storm sigil", "echoing bells", "violet dunes", "night orchid", "ritual brazier", "jade mask", "silver cenote", "black quartz",
        "serpent knot", "lunar mirror", "ember ash", "thunder glyph", "copper idol", "mist bridge", "sacred cliff", "crystal halo", "shadow totem", "stellar gate",
        "desert monolith", "forgotten archive", "iron feather", "ivory runestone", "violet lotus", "smoke serpent", "frozen obelisk", "sunken chapel", "gilded chains", "cinder crown",
        "howling canyon", "meteor shard", "woven charms", "storm lantern", "enchanted spindle", "sable shrine", "hollow drum", "cobalt flame", "ashen relic", "temporal crack",
        "obsidian wolf", "burning condor", "midnight glacier", "rain of petals", "twin moons", "veil of thorns"
    ]

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

    def _mechanics(self, card: dict) -> str:
        text = (card.get("text_key", "") + " " + card.get("id", "")).lower()
        eff = " ".join(e.get("type", "") for e in card.get("effects", [])) if isinstance(card.get("effects"), list) else ""
        src = f"{text} {eff}"
        parts = []
        if "draw" in src:
            parts.append("arcane card draw vortex")
        if "rupture" in src:
            parts.append("rupture energy fractures")
        if "debuff" in src or "weak" in src or "frail" in src:
            parts.append("hexing debuff aura")
        if "block" in src:
            parts.append("protective block sigils")
        if "energy" in src:
            parts.append("energy orb resonance")
        return ", ".join(parts) if parts else "mystic combat focus"

    def build(self, card: dict) -> str:
        card_type = self._card_type(card)
        rarity = self.RARITY.get(card.get("rarity", "common"), self.RARITY["common"])
        detail = self.DETAILS[abs(hash(card.get("id", "unknown"))) % len(self.DETAILS)]
        mechanics = self._mechanics(card)
        return f"{self.BASE}, {self.TYPE_VARIANTS[card_type]}, {rarity}, {mechanics}, unique detail: {detail}"

    def build_enemy(self, enemy: dict) -> str:
        enemy_id = enemy.get("id", "unknown")
        detail = self.DETAILS[abs(hash(enemy_id + "enemy")) % len(self.DETAILS)]
        return (
            f"{self.BASE}, ominous enemy portrait, arcane hostility, readable silhouette, mystical intent iconography, "
            f"ornate details, layered lighting, unique detail: {detail}"
        )


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
            bg_light = (130, 58 + rng.randint(0, 25), 210 + rng.randint(0, 30))
        if "ritual" in tags:
            accent_gold = (242, 190, 98)
        if rarity in {"rare", "legendary"}:
            accent_gold = (245, 215, 130)
        return bg_dark, bg_light, accent_gold, accent_ice

    def _draw_chakana(self, surf: pygame.Surface, rng: random.Random):
        cx = 110 + rng.randint(-30, 30)
        cy = 90 + rng.randint(-28, 28)
        step = 6 + rng.randint(0, 2)
        col = (216 + rng.randint(0, 24), 190 + rng.randint(0, 24), 242)
        for i in range(-30, 31, step):
            pygame.draw.rect(surf, col, (cx + i - 2, cy - 4, 5, 9))
            pygame.draw.rect(surf, col, (cx - 4, cy + i - 2, 9, 5))
        pygame.draw.rect(surf, (252, 242, 255), (cx - 14, cy - 14, 28, 28), 2)

    def _render(self, card_id: str, tags: list[str], rarity: str, salt: int = 0) -> pygame.Surface:
        seed = f"{card_id}:{salt}"
        rng = random.Random(seed)
        tags_set = set(tags)
        surf = pygame.Surface((384, 256))

        bg_dark, bg_light, accent_gold, accent_ice = self._palette(rng, tags_set, rarity)

        for y in range(256):
            t = y / 255.0
            for x in range(384):
                jitter = 5 if ((x + y + rng.randint(0, 3)) & 1) else -3
                r = int(bg_dark[0] * (1 - t) + bg_light[0] * t) + jitter
                g = int(bg_dark[1] * (1 - t) + bg_light[1] * t) + jitter
                b = int(bg_dark[2] * (1 - t) + bg_light[2] * t) + jitter
                surf.set_at((x, y), (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))

        for _ in range(26):
            x, y = rng.randint(10, 360), rng.randint(10, 230)
            w, h = rng.randint(16, 78), rng.randint(10, 56)
            pygame.draw.rect(surf, (140 + rng.randint(0, 65), 90 + rng.randint(0, 55), 190 + rng.randint(0, 55)), (x, y, w, h), 1)

        self._draw_chakana(surf, rng)

        for _ in range(30):
            x1, y1 = rng.randint(8, 376), rng.randint(8, 248)
            x2, y2 = x1 + rng.randint(-70, 70), y1 + rng.randint(-40, 40)
            pygame.draw.line(surf, accent_ice, (x1, y1), (x2, y2), 1)

        for _ in range(260):
            x, y = rng.randint(0, 383), rng.randint(0, 255)
            surf.set_at((x, y), (accent_gold[0], min(255, accent_gold[1] + rng.randint(-20, 20)), max(0, accent_gold[2] + rng.randint(-20, 20))))

        if "attack" in tags_set:
            pygame.draw.polygon(surf, (236, 128, 164), [(36, 220), (190, 34), (346, 220)], 4)
        if "skill" in tags_set:
            pygame.draw.rect(surf, (140, 198, 250), (76, 54, 240, 146), 4)
        if "arcane" in tags_set or "rupture" in tags_set:
            pygame.draw.circle(surf, (212, 176, 255), (192, 128), 92, 3)
            pygame.draw.circle(surf, (212, 176, 255), (192, 128), 52, 3)
        if "ritual" in tags_set:
            pygame.draw.circle(surf, (245, 146, 202), (192, 128), 88, 3)
        if "curse" in tags_set:
            pygame.draw.line(surf, (168, 34, 82), (20, 20), (364, 236), 4)
            pygame.draw.line(surf, (168, 34, 82), (364, 20), (20, 236), 4)

        pygame.draw.rect(surf, (244, 232, 255), surf.get_rect(), 3)

        crop = pygame.Rect(58, 40, 268, 176)
        return surf.subsurface(crop).copy()

    def _generate_and_save(self, card_id: str, tags: list[str], rarity: str, path: Path) -> None:
        surf = self._render(card_id, tags, rarity, 0)
        if self._variance(surf) < 70:
            surf = self._render(card_id, tags, rarity, 1)
        pygame.image.save(surf, str(path))
        self.cache[card_id] = surf

    def ensure_art(self, card_id: str, tags: list[str], rarity: str, mode: str = "missing_only") -> None:
        path = self.out_dir / f"{card_id}.png"
        if mode == "off":
            if path.exists():
                print(f"Using existing art: {card_id}")
            return

        if mode == "force_regen":
            self._generate_and_save(card_id, tags, rarity, path)
            self.generated_count += 1
            print(f"Generated art: {card_id} -> {path}")
            return

        if not path.exists():
            self._generate_and_save(card_id, tags, rarity, path)
            self.generated_count += 1
            print(f"Generated art: {card_id} -> {path}")
            return

        if self._is_uniform(path):
            self._generate_and_save(card_id, tags, rarity, path)
            self.replaced_count += 1
            print(f"Replaced uniform placeholder: {card_id} -> {path}")
            return

        print(f"Using existing art: {card_id}")


def export_prompts(cards: list[dict], enemies: list[dict] | None = None):
    pb = PromptBuilder()
    card_payload = {}
    for c in cards:
        card_id = c.get("id", "unknown")
        card_type = pb._card_type(c)
        rarity = pb.RARITY.get(c.get("rarity", "common"), pb.RARITY["common"])
        detail = pb.DETAILS[abs(hash(card_id)) % len(pb.DETAILS)]
        prompt = pb.build(c)
        card_payload[card_id] = {
            "base_style": pb.BASE,
            "card_type": card_type,
            "rarity": rarity,
            "unique_detail": detail,
            "prompt": prompt,
        }
    (data_dir() / "card_prompts.json").write_text(json.dumps(card_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if enemies is not None:
        enemy_payload = {}
        for e in enemies:
            eid = e.get("id", "unknown")
            detail = pb.DETAILS[abs(hash(eid + "enemy")) % len(pb.DETAILS)]
            enemy_payload[eid] = {
                "base_style": pb.BASE,
                "enemy_type": "hostile mystic",
                "rarity": "ornate details, layered lighting",
                "unique_detail": detail,
                "prompt": pb.build_enemy(e),
            }
        (data_dir() / "enemy_prompts.json").write_text(json.dumps(enemy_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    txt = "\n".join(f"{k}: {v['prompt']}" for k, v in card_payload.items())
    (data_dir() / "card_prompts.txt").write_text(txt, encoding="utf-8")
