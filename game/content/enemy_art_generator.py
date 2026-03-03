from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.core.paths import assets_dir


class EnemyArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "enemies"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _variance(self, surf: pygame.Surface) -> float:
        sample = []
        w, h = surf.get_size()
        for y in range(0, h, max(1, h // 16)):
            for x in range(0, w, max(1, w // 16)):
                sample.append(surf.get_at((x, y))[:3])
        rs = [p[0] for p in sample]
        gs = [p[1] for p in sample]
        bs = [p[2] for p in sample]
        return float((max(rs) - min(rs)) + (max(gs) - min(gs)) + (max(bs) - min(bs)))

    def _is_uniform(self, path: Path) -> bool:
        try:
            surf = pygame.image.load(str(path)).convert_alpha()
        except Exception:
            return True
        return self._variance(surf) < 60.0

    def _render(self, enemy_id: str, salt: int = 0):
        rng = random.Random(f"{enemy_id}:{salt}")
        surf = pygame.Surface((196, 196))
        base = (48 + rng.randint(0, 50), 30 + rng.randint(0, 42), 66 + rng.randint(0, 56))
        surf.fill(base)
        for y in range(0, 196, 2):
            for x in range((y // 2) % 2, 196, 2):
                surf.set_at((x, y), (base[0] + 14, base[1] + 10, base[2] + 18))
        pygame.draw.circle(surf, (228, 216, 255), (62, 78), 14)
        pygame.draw.circle(surf, (228, 216, 255), (132, 78), 14)
        pygame.draw.circle(surf, (22, 16, 34), (62, 78), 6)
        pygame.draw.circle(surf, (22, 16, 34), (132, 78), 6)
        for _ in range(24):
            x = rng.randint(10, 186)
            y = rng.randint(104, 188)
            pygame.draw.line(surf, (172, 124, 222), (98, 122), (x, y), 1)
        pygame.draw.rect(surf, (226, 192, 246), surf.get_rect(), 4)
        return surf

    def _generate_and_save(self, enemy_id: str, path: Path):
        surf = self._render(enemy_id, 0)
        if self._variance(surf) < 65:
            surf = self._render(enemy_id, 1)
        pygame.image.save(surf, str(path))

    def ensure_art(self, enemy_id: str, mode: str = "missing_only"):
        path = self.out_dir / f"{enemy_id}.png"
        if mode == "off":
            if path.exists():
                print(f"Using existing art: {enemy_id}")
            return
        if mode == "force_regen":
            self._generate_and_save(enemy_id, path)
            print(f"Generated art: {enemy_id} -> {path}")
            return
        if not path.exists():
            self._generate_and_save(enemy_id, path)
            print(f"Generated art: {enemy_id} -> {path}")
            return
        if self._is_uniform(path):
            self._generate_and_save(enemy_id, path)
            print(f"Replaced uniform placeholder: {enemy_id} -> {path}")
            return
        print(f"Using existing art: {enemy_id}")
