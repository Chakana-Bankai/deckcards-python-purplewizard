from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, add_rune_strokes, apply_fake_glow, dither, final_grade, palette_for_family, seed_from_id
from game.core.paths import assets_dir
from game.services.spiritual_bestiary import resolve_entity_profile


class EnemyArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "enemies"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.version_seed = GEN_ART_VERSION

    def _palette_family_from_profile(self, profile: dict, tier: str) -> str:
        palette_key = str(profile.get("palette", "")).strip().lower()
        by_palette = {
            "red_black": "crimson_chaos",
            "crimson_ritual": "crimson_chaos",
            "gold_cyan": "azure_cosmic",
            "violet_cyan": "violet_arcane",
            "void_violet": "obsidian_void",
            "emerald_gold": "emerald_spirit",
        }
        fam = by_palette.get(palette_key, "")
        if fam:
            return fam
        return "obsidian_void" if tier == "common" else "crimson_chaos" if tier == "elite" else "violet_arcane"

    def _render(self, enemy_id: str, tier: str = "common", biome: str = "ukhu"):
        rng = random.Random(seed_from_id(enemy_id, self.version_seed))
        profile = resolve_entity_profile(enemy_id, biome=biome, tier=tier, kind="boss" if tier == "boss" else "enemy")
        faction = str(profile.get("faction", "demons")).lower().strip()
        motif = str(profile.get("motif", "")).lower().strip()

        low = pygame.Surface((96, 96), pygame.SRCALPHA)
        fam = self._palette_family_from_profile(profile, tier)
        pal = palette_for_family(fam)
        low.fill((*pal[0], 255))

        # Aura stays behind silhouette and scales for bosses/archons.
        aura_radius = 34 if tier != "boss" else 42
        aura_alpha = 120 if tier != "boss" else 150
        pygame.draw.circle(low, (*pal[1], aura_alpha), (48, 44), aura_radius, 2)
        if tier == "boss" or faction == "archons" or motif == "archon":
            pygame.draw.circle(low, (*pal[2], 120), (48, 44), aura_radius + 8, 1)
            pygame.draw.circle(low, (*pal[3], 90), (48, 44), aura_radius - 10, 1)

        # Faction-oriented silhouette and motif accents.
        if faction == "guardians" or motif == "guardian":
            pts = [(14, 82), (24, 38), (48, 14), (72, 38), (82, 82), (64, 70), (48, 56), (32, 70)]
            pygame.draw.polygon(low, (*pal[2], 230), pts)
            pygame.draw.lines(low, (*pal[3], 190), False, [(20, 48), (48, 28), (76, 48)], 2)
            eye_color = (230, 245, 255, 230)
        elif faction == "oracles" or motif == "oracle":
            pts = [(16, 82), (30, 36), (48, 12), (66, 36), (80, 82), (48, 72)]
            pygame.draw.polygon(low, (*pal[2], 230), pts)
            pygame.draw.ellipse(low, (*pal[3], 210), pygame.Rect(34, 30, 28, 20), 2)
            pygame.draw.circle(low, (*pal[3], 180), (48, 40), 2)
            eye_color = (215, 235, 255, 230)
        elif faction == "archons" or motif == "archon":
            pts = [(12, 82), (18, 42), (34, 20), (48, 8), (62, 20), (78, 42), (84, 82), (48, 68)]
            pygame.draw.polygon(low, (*pal[2], 235), pts)
            pygame.draw.arc(low, (*pal[3], 190), pygame.Rect(26, 16, 44, 26), 0.1, 3.0, 2)
            pygame.draw.circle(low, (*pal[3], 140), (48, 22), 4, 1)
            eye_color = (255, 180, 200, 235)
        else:
            pts = [
                (rng.randint(12, 30), 82),
                (rng.randint(18, 36), rng.randint(24, 40)),
                (48, rng.randint(8, 20)),
                (rng.randint(60, 78), rng.randint(24, 40)),
                (rng.randint(66, 84), 82),
            ]
            pygame.draw.polygon(low, (*pal[2], 230), pts)
            pygame.draw.line(low, (*pal[3], 170), (24, 60), (72, 60), 1)
            eye_color = (255, 80, 120, 245) if tier != "common" else (220, 220, 255, 220)

        # Face read and eyes.
        pygame.draw.ellipse(low, (*pal[3], 220), pygame.Rect(30, 26, 36, 28), 2)
        for ex in [40, 56]:
            pygame.draw.circle(low, eye_color, (ex, 40), 3)

        add_rune_strokes(low, rng)
        dither(low, 0.1)
        apply_fake_glow(low, pal[2], 3 if tier == "boss" else 2)
        final_grade(low)
        return pygame.transform.scale(low, (196, 196))

    def ensure_art(self, enemy_id: str, mode: str = "missing_only", tier: str = "common", biome: str = "ukhu"):
        path = self.out_dir / f"{enemy_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return
        surf = self._render(enemy_id, tier, biome)
        pygame.image.save(surf, str(path))
