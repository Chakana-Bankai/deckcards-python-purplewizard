from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import seed_from_id

GEN_CARD_ART_VERSION = "card_gen_v4"

TYPE_PALETTES = {
    "attack": ((24, 8, 20), (126, 24, 44), (236, 110, 40), (96, 26, 112)),
    "defense": ((10, 28, 36), (20, 98, 106), (56, 164, 126), (74, 40, 130)),
    "control": ((10, 24, 56), (24, 56, 140), (64, 98, 196), (78, 236, 246)),
    "spirit": ((10, 10, 16), (78, 56, 24), (184, 146, 56), (108, 64, 156)),
}


def _family_to_type(card_type: str) -> str:
    c = (card_type or "").strip().lower()
    if c in TYPE_PALETTES:
        return c
    mapping = {
        "crimson_chaos": "attack",
        "emerald_spirit": "defense",
        "azure_cosmic": "control",
        "violet_arcane": "spirit",
        "solar_gold": "spirit",
    }
    return mapping.get(c, "spirit")


def _draw_gradient(surface: pygame.Surface, pal):
    w, h = surface.get_size()
    top, mid, low, _acc = pal
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.55:
            q = t / 0.55
            r = int(top[0] * (1 - q) + mid[0] * q)
            g = int(top[1] * (1 - q) + mid[1] * q)
            b = int(top[2] * (1 - q) + mid[2] * q)
        else:
            q = (t - 0.55) / 0.45
            r = int(mid[0] * (1 - q) + low[0] * q)
            g = int(mid[1] * (1 - q) + low[1] * q)
            b = int(mid[2] * (1 - q) + low[2] * q)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))
    vign = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(vign, (0, 0, 0, 88), vign.get_rect(), width=max(8, w // 10))
    surface.blit(vign, (0, 0))


def _add_dither(surface: pygame.Surface, rng: random.Random):
    w, h = surface.get_size()
    for y in range(h):
        for x in range((y + rng.randint(0, 1)) % 2, w, 2):
            c = surface.get_at((x, y))
            delta = rng.randint(-10, 10)
            surface.set_at((x, y), (max(0, min(255, c.r + delta)), max(0, min(255, c.g + delta)), max(0, min(255, c.b + delta)), c.a))


def _draw_rosette(surface: pygame.Surface, rng: random.Random, color):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    r = min(w, h) // 4
    for ring in range(1, 4):
        rr = r * ring // 2
        for i in range(6):
            ang = (i / 6.0) * 6.2831853 + rng.random() * 0.2
            ox = int(cx + rr * pygame.math.Vector2(1, 0).rotate_rad(ang).x)
            oy = int(cy + rr * pygame.math.Vector2(1, 0).rotate_rad(ang).y)
            pygame.draw.circle(surface, (*color, 70), (ox, oy), r // 2, 1)


def _draw_concentric(surface: pygame.Surface, rng: random.Random, color):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    for i in range(6, min(w, h) // 2, 8):
        pygame.draw.circle(surface, (*color, 66), (cx + rng.randint(-2, 2), cy + rng.randint(-2, 2)), i, 1)


def _draw_grid_nodes(surface: pygame.Surface, rng: random.Random, color):
    w, h = surface.get_size()
    step = 12 + rng.randint(0, 4)
    for x in range(-w // 2, w + w // 2, step):
        pygame.draw.line(surface, (*color, 40), (x, 0), (x + h, h), 1)
    for x in range(0, w, step * 2):
        for y in range(0, h, step * 2):
            pygame.draw.circle(surface, (*color, 90), (x + rng.randint(-1, 1), y + rng.randint(-1, 1)), 1)


def _draw_chakana_frame(surface: pygame.Surface, color):
    w, h = surface.get_size()
    r = pygame.Rect(10, 8, w - 20, h - 16)
    step = 8
    pts = [
        (r.left + step, r.top), (r.right - step, r.top), (r.right - step, r.top + step), (r.right, r.top + step),
        (r.right, r.bottom - step), (r.right - step, r.bottom - step), (r.right - step, r.bottom), (r.left + step, r.bottom),
        (r.left + step, r.bottom - step), (r.left, r.bottom - step), (r.left, r.top + step), (r.left + step, r.top + step),
    ]
    pygame.draw.lines(surface, (*color, 124), True, pts, 2)


def _draw_geometry(surface: pygame.Surface, variant: int, rng: random.Random, color):
    if variant == 0:
        _draw_rosette(surface, rng, color)
    elif variant == 1:
        _draw_concentric(surface, rng, color)
    elif variant == 2:
        _draw_grid_nodes(surface, rng, color)
    else:
        _draw_chakana_frame(surface, color)


def _draw_glyph(surface: pygame.Surface, glyph: str, color):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    if glyph == "sword":
        pygame.draw.line(surface, color, (cx - 18, cy + 24), (cx + 16, cy - 24), 4)
        pygame.draw.line(surface, color, (cx - 8, cy + 8), (cx + 8, cy + 8), 2)
    elif glyph == "shield":
        pygame.draw.polygon(surface, color, [(cx, cy - 24), (cx + 20, cy - 6), (cx + 12, cy + 22), (cx - 12, cy + 22), (cx - 20, cy - 6)], 3)
    elif glyph == "eye":
        pygame.draw.ellipse(surface, color, (cx - 26, cy - 14, 52, 28), 3)
        pygame.draw.circle(surface, color, (cx, cy), 6)
    elif glyph == "orb":
        pygame.draw.circle(surface, color, (cx, cy), 20, 3)
        pygame.draw.circle(surface, color, (cx + 6, cy - 6), 4)
    elif glyph == "mask":
        pygame.draw.ellipse(surface, color, (cx - 22, cy - 28, 44, 56), 3)
        pygame.draw.circle(surface, color, (cx - 8, cy - 4), 2)
        pygame.draw.circle(surface, color, (cx + 8, cy - 4), 2)
    else:
        pygame.draw.rect(surface, color, (cx - 20, cy - 26, 40, 52), 3, border_radius=4)
        pygame.draw.rect(surface, color, (cx - 12, cy - 18, 24, 36), 1, border_radius=2)


def _draw_silhouette(surface: pygame.Surface, ctype: str, accent: tuple[int, int, int]):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    lay = pygame.Surface((w, h), pygame.SRCALPHA)
    if ctype == "attack":
        poly = [(cx - 34, cy + 26), (cx - 4, cy - 32), (cx + 24, cy - 8), (cx + 8, cy + 30)]
    elif ctype == "defense":
        poly = [(cx, cy - 34), (cx + 30, cy - 6), (cx + 18, cy + 34), (cx - 18, cy + 34), (cx - 30, cy - 6)]
    elif ctype == "control":
        poly = [(cx, cy - 30), (cx + 34, cy), (cx, cy + 30), (cx - 34, cy)]
    else:
        poly = [(cx - 24, cy - 22), (cx + 24, cy - 22), (cx + 32, cy + 12), (cx, cy + 34), (cx - 32, cy + 12)]
    pygame.draw.polygon(lay, (*accent, 52), poly)
    pygame.draw.polygon(lay, (*accent, 124), poly, 2)
    surface.blit(lay, (0, 0))


def _draw_energy(surface: pygame.Surface, rng: random.Random, accent: tuple[int, int, int]):
    w, h = surface.get_size()
    fx = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(8):
        x1, y1 = rng.randint(8, w - 8), rng.randint(8, h - 8)
        x2, y2 = x1 + rng.randint(-20, 20), y1 + rng.randint(-20, 20)
        pygame.draw.line(fx, (*accent, 122), (x1, y1), (x2, y2), 1)
    surface.blit(fx, (0, 0))


def _hash16(surface: pygame.Surface) -> int:
    tiny = pygame.transform.smoothscale(surface, (16, 16))
    total = 0
    for y in range(16):
        for x in range(16):
            c = tiny.get_at((x, y))
            total += c.r + c.g + c.b
    return total


def _prompt_hint(prompt: str) -> str:
    p = str(prompt or "").lower()
    if "cosmic_warrior" in p or "blade" in p:
        return "attack"
    if "harmony_guardian" in p or "shield" in p:
        return "defense"
    if "oracle_of_fate" in p or "eye geometry" in p:
        return "control"
    return "spirit"


def generate(card_id: str, card_type: str, prompt: str, seed: int, out_path: Path) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ctype = _family_to_type(card_type)
    hint = _prompt_hint(prompt)
    if hint != "spirit":
        ctype = hint
    pal = TYPE_PALETTES.get(ctype, TYPE_PALETTES["spirit"])
    glyphs = ["sword", "shield", "eye", "orb", "mask", "portal"]
    last_hash = None
    chosen_variant = 0
    for attempt in range(4):
        rng = random.Random(seed + attempt * 313)
        low = pygame.Surface((160, 112), pygame.SRCALPHA, 32)
        _draw_gradient(low, pal)
        _add_dither(low, rng)

        chosen_variant = (seed + attempt) % 4
        _draw_geometry(low, chosen_variant, rng, pal[3])
        _draw_geometry(low, (chosen_variant + 2) % 4, rng, pal[2])
        _draw_silhouette(low, ctype, pal[2])

        glyph = glyphs[(seed + attempt) % len(glyphs)]
        if ctype == "attack":
            glyph = "sword"
        elif ctype == "defense":
            glyph = "shield"
        elif ctype == "control":
            glyph = "eye"
        _draw_glyph(low, glyph, pal[2])

        _draw_energy(low, rng, pal[3])

        for c in [(6, 6), (154, 6), (6, 106), (154, 106)]:
            pygame.draw.circle(low, pal[3], c, 4, 1)
        vign = pygame.Surface((160, 112), pygame.SRCALPHA)
        pygame.draw.rect(vign, (0, 0, 0, 96), vign.get_rect(), width=10)
        low.blit(vign, (0, 0))

        h = _hash16(low)
        if last_hash is None or abs(h - last_hash) > 120:
            last_hash = h
            break
        last_hash = h

    out = pygame.transform.scale(low, (320, 220)).convert_alpha()
    pygame.image.save(out, str(out_path))
    return {
        "card_id": card_id,
        "card_type": ctype,
        "prompt": prompt,
        "generator_used": GEN_CARD_ART_VERSION,
        "variant": chosen_variant,
        "hash16": int(last_hash or 0),
        "path": str(out_path),
    }


def render_card(card_id: str, family: str, symbol: str) -> pygame.Surface:
    ctype = _family_to_type(family)
    pal = TYPE_PALETTES.get(ctype, TYPE_PALETTES["spirit"])
    seed = seed_from_id(card_id, GEN_CARD_ART_VERSION)
    rng = random.Random(seed)
    low = pygame.Surface((160, 112), pygame.SRCALPHA, 32)
    _draw_gradient(low, pal)
    _add_dither(low, rng)
    _draw_geometry(low, seed % 4, rng, pal[3])
    _draw_silhouette(low, ctype, pal[2])
    _draw_glyph(low, ["sword", "shield", "eye", "orb", "mask", "portal"][seed % 6], pal[2])
    _draw_energy(low, rng, pal[3])
    return pygame.transform.scale(low, (320, 220)).convert_alpha()
