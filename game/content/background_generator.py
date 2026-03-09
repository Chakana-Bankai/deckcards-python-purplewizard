from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_BIOME_VERSION, dither, seed_from_id
from game.core.paths import assets_dir
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class BackgroundGenerator:
    BIOMES = ["Templo Obsidiana", "Pampa Astral", "Ruinas Chakana", "Caverna Umbral", "Hiperborea"]

    def __init__(self):
        self.cache: dict[tuple[str, int], tuple[pygame.Surface, pygame.Surface, pygame.Surface]] = {}
        self.out_dir = assets_dir() / ".cache" / "biomes"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.version_seed = GEN_BIOME_VERSION

    def _biome_family(self, biome: str) -> str:
        b = str(biome or "").lower()
        if "hanan" in b or "astral" in b:
            return "hanan"
        if "kay" in b or "ruinas" in b or "chakana" in b:
            return "kay"
        if "ukhu" in b or "umbral" in b or "caverna" in b or "obsidiana" in b:
            return "ukhu"
        if "hiper" in b or "polar" in b:
            return "hiperborea"
        if "fractura" in b or "boss" in b:
            return "fractura"
        return "kay"

    def _palette(self, family: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        palettes = {
            "hanan": ((20, 34, 72), (82, 126, 198), (228, 240, 255)),
            "kay": ((34, 24, 54), (108, 72, 146), (232, 214, 176)),
            "ukhu": ((14, 12, 22), (56, 36, 68), (186, 128, 146)),
            "hiperborea": ((18, 30, 50), (86, 146, 204), (238, 236, 214)),
            "fractura": ((20, 8, 14), (104, 24, 40), (242, 166, 184)),
        }
        return palettes.get(family, palettes["kay"])

    def _draw_gradient(self, bg: pygame.Surface, top: tuple[int, int, int], bot: tuple[int, int, int]):
        for y in range(180):
            t = y / 179.0
            col = (
                int(top[0] * (1 - t) + bot[0] * t),
                int(top[1] * (1 - t) + bot[1] * t),
                int(top[2] * (1 - t) + bot[2] * t),
                255,
            )
            pygame.draw.line(bg, col, (0, y), (319, y))

    def _draw_hanan(self, rng: random.Random, mg: pygame.Surface, fg: pygame.Surface, accent: tuple[int, int, int]):
        # Mountain silhouettes + celestial rings.
        peaks = [(0, 170)]
        x = 0
        while x < 320:
            x += rng.randint(20, 38)
            peaks.append((min(320, x), rng.randint(72, 124)))
        peaks += [(320, 170), (0, 170)]
        pygame.draw.polygon(mg, (28, 30, 52, 176), peaks)
        for _ in range(7):
            cx, cy = rng.randint(40, 280), rng.randint(30, 88)
            pygame.draw.circle(fg, (*accent, 64), (cx, cy), rng.randint(12, 24), 1)

    def _draw_kay(self, rng: random.Random, mg: pygame.Surface, fg: pygame.Surface, accent: tuple[int, int, int]):
        # Valley + ritual architecture.
        for _ in range(10):
            x = rng.randint(0, 300)
            w = rng.randint(10, 22)
            h = rng.randint(38, 84)
            pygame.draw.rect(mg, (32, 24, 42, 166), (x, 180 - h, w, h))
            if rng.random() < 0.55:
                pygame.draw.rect(mg, (*accent, 44), (x + 2, 180 - h + 6, max(2, w - 4), 2))
        for _ in range(14):
            x = rng.randint(0, 319)
            y = rng.randint(102, 176)
            pygame.draw.circle(fg, (*accent, rng.randint(28, 66)), (x, y), rng.randint(1, 3))

    def _draw_ukhu(self, rng: random.Random, mg: pygame.Surface, fg: pygame.Surface, accent: tuple[int, int, int]):
        # Jagged underworld spikes + corrupted fog/rifts.
        for _ in range(12):
            x = rng.randint(0, 318)
            w = rng.randint(8, 18)
            h = rng.randint(52, 124)
            poly = [(x, 180), (x + w // 2, 180 - h), (x + w, 180)]
            pygame.draw.polygon(mg, (26, 18, 34, 176), poly)
        for _ in range(8):
            x, y = rng.randint(20, 300), rng.randint(70, 160)
            pygame.draw.line(fg, (*accent, 72), (x - 8, y - 3), (x + 9, y + 3), 1)

    def _draw_hiperborea(self, rng: random.Random, mg: pygame.Surface, fg: pygame.Surface, accent: tuple[int, int, int]):
        # Ice spires + aurora bands.
        for _ in range(9):
            x = rng.randint(0, 310)
            h = rng.randint(50, 110)
            w = rng.randint(8, 16)
            pygame.draw.polygon(mg, (24, 38, 62, 170), [(x, 180), (x + w // 2, 180 - h), (x + w, 180)])
            pygame.draw.line(mg, (*accent, 86), (x + w // 2, 180 - h), (x + w // 2, 180 - h + 18), 1)
        for _ in range(4):
            y = rng.randint(24, 82)
            start = rng.randint(-60, 0)
            color = (accent[0], accent[1], min(255, accent[2] + 26), 58)
            pygame.draw.arc(fg, color, pygame.Rect(start, y, 420, rng.randint(28, 42)), 0.2, 2.9, 2)

    def _draw_fractura(self, rng: random.Random, mg: pygame.Surface, fg: pygame.Surface, accent: tuple[int, int, int]):
        # Broken shards + unstable cracks.
        for _ in range(13):
            x = rng.randint(0, 320)
            y = rng.randint(70, 180)
            pts = [(x, y), (x + rng.randint(10, 22), y - rng.randint(10, 32)), (x + rng.randint(20, 36), y + rng.randint(2, 10))]
            pygame.draw.polygon(mg, (42, 14, 22, 182), pts)
        for _ in range(10):
            x = rng.randint(18, 302)
            y = rng.randint(40, 162)
            pygame.draw.line(fg, (*accent, 88), (x, y), (x + rng.randint(-14, 14), y + rng.randint(8, 22)), 1)

    def _make_low_layer(self, biome: str, seed: int):
        family = self._biome_family(biome)
        rng = random.Random(seed_from_id(f"{family}:{biome}:{seed}", self.version_seed))
        bg = pygame.Surface((320, 180), pygame.SRCALPHA)
        mg = pygame.Surface((320, 180), pygame.SRCALPHA)
        fg = pygame.Surface((320, 180), pygame.SRCALPHA)

        top, bot, accent = self._palette(family)
        self._draw_gradient(bg, top, bot)

        # Family-specific stars/atmosphere density.
        star_count = {"hanan": 52, "kay": 24, "ukhu": 16, "hiperborea": 36, "fractura": 22}.get(family, 28)
        for _ in range(star_count):
            pygame.draw.circle(bg, (210, 220, 255, rng.randint(24, 118)), (rng.randint(0, 319), rng.randint(0, 112)), rng.randint(1, 2))

        if family == "hanan":
            self._draw_hanan(rng, mg, fg, accent)
        elif family == "ukhu":
            self._draw_ukhu(rng, mg, fg, accent)
        elif family == "hiperborea":
            self._draw_hiperborea(rng, mg, fg, accent)
        elif family == "fractura":
            self._draw_fractura(rng, mg, fg, accent)
        else:
            self._draw_kay(rng, mg, fg, accent)

        # Shared sacred/corrupted motif overlays.
        for _ in range(5):
            cx, cy = rng.randint(30, 290), rng.randint(28, 94)
            r = rng.randint(8, 18)
            pygame.draw.circle(fg, (*accent, 28), (cx, cy), r, 1)
            if rng.random() < 0.45:
                pygame.draw.line(fg, (*accent, 24), (cx - r, cy), (cx + r, cy), 1)
                pygame.draw.line(fg, (*accent, 24), (cx, cy - r), (cx, cy + r), 1)

        dither(bg, 0.12)
        dither(mg, 0.08)
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
