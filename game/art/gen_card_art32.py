from __future__ import annotations

import random
from pathlib import Path

import pygame

from game.art.gen_art32 import seed_from_id

GEN_CARD_ART_VERSION = "card_gen_v6"

TYPE_PALETTES = {
    "attack": ((24, 8, 20), (126, 24, 44), (236, 110, 40), (96, 26, 112)),
    "defense": ((10, 28, 36), (20, 98, 106), (56, 164, 126), (74, 40, 130)),
    "control": ((10, 24, 56), (24, 56, 140), (64, 98, 196), (78, 236, 246)),
    "ritual": ((18, 12, 28), (72, 44, 118), (162, 106, 214), (214, 186, 112)),
    "legendary": ((16, 10, 14), (92, 54, 28), (214, 158, 74), (236, 208, 136)),
    "spirit": ((10, 10, 16), (78, 56, 24), (184, 146, 56), (108, 64, 156)),
}

ARCHETYPE_PALETTE_HINTS = {
    "crimson-magenta": ((20, 8, 20), (122, 22, 58), (236, 104, 64), (182, 64, 176)),
    "teal-gold": ((8, 20, 24), (18, 84, 104), (138, 142, 74), (214, 182, 86)),
    "indigo-cyan": ((8, 16, 38), (34, 44, 126), (70, 116, 206), (86, 234, 236)),
    "violet-neutral": ((14, 10, 24), (74, 56, 124), (142, 102, 188), (210, 164, 236)),
    "marble-ice-gold": ((224, 232, 240), (186, 214, 236), (138, 166, 204), (214, 186, 112)),
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
        "ritual": "ritual",
        "legendary": "legendary",
    }
    return mapping.get(c, "spirit")


def _extract_field(prompt: str, key: str, stop_tokens: tuple[str, ...]) -> str:
    src = str(prompt or "")
    i = src.lower().find(key)
    if i < 0:
        return ""
    start = i + len(key)
    tail = src[start:]
    end = len(tail)
    for st in stop_tokens:
        j = tail.lower().find(st)
        if j >= 0:
            end = min(end, j)
    return tail[:end].strip(" ,:;.")


def _semantic_from_prompt(prompt: str) -> dict:
    p = str(prompt or "")
    pal = _extract_field(p, "palette ", ("lighting", "sacred geometry", "motif", "subject", "object", "environment", "effects", "effect signature", "energy pattern"))
    motif = _extract_field(p, "motif ", ("(", "subject", "object", "environment", "effects", "effect signature", "energy pattern", "lore tokens"))
    symbol = _extract_field(p, "sacred geometry ", ("motif", "subject", "object", "environment", "effects", "effect signature", "energy pattern"))
    subject = _extract_field(p, "subject ", ("object", "environment", "effects", "effect signature", "energy pattern", "lore tokens"))
    obj = _extract_field(p, "object ", ("environment", "effects", "effect signature", "energy pattern", "lore tokens"))
    environment = _extract_field(p, "environment ", ("effects", "effect signature", "energy pattern", "lore tokens"))
    effects = _extract_field(p, "effects ", ("energy pattern", "lore tokens"))
    energy = _extract_field(p, "energy pattern ", ("lore tokens",))
    lore_tokens = _extract_field(p, "lore tokens ", ())
    rarity = _extract_field(p, "rarity ", ("sacred geometry", "motif", "subject", "object", "environment", "effects", "effect signature", "energy pattern", "lore tokens"))
    role = _extract_field(p, "role ", ("palette", "lighting", "rarity", "sacred geometry"))
    return {
        "palette": pal.lower(),
        "motif": motif.lower(),
        "symbol": symbol.lower(),
        "subject": subject.lower(),
        "object": obj.lower(),
        "environment": environment.lower(),
        "effects_desc": effects.lower(),
        "energy": energy.lower(),
        "lore_tokens": lore_tokens.lower(),
        "rarity": rarity.lower(),
        "role": role.lower(),
    }


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

def _draw_scene_background(surface: pygame.Surface, semantic: dict, rng: random.Random, pal):
    w, h = surface.get_size()
    top, mid, low, acc = pal
    env = str(semantic.get("environment", "") or "")
    motif = str(semantic.get("motif", "") or "")

    horizon = int(h * 0.62)
    pygame.draw.rect(surface, (*low, 46), (0, horizon, w, h - horizon))

    if any(k in env for k in ("sea", "mar", "frozen sea")):
        for y in range(horizon, h, 3):
            pygame.draw.line(surface, (*acc, 34), (0, y), (w, y), 1)
    elif any(k in env for k in ("jungle", "forest", "selva")):
        for _ in range(12):
            x = rng.randint(0, w - 6)
            th = rng.randint(h // 8, h // 4)
            pygame.draw.rect(surface, (*low, 70), (x, horizon - th, 3, th))
            pygame.draw.circle(surface, (*mid, 54), (x + 2, horizon - th), rng.randint(4, 8))
    elif any(k in env for k in ("sky city", "temple", "sanctuary", "ruins", "architecture")) or any(k in motif for k in ("temple", "civilization", "polar")):
        for _ in range(6):
            bw = rng.randint(12, 26)
            bh = rng.randint(14, 34)
            bx = rng.randint(0, w - bw)
            by = horizon - bh - rng.randint(0, 10)
            pygame.draw.rect(surface, (*mid, 56), (bx, by, bw, bh), border_radius=2)
    else:
        points = []
        x = 0
        while x < w:
            points.append((x, horizon - rng.randint(6, 20)))
            x += rng.randint(10, 20)
        points.append((w, horizon))
        points.extend([(w, h), (0, h)])
        pygame.draw.polygon(surface, (*mid, 60), points)

    if any(k in env for k in ("gaia", "tree", "arbol")):
        trunk_x = w // 2
        pygame.draw.rect(surface, (*low, 110), (trunk_x - 3, horizon - 26, 6, 26))
        pygame.draw.circle(surface, (*mid, 78), (trunk_x, horizon - 34), 16)


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
        pygame.draw.line(surface, (*color, 35), (x, 0), (x + h, h), 1)
    for x in range(0, w, step * 2):
        for y in range(0, h, step * 2):
            pygame.draw.circle(surface, (*color, 78), (x + rng.randint(-1, 1), y + rng.randint(-1, 1)), 1)


def _draw_chakana_frame(surface: pygame.Surface, color):
    w, h = surface.get_size()
    r = pygame.Rect(10, 8, w - 20, h - 16)
    step = 8
    pts = [
        (r.left + step, r.top),
        (r.right - step, r.top),
        (r.right - step, r.top + step),
        (r.right, r.top + step),
        (r.right, r.bottom - step),
        (r.right - step, r.bottom - step),
        (r.right - step, r.bottom),
        (r.left + step, r.bottom),
        (r.left + step, r.bottom - step),
        (r.left, r.bottom - step),
        (r.left, r.top + step),
        (r.left + step, r.top + step),
    ]
    pygame.draw.lines(surface, (*color, 108), True, pts, 2)


def _draw_geometry(surface: pygame.Surface, variant: int, rng: random.Random, color):
    if variant == 0:
        _draw_rosette(surface, rng, color)
    elif variant == 1:
        _draw_concentric(surface, rng, color)
    elif variant == 2:
        _draw_grid_nodes(surface, rng, color)
    else:
        _draw_chakana_frame(surface, color)


def _draw_symbol_overlay(surface: pygame.Surface, symbol: str, color: tuple[int, int, int]):
    s = str(symbol or "")
    if not s:
        return
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    if "blade" in s:
        pygame.draw.line(surface, (*color, 122), (cx - 28, cy + 24), (cx + 26, cy - 22), 2)
    elif "shield" in s:
        pygame.draw.polygon(surface, (*color, 116), [(cx, cy - 24), (cx + 24, cy - 6), (cx + 16, cy + 26), (cx - 16, cy + 26), (cx - 24, cy - 6)], 2)
    elif "eye" in s:
        pygame.draw.ellipse(surface, (*color, 116), (cx - 30, cy - 14, 60, 28), 2)
        pygame.draw.circle(surface, (*color, 116), (cx, cy), 4)
    elif "seal" in s or "glyph" in s:
        pygame.draw.circle(surface, (*color, 102), (cx, cy), 22, 2)
        pygame.draw.line(surface, (*color, 102), (cx - 16, cy), (cx + 16, cy), 1)
        pygame.draw.line(surface, (*color, 102), (cx, cy - 16), (cx, cy + 16), 1)


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


def _draw_energy(surface: pygame.Surface, rng: random.Random, accent: tuple[int, int, int], energy_hint: str = ""):
    w, h = surface.get_size()
    fx = pygame.Surface((w, h), pygame.SRCALPHA)
    energy = str(energy_hint or "")
    lines = 7
    if "burst" in energy:
        lines = 9
    elif "stable" in energy:
        lines = 5
    elif "spiral" in energy:
        lines = 9

    for _ in range(lines):
        x1, y1 = rng.randint(8, w - 8), rng.randint(8, h - 8)
        x2, y2 = x1 + rng.randint(-20, 20), y1 + rng.randint(-20, 20)
        pygame.draw.line(fx, (*accent, 108), (x1, y1), (x2, y2), 1)
    surface.blit(fx, (0, 0))


def _draw_energy_glow(surface: pygame.Surface, accent: tuple[int, int, int], intensity: int = 1):
    w, h = surface.get_size()
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    base = min(w, h) // 3
    for i in range(1, 3 + max(0, intensity)):
        r = base + i * 8
        pygame.draw.circle(glow, (*accent, max(18, 62 - i * 10)), (cx, cy), r, 1)
    surface.blit(glow, (0, 0))


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
    if "ritual" in p or "seal" in p:
        return "ritual"
    if "legendary" in p:
        return "legendary"
    return "spirit"


def _motif_group(semantic: dict, ctype: str) -> str:
    motif = str(semantic.get("motif", "")).lower()
    symbol = str(semantic.get("symbol", "")).lower()
    energy = str(semantic.get("energy", "")).lower()
    if any(k in motif for k in ("weapon", "blade", "spear", "strike")):
        return "weapon"
    if any(k in motif for k in ("animal", "beast", "puma", "condor", "serpent")):
        return "animal"
    if any(k in motif for k in ("ritual", "sigil", "seal", "chakana")):
        return "ritual_symbol"
    if any(k in motif for k in ("cosmic", "star", "astral", "constellation", "aurora")):
        return "cosmic_structure"
    if any(k in motif for k in ("civilization", "temple", "hyperborea", "polar", "archon")):
        return "civilization_symbol"
    if "eye" in symbol:
        return "cosmic_structure"
    if "shield" in symbol:
        return "ritual_symbol"
    if "burst" in energy:
        return "weapon"
    if ctype == "attack":
        return "weapon"
    if ctype == "defense":
        return "ritual_symbol"
    if ctype in {"control", "ritual"}:
        return "cosmic_structure"
    return "civilization_symbol"


def _draw_motif_weapon(surface: pygame.Surface, color: tuple[int, int, int], rng: random.Random):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    tilt = rng.randint(-8, 8)
    pygame.draw.line(surface, (*color, 138), (cx - 34, cy + 26), (cx + 28, cy - 24), 2)
    pygame.draw.polygon(surface, (*color, 120), [(cx + 28, cy - 24), (cx + 18, cy - 12), (cx + 34 + tilt, cy - 10), (cx + 24, cy - 20)], 1)


def _draw_motif_animal(surface: pygame.Surface, color: tuple[int, int, int]):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    pygame.draw.polygon(surface, (*color, 128), [(cx - 16, cy + 16), (cx - 8, cy - 18), (cx + 8, cy - 18), (cx + 16, cy + 16)], 2)
    pygame.draw.circle(surface, (*color, 122), (cx - 6, cy - 4), 2)
    pygame.draw.circle(surface, (*color, 122), (cx + 6, cy - 4), 2)


def _draw_motif_ritual(surface: pygame.Surface, color: tuple[int, int, int]):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    pygame.draw.circle(surface, (*color, 120), (cx, cy), 26, 2)
    for d in (-16, 0, 16):
        pygame.draw.line(surface, (*color, 112), (cx - 20, cy + d), (cx + 20, cy + d), 1)


def _draw_motif_cosmic(surface: pygame.Surface, color: tuple[int, int, int], rng: random.Random):
    w, h = surface.get_size()
    stars = [(rng.randint(24, w - 24), rng.randint(20, h - 20)) for _ in range(6)]
    for a, b in zip(stars, stars[1:]):
        pygame.draw.line(surface, (*color, 98), a, b, 1)
    for s in stars:
        pygame.draw.circle(surface, (*color, 140), s, 1)


def _draw_motif_civilization(surface: pygame.Surface, color: tuple[int, int, int]):
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2
    pygame.draw.rect(surface, (*color, 112), (cx - 26, cy - 24, 52, 44), 2)
    pygame.draw.line(surface, (*color, 112), (cx - 20, cy - 12), (cx + 20, cy - 12), 1)
    pygame.draw.line(surface, (*color, 112), (cx - 16, cy), (cx + 16, cy), 1)


def _draw_motif_layer(surface: pygame.Surface, group: str, color: tuple[int, int, int], rng: random.Random):
    if group == "weapon":
        _draw_motif_weapon(surface, color, rng)
    elif group == "animal":
        _draw_motif_animal(surface, color)
    elif group == "ritual_symbol":
        _draw_motif_ritual(surface, color)
    elif group == "cosmic_structure":
        _draw_motif_cosmic(surface, color, rng)
    else:
        _draw_motif_civilization(surface, color)


def _glyph_for_theme(ctype: str, motif_group: str, seed: int) -> str:
    if ctype == "attack":
        return "sword"
    if ctype == "defense":
        return "shield"
    if ctype == "control":
        return "eye"
    if ctype == "ritual":
        return "orb"
    if ctype == "legendary":
        return "mask"
    if motif_group == "weapon":
        return "sword"
    if motif_group == "animal":
        return "mask"
    if motif_group == "cosmic_structure":
        return "eye"
    return ["orb", "portal", "mask"][seed % 3]


def _is_legendary(semantic: dict, ctype: str, card_id: str) -> bool:
    if ctype == "legendary":
        return True
    rarity = str(semantic.get("rarity", "")).lower()
    role = str(semantic.get("role", "")).lower()
    cid = str(card_id).lower()
    return "legendary" in rarity or "legendary" in role or "legendary" in cid


def _palette_from_semantic(default_pal, semantic: dict):
    key = str(semantic.get("palette", "")).strip().lower()
    return ARCHETYPE_PALETTE_HINTS.get(key, default_pal)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    tt = max(0.0, min(1.0, float(t)))
    return (
        int(a[0] * (1.0 - tt) + b[0] * tt),
        int(a[1] * (1.0 - tt) + b[1] * tt),
        int(a[2] * (1.0 - tt) + b[2] * tt),
    )



def _soften_color(color: tuple[int, int, int], amount: float = 0.88) -> tuple[int, int, int]:
    a = max(0.0, min(1.0, float(amount)))
    return (
        max(0, min(255, int(color[0] * a))),
        max(0, min(255, int(color[1] * a))),
        max(0, min(255, int(color[2] * a))),
    )
def _background_palette_from_semantic(pal, semantic: dict):
    lore = str(semantic.get("lore_tokens", "")).lower()
    motif = str(semantic.get("motif", "")).lower()

    # Biome/civilization flavored background while preserving card type identity.
    if any(k in lore for k in ("ukhu", "underworld", "void", "fractura")) or any(k in motif for k in ("void", "demon", "rupture")):
        tint = (58, 18, 36)
    elif any(k in lore for k in ("hanan", "celestial", "upper world")):
        tint = (160, 170, 214)
    elif any(k in lore for k in ("kay", "living world", "ritual balance")):
        tint = (74, 114, 126)
    elif any(k in lore for k in ("hyperborea", "hiperboria", "polar", "ice")):
        tint = (184, 212, 232)
    else:
        tint = None

    if tint is None:
        return pal
    top, mid, low, acc = pal
    return (
        _mix(top, tint, 0.18),
        _mix(mid, tint, 0.14),
        _mix(low, tint, 0.12),
        _mix(acc, tint, 0.08),
    )


def _boost_legendary_saturation(surface: pygame.Surface):
    w, h = surface.get_size()
    sat = pygame.Surface((w, h), pygame.SRCALPHA)
    sat.fill((26, 18, 8, 34))
    surface.blit(sat, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def generate(card_id: str, card_type: str, prompt: str, seed: int, out_path: Path) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ctype = _family_to_type(card_type)
    hint = _prompt_hint(prompt)
    if hint != "spirit":
        ctype = hint

    semantic = _semantic_from_prompt(prompt)
    pal = _palette_from_semantic(TYPE_PALETTES.get(ctype, TYPE_PALETTES["spirit"]), semantic)
    pal = _background_palette_from_semantic(pal, semantic)

    last_hash = None
    chosen_variant = 0
    sem_hash = seed_from_id(f"{card_id}:{semantic.get('motif','')}:{semantic.get('symbol','')}:{semantic.get('energy','')}", GEN_CARD_ART_VERSION)
    motif_group = _motif_group(semantic, ctype)
    legendary = _is_legendary(semantic, ctype, card_id)
    if legendary and ctype != "legendary":
        ctype = "legendary"
        pal = _palette_from_semantic(TYPE_PALETTES["legendary"], semantic)

    for attempt in range(5):
        rng = random.Random(seed + sem_hash + attempt * 313)
        low = pygame.Surface((160, 112), pygame.SRCALPHA, 32)

        # Layer 1: background
        _draw_gradient(low, pal)
        _add_dither(low, rng)
        _draw_scene_background(low, semantic, rng, pal)

        # Layer 2: geometry
        variant_pool = [0, 1, 2, 3]
        motif = str(semantic.get("motif", ""))
        if "cosmic" in motif:
            variant_pool = [2, 1, 3, 0]
        elif "ritual" in motif or "chakana" in motif:
            variant_pool = [3, 0, 1, 2]
        elif "demons" in motif:
            variant_pool = [1, 2, 0, 3]
        elif "crystals" in motif:
            variant_pool = [2, 3, 1, 0]
        elif "auroras" in motif:
            variant_pool = [1, 2, 3, 0]
        elif "polar_temple" in motif or "polar_temples" in motif:
            variant_pool = [3, 2, 0, 1]
        elif "ancient_guardian" in motif or "ancient_guardians" in motif:
            variant_pool = [0, 3, 1, 2]

        # Diversify geometry order by semantic hash to avoid repeated pattern cadence.
        rot = (sem_hash + attempt) % len(variant_pool)
        variant_pool = variant_pool[rot:] + variant_pool[:rot]
        chosen_variant = variant_pool[(seed + attempt + sem_hash) % len(variant_pool)]
        _draw_geometry(low, chosen_variant, rng, _soften_color(pal[3], 0.78))
        if any(k in motif for k in ("ritual", "chakana", "seal", "sigil")):
            _draw_geometry(low, 3, rng, _soften_color(_mix(pal[2], pal[3], 0.5), 0.72))

        # Layer 3: symbol
        _draw_silhouette(low, ctype, pal[2])
        _draw_glyph(low, _glyph_for_theme(ctype, motif_group, seed + sem_hash + attempt), pal[2])
        if any(k in motif for k in ("ritual", "chakana", "seal", "sigil")):
            _draw_symbol_overlay(low, semantic.get("symbol", ""), _soften_color(pal[3], 0.76))

        # Layer 4: motif
        _draw_motif_layer(low, motif_group, pal[2], rng)

        # Layer 5: energy FX
        _draw_energy(low, rng, pal[3], semantic.get("energy", ""))
        if legendary:
            _draw_energy_glow(low, pal[3], intensity=2)
            _draw_geometry(low, (chosen_variant + 1) % 4, rng, _soften_color(pal[3], 0.9))
            _draw_motif_layer(low, motif_group, _mix(pal[2], pal[3], 0.6), rng)
            _boost_legendary_saturation(low)
            pygame.draw.circle(low, (*pal[3], 96), (80, 56), 34, 2)

        for c in [(6, 6), (154, 6), (6, 106), (154, 106)]:
            pygame.draw.circle(low, pal[3], c, 4, 1)
        vign = pygame.Surface((160, 112), pygame.SRCALPHA)
        pygame.draw.rect(vign, (0, 0, 0, 96), vign.get_rect(), width=10)
        low.blit(vign, (0, 0))

        h = _hash16(low)
        if last_hash is None or abs(h - last_hash) > 100:
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
    _draw_geometry(low, seed % 4, rng, _soften_color(pal[3], 0.88))
    _draw_silhouette(low, ctype, pal[2])
    motif_group = _motif_group({"motif": family, "symbol": symbol, "energy": "arc_traces"}, ctype)
    _draw_motif_layer(low, motif_group, pal[2], rng)
    _draw_glyph(low, _glyph_for_theme(ctype, motif_group, seed), pal[2])
    _draw_symbol_overlay(low, symbol, _soften_color(pal[3], 0.9))
    _draw_energy(low, rng, pal[3], "arc_traces")
    if ctype == "legendary":
        _draw_energy_glow(low, pal[3], intensity=2)

    return pygame.transform.scale(low, (320, 220)).convert_alpha()





