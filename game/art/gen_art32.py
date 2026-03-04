from __future__ import annotations

import random
import zlib
import pygame

GEN_ART_VERSION = "art32_v1"
GEN_BIOME_VERSION = "biome_layer_v1"
DEFAULT_PALETTE = [(26, 18, 52), (74, 52, 120), (154, 112, 212), (240, 220, 170)]


def seed_from_id(id: str, version: str = GEN_ART_VERSION) -> int:
    return zlib.crc32(f"{version}:{id}".encode("utf-8")) & 0xFFFFFFFF


def palette_for_family(family: str) -> list[tuple[int, int, int]]:
    p = {
        "violet_arcane": [(26, 18, 52), (74, 52, 120), (154, 112, 212), (240, 220, 170)],
        "solar_gold": [(42, 22, 18), (116, 64, 30), (188, 138, 50), (255, 228, 160)],
        "emerald_spirit": [(12, 34, 26), (38, 92, 68), (76, 156, 122), (215, 246, 216)],
        "crimson_chaos": [(38, 10, 18), (98, 28, 44), (170, 52, 76), (252, 198, 176)],
        "azure_cosmic": [(12, 24, 52), (40, 82, 132), (80, 148, 210), (206, 238, 255)],
        "obsidian_void": [(8, 8, 12), (36, 36, 52), (78, 82, 104), (220, 224, 242)],
    }
    return p.get(family, p["violet_arcane"])


def chakana_points(center: tuple[int, int], size: int, step: float = 0.35) -> list[tuple[int, int]]:
    cx, cy = center
    s = max(4, int(size))
    k = max(2, int(s * step))
    return [
        (cx - k, cy - s), (cx + k, cy - s), (cx + k, cy - k), (cx + s, cy - k), (cx + s, cy + k),
        (cx + k, cy + k), (cx + k, cy + s), (cx - k, cy + s), (cx - k, cy + k), (cx - s, cy + k),
        (cx - s, cy - k), (cx - k, cy - k), (cx - k, cy - s), (cx, cy - s), (cx, cy - k),
        (cx + s, cy), (cx, cy + k), (cx, cy + s), (cx - k, cy), (cx - s, cy),
    ]


def dither(surface: pygame.Surface, strength=0.12):
    if isinstance(strength, random.Random):
        strength = 0.12
    w, h = surface.get_size()
    for y in range(0, h, 2):
        for x in range((y // 2) % 2, w, 2):
            c = surface.get_at((x, y))
            surface.set_at((x, y), (max(0, int(c.r * (1 - strength))), max(0, int(c.g * (1 - strength))), max(0, int(c.b * (1 - strength))), c.a))


def add_rune_strokes(surface: pygame.Surface, rng: random.Random, n: int = 16):
    w, h = surface.get_size()
    for _ in range(max(1, int(n))):
        x, y = rng.randint(8, w - 8), rng.randint(8, h - 8)
        pygame.draw.line(surface, (230, 230, 255, 110), (x, y), (x, y + rng.randint(4, 8)), 1)


def draw_sacred_geometry_bg(surface: pygame.Surface, *args):
    if len(args) == 1:
        rng = args[0]
        palette = DEFAULT_PALETTE
    elif len(args) == 2:
        palette, rng = args
    else:
        raise TypeError("draw_sacred_geometry_bg(surface, rng) or draw_sacred_geometry_bg(surface, palette, rng)")
    if not isinstance(palette, (list, tuple)) or len(palette) < 3:
        palette = DEFAULT_PALETTE
    w, h = surface.get_size()
    top, mid, hi = palette[0], palette[1], palette[2]
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + mid[0] * t)
        g = int(top[1] * (1 - t) + mid[1] * t)
        b = int(top[2] * (1 - t) + mid[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))
    cx, cy = w // 2, h // 2
    for i in range(1, 8):
        pygame.draw.circle(surface, (*hi, 22 + i * 6), (cx, cy), i * 10, 1)
    for i in range(0, w, 12):
        pygame.draw.line(surface, (180, 180, 220, 14), (i, 0), (i, h), 1)
    jitter = rng.randint(0, 1) if isinstance(rng, random.Random) else 0
    if jitter:
        pygame.draw.circle(surface, (hi[0], hi[1], hi[2], 35), (cx, cy), min(w, h) // 3, 1)


def draw_symbol(surface: pygame.Surface, symbol_type: str, rng: random.Random):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    col = (240, 226, 170, 235)
    if symbol_type == "sword":
        pygame.draw.line(surface, col, (cx - 18, cy + 26), (cx + 22, cy - 30), 5)
    elif symbol_type == "staff":
        pygame.draw.line(surface, col, (cx, cy - 34), (cx, cy + 34), 5); pygame.draw.circle(surface, col, (cx, cy - 40), 8)
    elif symbol_type == "cup":
        pygame.draw.rect(surface, col, pygame.Rect(cx - 20, cy - 8, 40, 20), 3, border_radius=3)
    elif symbol_type == "axe":
        pygame.draw.line(surface, col, (cx, cy - 36), (cx + 8, cy + 36), 5); pygame.draw.polygon(surface, col, [(cx - 24, cy - 8), (cx + 10, cy - 26), (cx + 2, cy + 8)])
    elif symbol_type == "tree":
        pygame.draw.line(surface, col, (cx, cy + 26), (cx, cy - 6), 5); pygame.draw.circle(surface, col, (cx, cy - 14), 18, 3)
    elif symbol_type == "orb":
        pygame.draw.circle(surface, col, (cx, cy), 22, 4)
    elif symbol_type == "mask":
        pygame.draw.ellipse(surface, col, pygame.Rect(cx - 22, cy - 26, 44, 52), 4)
    elif symbol_type == "condor":
        pygame.draw.lines(surface, col, False, [(cx - 30, cy + 8), (cx, cy - 16), (cx + 30, cy + 8)], 4)
    elif symbol_type == "puma":
        pygame.draw.lines(surface, col, False, [(cx - 26, cy + 12), (cx - 8, cy - 8), (cx + 18, cy + 8)], 4)
    elif symbol_type == "portal":
        pygame.draw.rect(surface, col, pygame.Rect(cx - 20, cy - 28, 40, 56), 4)
    else:
        pygame.draw.line(surface, col, (cx - 24, cy - 24), (cx + 24, cy + 24), 4); pygame.draw.line(surface, col, (cx + 24, cy - 24), (cx - 24, cy + 24), 4)


def apply_fake_glow(surface: pygame.Surface, color=(200, 160, 255), radius=2):
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface, (max(1, w // (2 + radius)), max(1, h // (2 + radius))))
    blur = pygame.transform.smoothscale(small, (w, h))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    glow.blit(blur, (0, 0)); glow.fill((*color, 28), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def final_grade(surface: pygame.Surface):
    w, h = surface.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(ov, (0, 0, 0, 42), ov.get_rect(), width=16)
    surface.blit(ov, (0, 0))
