from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.core.paths import assets_dir
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class BackgroundGenerator:
    BIOMES = ["Templo Obsidiana", "Pampa Astral", "Ruinas Chakana", "Caverna Umbral"]

    def __init__(self):
        self.cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface, pygame.Surface, pygame.Surface]] = {}
        self.out_dir = assets_dir() / "backgrounds"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _gradient(self, top, bottom):
        surf = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        for y in range(INTERNAL_HEIGHT):
            t = y / max(1, INTERNAL_HEIGHT - 1)
            c = (
                int(top[0] * (1 - t) + bottom[0] * t),
                int(top[1] * (1 - t) + bottom[1] * t),
                int(top[2] * (1 - t) + bottom[2] * t),
                255,
            )
            pygame.draw.line(surf, c, (0, y), (INTERNAL_WIDTH, y))
        return surf

    def _make_layers(self, biome: str, seed: int):
        palette = {
            "Templo Obsidiana": ((34, 25, 55), (8, 10, 20)),
            "Pampa Astral": ((52, 58, 92), (14, 20, 38)),
            "Ruinas Chakana": ((58, 40, 84), (14, 12, 30)),
            "Caverna Umbral": ((22, 24, 42), (6, 7, 18)),
        }
        top, bottom = palette.get(biome, ((44, 30, 70), (12, 14, 26)))
        bg = self._gradient(top, bottom)
        mid = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        fg = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        particles = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        rng = random.Random(f"{biome}:{seed}")

        for _ in range(28):
            x = rng.randint(0, INTERNAL_WIDTH - 1)
            w = rng.randint(28, 130)
            h = rng.randint(120, 420)
            y = INTERNAL_HEIGHT - h
            pygame.draw.rect(mid, (24, 18, 38, 120), (x, y, w, h), border_radius=4)
        for _ in range(22):
            x = rng.randint(0, INTERNAL_WIDTH - 1)
            w = rng.randint(20, 100)
            h = rng.randint(80, 260)
            y = INTERNAL_HEIGHT - h
            pygame.draw.rect(fg, (16, 14, 26, 130), (x, y, w, h), border_radius=3)

        for _ in range(180):
            x = rng.randint(0, INTERNAL_WIDTH - 1)
            y = rng.randint(0, INTERNAL_HEIGHT - 1)
            a = rng.randint(15, 55)
            particles.set_at((x, y), (190, 170, 230, a))

        return bg, mid, fg, particles

    def get_layers(self, biome: str, seed: int):
        key = (biome, seed)
        if key not in self.cache:
            self.cache[key] = self._make_layers(biome, seed)
        return self.cache[key]

    def render_parallax(self, surface: pygame.Surface, biome: str, seed: int, t: float, clip_rect: pygame.Rect | None = None, particles_on: bool = True):
        bg, mid, fg, particles = self.get_layers(biome, seed)
        old_clip = surface.get_clip()
        if clip_rect is not None:
            surface.set_clip(clip_rect)
        o1 = int((t * 0.2) % 40)
        o2 = int((t * 0.5) % 80)
        o3 = int((t * 1.2) % 120)
        surface.blit(bg, (0, 0))
        surface.blit(mid, (-o1, 0)); surface.blit(mid, (INTERNAL_WIDTH - o1, 0))
        surface.blit(fg, (-o2, 0)); surface.blit(fg, (INTERNAL_WIDTH - o2, 0))
        if particles_on:
            surface.blit(particles, (-o3, 0)); surface.blit(particles, (INTERNAL_WIDTH - o3, 0))
        if clip_rect is not None:
            surface.set_clip(old_clip)
