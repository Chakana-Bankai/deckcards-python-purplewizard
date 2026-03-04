from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, add_rune_strokes, apply_fake_glow, dither, final_grade, palette_for_family, seed_from_id
from game.core.paths import assets_dir


class EnemyArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "enemies"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.version_seed = GEN_ART_VERSION

    def _render(self, enemy_id: str, tier: str = "common", biome: str = "ukhu"):
        rng = random.Random(seed_from_id(enemy_id, self.version_seed))
        low = pygame.Surface((96, 96), pygame.SRCALPHA)
        fam = "obsidian_void" if tier == "common" else "crimson_chaos" if tier == "elite" else "violet_arcane"
        pal = palette_for_family(fam)
        low.fill((*pal[0], 255))
        # silhouette
        pts = [(rng.randint(12, 30), 82), (rng.randint(18, 36), rng.randint(24, 40)), (48, rng.randint(8, 20)), (rng.randint(60, 78), rng.randint(24, 40)), (rng.randint(66, 84), 82)]
        pygame.draw.polygon(low, (*pal[2], 230), pts)
        # mask + eyes
        pygame.draw.ellipse(low, (*pal[3], 220), pygame.Rect(30, 26, 36, 28), 2)
        for ex in [40, 56]:
            pygame.draw.circle(low, (255, 80, 120, 245) if tier != "common" else (220, 220, 255, 220), (ex, 40), 3)
        # aura
        pygame.draw.circle(low, (*pal[1], 120), (48, 44), 34, 2)
        add_rune_strokes(low, rng)
        dither(low, 0.1)
        apply_fake_glow(low, pal[2], 2)
        final_grade(low)
        return pygame.transform.scale(low, (196, 196))

    def ensure_art(self, enemy_id: str, mode: str = "missing_only", tier: str = "common", biome: str = "ukhu"):
        path = self.out_dir / f"{enemy_id}.png"
        if path.exists() and mode not in {"force_regen"}:
            return
        surf = self._render(enemy_id, tier, biome)
        pygame.image.save(surf, str(path))
