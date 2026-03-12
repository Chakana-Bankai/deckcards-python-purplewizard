from __future__ import annotations

import pygame


FRAME_TIERS = ("common", "rare", "epic", "legendary")


def normalize_frame_rarity(rarity: str) -> str:
    key = str(rarity or "common").strip().lower()
    if key in {"epic", "ritual"}:
        return "epic"
    if key in {"legendary", "legend", "mythic"}:
        return "legendary"
    if key in {"rare", "uncommon"}:
        return "rare"
    return "common"


def _frame_palette(tier: str, accent: tuple[int, int, int] | None = None) -> dict[str, tuple[int, int, int]]:
    palettes = {
        "common": {
            "plate": (26, 22, 32),
            "line": (170, 148, 110),
            "glow": (214, 196, 156),
            "aura": (72, 64, 54),
        },
        "rare": {
            "plate": (20, 22, 36),
            "line": (132, 176, 236),
            "glow": (186, 216, 250),
            "aura": (84, 118, 162),
        },
        "epic": {
            "plate": (24, 18, 38),
            "line": (194, 138, 244),
            "glow": (226, 188, 255),
            "aura": (116, 84, 160),
        },
        "legendary": {
            "plate": (30, 24, 18),
            "line": (244, 202, 112),
            "glow": (255, 230, 168),
            "aura": (176, 128, 64),
        },
    }
    palette = dict(palettes.get(tier, palettes["common"]))
    if accent is not None:
        palette["line"] = tuple(
            max(0, min(255, int((base * 0.55) + (acc * 0.45))))
            for base, acc in zip(palette["line"], accent)
        )
    return palette


def apply_frame_overlay(
    target: pygame.Surface,
    rect: pygame.Rect,
    rarity: str,
    *,
    accent: tuple[int, int, int] | None = None,
    set_is_hiperboria: bool = False,
) -> None:
    tier = normalize_frame_rarity(rarity)
    pal = _frame_palette(tier, accent)

    aura = pygame.Surface((rect.w + 28, rect.h + 28), pygame.SRCALPHA)
    aura_alpha = {
        "common": 22,
        "rare": 54,
        "epic": 62,
        "legendary": 74,
    }[tier]
    pygame.draw.rect(aura, (*pal["aura"], aura_alpha), aura.get_rect(), border_radius=18)
    target.blit(aura, (rect.x - 14, rect.y - 14))

    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(plate, (*pal["plate"], 148), plate.get_rect(), border_radius=10)
    pygame.draw.rect(plate, (*pal["line"], 230), plate.get_rect(), 2, border_radius=10)
    pygame.draw.rect(plate, (*pal["glow"], 90), plate.get_rect().inflate(-8, -8), 1, border_radius=8)
    target.blit(plate, rect.topleft)

    corners = (
        (rect.left + 10, rect.top + 10),
        (rect.right - 10, rect.top + 10),
        (rect.left + 10, rect.bottom - 10),
        (rect.right - 10, rect.bottom - 10),
    )
    for cx, cy in corners:
        pygame.draw.circle(target, (*pal["glow"], 210), (cx, cy), 3)

    if tier in {"epic", "legendary"}:
        edge = rect.inflate(8, 8)
        pygame.draw.rect(target, (*pal["glow"], 96), edge, 1, border_radius=12)

    if tier == "legendary":
        halo = rect.inflate(16, 16)
        pygame.draw.rect(target, (*pal["glow"], 62), halo, 1, border_radius=14)

    if set_is_hiperboria:
        frost = rect.inflate(10, 10)
        pygame.draw.rect(target, (198, 224, 244, 76), frost, 1, border_radius=13)
