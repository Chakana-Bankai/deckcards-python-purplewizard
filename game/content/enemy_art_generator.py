from __future__ import annotations

from pathlib import Path
import random
import pygame

from game.core.paths import assets_dir


class EnemyArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "enemies"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def ensure_art(self, enemy_id: str):
        path = self.out_dir / f"{enemy_id}.png"
        if path.exists():
            return
        rng = random.Random(enemy_id)
        surf = pygame.Surface((128, 128))
        base = (60 + rng.randint(0, 40), 30 + rng.randint(0, 30), 60 + rng.randint(0, 50))
        surf.fill(base)
        for y in range(0, 128, 2):
            for x in range((y // 2) % 2, 128, 2):
                surf.set_at((x, y), (base[0] + 12, base[1] + 8, base[2] + 15))
        eye = (230, 210, 255)
        pygame.draw.circle(surf, eye, (44, 52), 8)
        pygame.draw.circle(surf, eye, (84, 52), 8)
        pygame.draw.circle(surf, (30, 20, 40), (44, 52), 3)
        pygame.draw.circle(surf, (30, 20, 40), (84, 52), 3)
        for _ in range(14):
            x = rng.randint(8, 120)
            y = rng.randint(70, 118)
            pygame.draw.line(surf, (170, 120, 210), (64, 88), (x, y), 1)
        pygame.draw.rect(surf, (220, 190, 245), surf.get_rect(), 3)
        pygame.image.save(surf, str(path))
        print(f"[art] Generated enemy art: {enemy_id} -> {path}")
