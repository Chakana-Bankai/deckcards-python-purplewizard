from __future__ import annotations

from pathlib import Path

import pygame

from game.core.paths import assets_dir
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class BackgroundGenerator:
    BIOMES = ["Templo Obsidiana", "Pampa Astral", "Ruinas Chakana", "Caverna Umbral"]

    def __init__(self):
        self.cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface, pygame.Surface]] = {}
        self.out_dir = assets_dir() / "backgrounds"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _rng(self, seed: int):
        return (seed * 1103515245 + 12345) & 0x7FFFFFFF

    def _gradient(self, top, bottom):
        surf = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        for y in range(INTERNAL_HEIGHT):
            t = y / max(1, INTERNAL_HEIGHT - 1)
            c = (
                int(top[0] * (1 - t) + bottom[0] * t),
                int(top[1] * (1 - t) + bottom[1] * t),
                int(top[2] * (1 - t) + bottom[2] * t),
            )
            pygame.draw.line(surf, c, (0, y), (INTERNAL_WIDTH, y))
        return surf

    def _make_layers(self, biome: str, seed: int):
        palette = {
            "Templo Obsidiana": ((40, 28, 66), (9, 10, 22)),
            "Pampa Astral": ((58, 44, 90), (16, 20, 38)),
            "Ruinas Chakana": ((69, 35, 72), (16, 13, 34)),
            "Caverna Umbral": ((28, 24, 48), (7, 7, 18)),
        }
        top, bottom = palette.get(biome, ((44, 30, 70), (12, 14, 26)))
        sky = self._gradient(top, bottom)
        silhouettes = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        fog = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        val = seed
        for i in range(18):
            val = self._rng(val + i)
            x = val % INTERNAL_WIDTH
            h = 130 + (val % 360)
            w = 40 + (val % 120)
            y = INTERNAL_HEIGHT - h
            pygame.draw.rect(silhouettes, (20, 12, 30, 130), (x, y, w, h))
            pygame.draw.rect(silhouettes, (34, 20, 48, 90), (x + 4, y + 8, w - 8, h - 8))
        for i in range(120):
            val = self._rng(val + i * 3)
            x = val % INTERNAL_WIDTH
            y = (val // 3) % INTERNAL_HEIGHT
            a = 16 + (val % 32)
            fog.set_at((x, y), (170, 120, 220, a))
        for y in range(0, INTERNAL_HEIGHT, 2):
            for x in range((y // 2) % 2, INTERNAL_WIDTH, 2):
                c = sky.get_at((x, y))
                sky.set_at((x, y), (max(0, c.r - 4), max(0, c.g - 4), max(0, c.b - 4)))
        return sky, silhouettes, fog

    def get_layers(self, biome: str, seed: int):
        key = (biome, seed)
        if key not in self.cache:
            layers = self._make_layers(biome, seed)
            self.cache[key] = layers
            out = self.out_dir / f"{biome.replace(' ', '_').lower()}_{seed}.png"
            if not out.exists():
                snap = layers[0].copy()
                snap.blit(layers[1], (0, 0))
                snap.blit(layers[2], (0, 0))
                pygame.image.save(snap, str(out))
        return self.cache[key]
