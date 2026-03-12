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


def draw_fx(surface: pygame.Surface, semantic: dict, palette, rng: random.Random, keepout: pygame.Rect | None = None):
    rule = resolve_fx_rule(semantic)
    color = _pick_color(rule, palette)
    w, h = surface.get_size()
    keepout = keepout or pygame.Rect(int(w * 0.24), int(h * 0.18), int(w * 0.52), int(h * 0.54))
    ring_rect = pygame.Rect(int(w * 0.12), int(h * 0.08), int(w * 0.76), int(h * 0.76))

    family = rule.family
    if family == 'aura_glow':
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*color, rule.alpha_min), (int(w * 0.18), int(h * 0.12), int(w * 0.64), int(h * 0.62)), 4)
        pygame.draw.ellipse(glow, (*color, max(rule.alpha_min - 18, 32)), (int(w * 0.22), int(h * 0.18), int(w * 0.56), int(h * 0.50)), 2)
        surface.blit(glow, (0, 0))
    elif family == 'sacred_wind':
        for _ in range(rule.particle_count):
            side = rng.choice(['left', 'right'])
            x1 = rng.randint(int(w * 0.04), int(w * 0.18)) if side == 'left' else rng.randint(int(w * 0.82), int(w * 0.96))
            y1 = rng.randint(int(h * 0.20), int(h * 0.74))
            x2 = x1 + rng.randint(14, 28) * (1 if side == 'left' else -1)
            y2 = y1 + rng.randint(-8, 8)
            pygame.draw.arc(surface, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (min(x1, x2), min(y1, y2), abs(x2 - x1) + 18, 16), 0.2, 2.8, 2)
    elif family == 'rune_particles':
        corners = [
            pygame.Rect(0, 0, int(w * 0.28), int(h * 0.28)),
            pygame.Rect(int(w * 0.72), 0, int(w * 0.28), int(h * 0.28)),
            pygame.Rect(0, int(h * 0.72), int(w * 0.28), int(h * 0.28)),
            pygame.Rect(int(w * 0.72), int(h * 0.72), int(w * 0.28), int(h * 0.28)),
        ]
        for _ in range(rule.particle_count):
            rect = rng.choice(corners)
            x, y = _rand_point(rng, rect)
            s = rng.randint(2, 4)
            pygame.draw.rect(surface, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (x, y, s, s), border_radius=1)
    elif family == 'corruption_smoke':
        smoke = pygame.Surface((w, h), pygame.SRCALPHA)
        zones = [
            pygame.Rect(int(w * 0.06), int(h * 0.18), int(w * 0.20), int(h * 0.46)),
            pygame.Rect(int(w * 0.74), int(h * 0.18), int(w * 0.20), int(h * 0.46)),
        ]
        for _ in range(rule.particle_count):
            rect = rng.choice(zones)
            cx, cy = _rand_point(rng, rect)
            rw = rng.randint(int(w * 0.08), int(w * 0.14))
            rh = rng.randint(int(h * 0.06), int(h * 0.12))
            pygame.draw.ellipse(smoke, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (cx, cy, rw, rh))
        surface.blit(smoke, (0, 0))
    elif family == 'solar_light':
        light = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(light, (*color, rule.alpha_min), [
            (int(w * 0.16), int(h * 0.02)),
            (int(w * 0.40), int(h * 0.02)),
            (int(w * 0.30), int(h * 0.28)),
            (int(w * 0.08), int(h * 0.30)),
        ])
        for _ in range(max(3, rule.particle_count - 2)):
            px = rng.randint(int(w * 0.10), int(w * 0.40))
            py = rng.randint(int(h * 0.06), int(h * 0.32))
            pygame.draw.circle(light, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (px, py), rng.randint(1, 2))
        surface.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    elif family == 'void_sparks':
        zones = [
            pygame.Rect(0, 0, int(w * 0.22), h),
            pygame.Rect(int(w * 0.78), 0, int(w * 0.22), h),
        ]
        for _ in range(rule.particle_count):
            rect = rng.choice(zones)
            x, y = _rand_point(rng, rect)
            pygame.draw.line(surface, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (x, y), (x + rng.randint(-5, 5), y + rng.randint(-8, 8)), 2)
            pygame.draw.circle(surface, (*color, rng.randint(max(136, rule.alpha_min), max(164, rule.alpha_max))), (x, y), 1)

    # Small universal spark pass constrained outside the subject core.
    for _ in range(max(3, rule.particle_count // 2)):
        px = rng.randint(0, w - 1)
        py = rng.randint(0, h - 1)
        if not _outside_keepout((px, py), keepout):
            continue
        pygame.draw.circle(surface, (*color, rng.randint(max(144, rule.alpha_min), max(176, rule.alpha_max))), (px, py), 1)
