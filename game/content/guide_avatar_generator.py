from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import add_rune_strokes, apply_fake_glow, dither, draw_sacred_geometry_bg, final_grade, seed_from_id
from game.core.paths import assets_dir


GUIDE_TYPES = ["angel", "shaman", "demon", "arcane_hacker"]


class GuideAvatarGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "guides"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _mask(self, surf: pygame.Surface, t: str, rng: random.Random):
        w, h = surf.get_size()
        cx, cy = w // 2, h // 2
        tone = {
            "angel": (220, 206, 255),
            "shaman": (155, 190, 145),
            "demon": (220, 102, 142),
            "arcane_hacker": (120, 214, 235),
        }.get(t, (200, 180, 240))
        if t == "angel":
            pygame.draw.ellipse(surf, tone, (cx - 22, cy - 24, 44, 54))
        elif t == "shaman":
            pygame.draw.polygon(surf, tone, [(cx - 24, cy - 18), (cx + 24, cy - 18), (cx + 16, cy + 28), (cx - 16, cy + 28)])
        elif t == "demon":
            pygame.draw.polygon(surf, tone, [(cx, cy - 30), (cx + 28, cy - 8), (cx + 18, cy + 30), (cx - 18, cy + 30), (cx - 28, cy - 8)])
            pygame.draw.polygon(surf, (180, 70, 110), [(cx - 18, cy - 22), (cx - 8, cy - 44), (cx - 2, cy - 20)])
            pygame.draw.polygon(surf, (180, 70, 110), [(cx + 18, cy - 22), (cx + 8, cy - 44), (cx + 2, cy - 20)])
        else:
            pygame.draw.rect(surf, tone, (cx - 24, cy - 20, 48, 52), border_radius=8)
            for i in range(3):
                pygame.draw.line(surf, (80, 190, 220), (cx - 22, cy - 16 + i * 8), (cx + 22, cy - 16 + i * 8), 1)

        ey = cy - 2
        for ex in (cx - 9, cx + 9):
            pygame.draw.circle(surf, (20, 18, 30), (ex, ey), 4)
            pygame.draw.circle(surf, (235, 245, 255), (ex, ey), 2)
        add_rune_strokes(surf, rng, n=8)

    def generate(self, guide_type: str, mode: str = "missing_only") -> Path:
        gt = guide_type if guide_type in GUIDE_TYPES else "angel"
        out = self.out_dir / f"{gt}.png"
        if out.exists() and mode == "missing_only":
            return out
        rng = random.Random(seed_from_id(f"guide:{gt}", "guide-v1"))
        low = pygame.Surface((64, 64))
        draw_sacred_geometry_bg(low, ((38, 28, 58), (90, 64, 140), (214, 188, 96)), rng)
        self._mask(low, gt, rng)
        dither(low, rng)
        apply_fake_glow(low)
        final_grade(low)
        hi = pygame.transform.scale(low, (256, 256))
        pygame.image.save(hi, out)
        return out
