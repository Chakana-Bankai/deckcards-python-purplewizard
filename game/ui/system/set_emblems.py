from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class SetEmblemProfile:
    expansion_id: str
    expansion_emblem: str
    expansion_palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    expansion_symbolic_theme: str


SET_EMBLEM_REGISTRY: dict[str, SetEmblemProfile] = {
    "base": SetEmblemProfile(
        expansion_id="BASE",
        expansion_emblem="chakana_origin",
        expansion_palette=((198, 178, 132), (146, 126, 96), (38, 30, 24)),
        expansion_symbolic_theme="fundacional_origen_chakana",
    ),
    "hiperborea": SetEmblemProfile(
        expansion_id="HIPERBOREA",
        expansion_emblem="chakana_polar",
        expansion_palette=((226, 206, 140), (178, 220, 244), (36, 46, 62)),
        expansion_symbolic_theme="polar_ancestral_aurora",
    ),
    "archon_war": SetEmblemProfile(
        expansion_id="ARCHON_WAR",
        expansion_emblem="archon_crown",
        expansion_palette=((222, 106, 106), (118, 42, 74), (32, 18, 28)),
        expansion_symbolic_theme="corrupcion_arconte_guerra_cosmica",
    ),
    "solar_awakening": SetEmblemProfile(
        expansion_id="SOLAR_AWAKENING",
        expansion_emblem="solar_chakana",
        expansion_palette=((238, 210, 124), (214, 146, 86), (40, 26, 18)),
        expansion_symbolic_theme="despertar_solar_ritual",
    ),
}


def normalize_set_id(card_like: dict | None) -> str:
    card_like = card_like or {}
    sid = str(card_like.get("set", "") or "").strip().lower()
    cid = str(card_like.get("id", "") or "").strip().lower()
    raw_emblem = str(card_like.get("set_emblem", "") or "").strip().lower()
    if "hiperborea" in sid or "hiperborea" in raw_emblem or raw_emblem == "chakana_polar" or cid.startswith("hip_"):
        return "hiperborea"
    if "archon" in sid or "archon" in raw_emblem:
        return "archon_war"
    if "solar" in sid or "solar" in raw_emblem:
        return "solar_awakening"
    return "base"


def get_set_profile(set_id: str) -> SetEmblemProfile:
    key = str(set_id or "base").strip().lower()
    return SET_EMBLEM_REGISTRY.get(key, SET_EMBLEM_REGISTRY["base"])


def _draw_base_emblem(surface: pygame.Surface, center: tuple[int, int], radius: int, col_main, col_accent):
    cx, cy = center
    pygame.draw.circle(surface, col_main, center, radius, 1)
    pygame.draw.line(surface, col_main, (cx - radius + 2, cy), (cx + radius - 2, cy), 1)
    pygame.draw.line(surface, col_main, (cx, cy - radius + 2), (cx, cy + radius - 2), 1)
    pygame.draw.circle(surface, col_accent, center, max(1, radius // 3), 1)


def _draw_hiperborea_emblem(surface: pygame.Surface, center: tuple[int, int], radius: int, col_main, col_accent):
    cx, cy = center
    pygame.draw.circle(surface, col_accent, center, radius, 1)
    pygame.draw.circle(surface, col_main, center, max(2, radius - 2), 1)
    pygame.draw.line(surface, col_main, (cx - radius + 2, cy), (cx + radius - 2, cy), 1)
    pygame.draw.line(surface, col_main, (cx, cy - radius + 2), (cx, cy + radius - 2), 1)
    pygame.draw.line(surface, col_accent, (cx - radius + 4, cy - radius + 4), (cx + radius - 4, cy + radius - 4), 1)
    pygame.draw.line(surface, col_accent, (cx + radius - 4, cy - radius + 4), (cx - radius + 4, cy + radius - 4), 1)


def _draw_archon_emblem(surface: pygame.Surface, center: tuple[int, int], radius: int, col_main, col_accent):
    cx, cy = center
    pts = [(cx, cy - radius), (cx + radius - 2, cy), (cx, cy + radius), (cx - radius + 2, cy)]
    pygame.draw.polygon(surface, col_main, pts, 1)
    pygame.draw.circle(surface, col_accent, center, max(1, radius // 3), 1)
    pygame.draw.line(surface, col_main, (cx - radius + 3, cy + radius - 3), (cx + radius - 3, cy - radius + 3), 1)


def _draw_solar_emblem(surface: pygame.Surface, center: tuple[int, int], radius: int, col_main, col_accent):
    cx, cy = center
    pygame.draw.circle(surface, col_main, center, max(1, radius - 1), 1)
    pygame.draw.circle(surface, col_accent, center, max(1, radius // 3), 1)
    for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
        pygame.draw.line(surface, col_main, center, (cx + dx, cy + dy), 1)


def draw_set_emblem(surface: pygame.Surface, rect: pygame.Rect, set_id: str):
    profile = get_set_profile(set_id)
    base_col, accent_col, bg_col = profile.expansion_palette
    pygame.draw.rect(surface, bg_col, rect, border_radius=6)
    pygame.draw.rect(surface, accent_col, rect, 1, border_radius=6)

    radius = max(4, min(rect.w, rect.h) // 2 - 3)
    center = rect.center
    emblem = profile.expansion_emblem
    if emblem == "chakana_polar":
        _draw_hiperborea_emblem(surface, center, radius, base_col, accent_col)
    elif emblem == "archon_crown":
        _draw_archon_emblem(surface, center, radius, base_col, accent_col)
    elif emblem == "solar_chakana":
        _draw_solar_emblem(surface, center, radius, base_col, accent_col)
    else:
        _draw_base_emblem(surface, center, radius, base_col, accent_col)
