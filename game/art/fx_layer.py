from __future__ import annotations

import random
import pygame

from game.art.fx_rules import resolve_fx_rule


def _pick_color(rule, palette):
    top, mid, low, acc = palette
    if rule.palette_bias == 'archon':
        return acc
    if rule.palette_bias == 'hyperborea':
        return (min(255, acc[0]), min(255, acc[1]), min(255, acc[2]))
    return acc


def _outside_keepout(pt, keepout: pygame.Rect) -> bool:
    return not keepout.collidepoint(pt)


def _rand_point(rng: random.Random, rect: pygame.Rect):
    return (rng.randint(rect.left, rect.right), rng.randint(rect.top, rect.bottom))


def _clamp_alpha(rule_alpha: int, scale: float = 1.0, hard_cap: int = 32) -> int:
    return max(6, min(hard_cap, int(rule_alpha * scale)))


def draw_fx(
    surface: pygame.Surface,
    semantic: dict,
    palette,
    rng: random.Random,
    keepout: pygame.Rect | None = None,
    fx_sector: pygame.Rect | None = None,
    spawn_anchor: tuple[int, int] | None = None,
):
    rule = resolve_fx_rule(semantic)
    color = _pick_color(rule, palette)
    w, h = surface.get_size()
    keepout = (keepout or pygame.Rect(int(w * 0.34), int(h * 0.20), int(w * 0.32), int(h * 0.42))).clip(surface.get_rect())
    fx_sector = (fx_sector or pygame.Rect(int(w * 0.18), int(h * 0.10), int(w * 0.64), int(h * 0.66))).clip(surface.get_rect())
    anchor = spawn_anchor or fx_sector.center

    family = rule.family
    soft_min = _clamp_alpha(rule.alpha_min, 0.28, 24)
    soft_max = _clamp_alpha(rule.alpha_max, 0.26, 30)
    rim_alpha = min(12, soft_max)

    if family == 'aura_glow':
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        halo = pygame.Rect(0, 0, int(fx_sector.width * 0.34), int(fx_sector.height * 0.34))
        halo.center = anchor
        halo.clamp_ip(fx_sector)
        pygame.draw.ellipse(glow, (*color, rim_alpha), halo, max(1, w // 220))
        pygame.draw.ellipse(glow, (*color, max(8, rim_alpha - 6)), halo.inflate(-max(6, halo.width // 8), -max(6, halo.height // 8)), 1)
        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    elif family == 'sacred_wind':
        for _ in range(max(3, rule.particle_count // 2)):
            x1 = rng.randint(fx_sector.left, fx_sector.right)
            y1 = rng.randint(fx_sector.top, fx_sector.bottom)
            if not _outside_keepout((x1, y1), keepout):
                continue
            x2 = x1 + rng.randint(-18, 18)
            y2 = y1 + rng.randint(-8, 8)
            pygame.draw.arc(surface, (*color, rng.randint(soft_min, soft_max)), (min(x1, x2), min(y1, y2), abs(x2 - x1) + 10, 10), 0.2, 2.8, 1)
    elif family == 'rune_particles':
        corners = [
            pygame.Rect(fx_sector.left, fx_sector.top, fx_sector.width // 3, fx_sector.height // 3),
            pygame.Rect(fx_sector.right - fx_sector.width // 3, fx_sector.top, fx_sector.width // 3, fx_sector.height // 3),
        ]
        for _ in range(max(4, rule.particle_count // 2)):
            rect = rng.choice(corners)
            x, y = _rand_point(rng, rect)
            if not _outside_keepout((x, y), keepout):
                continue
            s = rng.randint(1, 3)
            pygame.draw.rect(surface, (*color, rng.randint(soft_min, soft_max)), (x, y, s, s), border_radius=1)
    elif family == 'corruption_smoke':
        smoke = pygame.Surface((w, h), pygame.SRCALPHA)
        zones = [
            pygame.Rect(fx_sector.left, fx_sector.top + fx_sector.height // 6, fx_sector.width // 4, fx_sector.height // 2),
            pygame.Rect(fx_sector.right - fx_sector.width // 4, fx_sector.top + fx_sector.height // 6, fx_sector.width // 4, fx_sector.height // 2),
        ]
        for _ in range(max(3, rule.particle_count // 2)):
            rect = rng.choice(zones)
            cx, cy = _rand_point(rng, rect)
            if not _outside_keepout((cx, cy), keepout):
                continue
            rw = rng.randint(max(8, w // 20), max(12, w // 12))
            rh = rng.randint(max(6, h // 18), max(10, h // 10))
            pygame.draw.ellipse(smoke, (*color, rng.randint(soft_min, soft_max)), (cx, cy, rw, rh))
        surface.blit(smoke, (0, 0))
    elif family == 'solar_light':
        light = pygame.Surface((w, h), pygame.SRCALPHA)
        beam = [
            (max(0, anchor[0] - fx_sector.width // 6), fx_sector.top),
            (min(w, anchor[0] + fx_sector.width // 9), fx_sector.top),
            (anchor[0] + fx_sector.width // 14, min(h, keepout.top - 2)),
            (anchor[0] - fx_sector.width // 10, min(h, keepout.top + 6)),
        ]
        pygame.draw.polygon(light, (*color, max(8, soft_min - 2)), beam)
        surface.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    elif family == 'void_sparks':
        side_zones = [
            pygame.Rect(fx_sector.left, fx_sector.top, fx_sector.width // 4, fx_sector.height),
            pygame.Rect(fx_sector.right - fx_sector.width // 4, fx_sector.top, fx_sector.width // 4, fx_sector.height),
        ]
        for _ in range(max(4, rule.particle_count // 2)):
            rect = rng.choice(side_zones)
            x, y = _rand_point(rng, rect)
            if not _outside_keepout((x, y), keepout):
                continue
            pygame.draw.line(surface, (*color, rng.randint(soft_min, soft_max)), (x, y), (x + rng.randint(-3, 3), y + rng.randint(-5, 5)), 1)

    for _ in range(max(2, rule.particle_count // 3)):
        px = rng.randint(fx_sector.left, fx_sector.right)
        py = rng.randint(fx_sector.top, fx_sector.bottom)
        if not _outside_keepout((px, py), keepout):
            continue
        pygame.draw.circle(surface, (*color, rng.randint(soft_min, soft_max)), (px, py), 1)
