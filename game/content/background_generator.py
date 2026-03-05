from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_BIOME_VERSION, dither, seed_from_id
from game.core.paths import assets_dir
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class BackgroundGenerator:
    BIOMES = ["Templo Obsidiana", "Pampa Astral", "Ruinas Chakana", "Caverna Umbral"]

    def __init__(self):
        self.cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface, pygame.Surface]] = {}
        self.out_dir = assets_dir() / ".cache" / "biomes"
        self.out_dir = assets_dir() / "sprites" / "biomes"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.version_seed = GEN_BIOME_VERSION

    def _make_low_layer(self, biome: str, seed: int):
        rng = random.Random(seed_from_id(f"{biome}:{seed}", self.version_seed))
        bg = pygame.Surface((320, 180), pygame.SRCALPHA)
        mg = pygame.Surface((320, 180), pygame.SRCALPHA)
        fg = pygame.Surface((320, 180), pygame.SRCALPHA)
        palettes = {
            "Templo Obsidiana": ((25, 20, 42), (68, 54, 92)),
            "Pampa Astral": ((28, 38, 70), (72, 102, 162)),
            "Ruinas Chakana": ((38, 24, 60), (98, 66, 142)),
            "Caverna Umbral": ((18, 20, 34), (48, 56, 78)),
        }
        top, bot = palettes.get(biome, ((30, 26, 50), (86, 66, 130)))
        for y in range(180):
            t = y / 179.0
            col = (int(top[0] * (1 - t) + bot[0] * t), int(top[1] * (1 - t) + bot[1] * t), int(top[2] * (1 - t) + bot[2] * t), 255)
            pygame.draw.line(bg, col, (0, y), (319, y))
        for _ in range(40):
            pygame.draw.circle(bg, (210, 220, 255, rng.randint(40, 120)), (rng.randint(0, 319), rng.randint(0, 100)), rng.randint(1, 2))
        for _ in range(16):
            x = rng.randint(0, 319); w = rng.randint(12, 36); h = rng.randint(46, 110)
            pygame.draw.rect(mg, (20, 18, 30, 160), (x, 180 - h, w, h))
        for _ in range(22):
            x = rng.randint(0, 319); y = rng.randint(90, 179)
            pygame.draw.circle(fg, (170, 150, 220, rng.randint(24, 70)), (x, y), rng.randint(1, 3))
        dither(bg, 0.12); dither(mg, 0.08)
        return bg, mg, fg

    def _save_layers(self, biome: str, layers):
        bdir = self.out_dir / biome.lower().replace(" ", "_")
        bdir.mkdir(parents=True, exist_ok=True)
        names = ["bg", "mg", "fg"]
        scaled = []
        for i, layer in enumerate(layers):
            big = pygame.transform.scale(layer, (INTERNAL_WIDTH, INTERNAL_HEIGHT))
            pygame.image.save(big, str(bdir / f"{names[i]}.png"))
            scaled.append(big)
        return tuple(scaled)

    def get_layers(self, biome: str, seed: int):
        key = (biome, seed)
        if key not in self.cache:
            layers = self._make_low_layer(biome, seed)
            self.cache[key] = self._save_layers(biome, layers)
        return self.cache[key]

    def render_parallax(self, surface: pygame.Surface, biome: str, seed: int, t: float, clip_rect: pygame.Rect | None = None, particles_on: bool = True):
        bg, mg, fg = self.get_layers(biome, seed)
        old = surface.get_clip()
        if clip_rect is not None:
            surface.set_clip(clip_rect)
        o1 = int((t * 0.2) % 64)
        o2 = int((t * 0.5) % 128)
        o3 = int((t * 1.2) % 200)
        surface.blit(bg, (0, 0))
        surface.blit(mg, (-o1, 0)); surface.blit(mg, (INTERNAL_WIDTH - o1, 0))
        if particles_on:
            surface.blit(fg, (-o3, 0)); surface.blit(fg, (INTERNAL_WIDTH - o3, 0))
        else:
            surface.blit(fg, (-o2, 0)); surface.blit(fg, (INTERNAL_WIDTH - o2, 0))
        if clip_rect is not None:
            surface.set_clip(old)
