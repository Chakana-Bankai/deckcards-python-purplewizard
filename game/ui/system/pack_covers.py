from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

from game.core.paths import curated_assets_dir
from game.ui.theme import UI_THEME


def pack_cover_dir() -> Path:
    return curated_assets_dir() / "ui" / "packs"


def pack_cover_path(pack_id: str) -> Path:
    key = str(pack_id or "base_pack").strip().lower()
    return pack_cover_dir() / f"{key}.png"


def _pack_palette(pack_id: str):
    pid = str(pack_id or "").lower().strip()
    if pid == "hiperborea_pack":
        return {"bg": (22, 42, 62), "mid": (84, 142, 186), "accent": (168, 230, 244), "ink": (232, 248, 255)}
    if pid == "mystery_pack":
        return {"bg": (36, 18, 52), "mid": (110, 64, 152), "accent": (214, 148, 244), "ink": (248, 236, 255)}
    return {"bg": (34, 24, 56), "mid": (122, 84, 158), "accent": (236, 208, 118), "ink": (248, 240, 220)}


@lru_cache(maxsize=24)
def _load_cover_cached(path_str: str):
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        img = pygame.image.load(str(path))
        try:
            return img.convert_alpha()
        except Exception:
            return img
    except Exception:
        return None


def _fit_contained(image: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    iw, ih = image.get_size()
    tw, th = size
    if iw <= 0 or ih <= 0 or tw <= 0 or th <= 0:
        return pygame.Surface((max(1, tw), max(1, th)), pygame.SRCALPHA)
    scale = min(tw / float(iw), th / float(ih))
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    return pygame.transform.smoothscale(image, (nw, nh))


def draw_pack_cover(surface: pygame.Surface, rect: pygame.Rect, app, pack_id: str, title: str, *, selected: bool = False, hovered: bool = False, price_text: str = ""):
    pal = _pack_palette(pack_id)
    glow = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
    if selected or hovered:
        pygame.draw.rect(glow, (*pal["accent"], 54), glow.get_rect(), border_radius=30)
        surface.blit(glow, (rect.x - 12, rect.y - 12))

    cover = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(cover, pal["bg"], cover.get_rect(), border_radius=22)
    for i in range(rect.h):
        fade = min(168, 28 + i // 4)
        color = (
            min(255, pal["mid"][0] + i // 16),
            min(255, pal["mid"][1] + i // 20),
            min(255, pal["mid"][2] + i // 22),
            fade,
        )
        pygame.draw.line(cover, color, (0, i), (rect.w, i))
    surface.blit(cover, rect.topleft)
    pygame.draw.rect(surface, pal["accent"] if selected else UI_THEME["gold"], rect, 4 if selected else 2, border_radius=22)

    art_rect = rect.inflate(-34, -118)
    img = _load_cover_cached(str(pack_cover_path(pack_id)))
    if img is not None:
        fitted = _fit_contained(img, (art_rect.w, art_rect.h))
        surface.blit(fitted, fitted.get_rect(center=art_rect.center))
    else:
        center = art_rect.center
        pygame.draw.circle(surface, pal["accent"], center, min(art_rect.w, art_rect.h) // 3, 2)
        pygame.draw.circle(surface, pal["mid"], center, min(art_rect.w, art_rect.h) // 5)
        pygame.draw.line(surface, pal["ink"], (center[0], art_rect.y + 16), (center[0], art_rect.bottom - 16), 2)
        pygame.draw.line(surface, pal["ink"], (art_rect.x + 16, center[1]), (art_rect.right - 16, center[1]), 2)
        pygame.draw.line(surface, pal["ink"], (art_rect.x + 34, art_rect.y + 34), (art_rect.right - 34, art_rect.bottom - 34), 2)
        pygame.draw.line(surface, pal["ink"], (art_rect.right - 34, art_rect.y + 34), (art_rect.x + 34, art_rect.bottom - 34), 2)
        for radius in (36, 70, 102):
            pygame.draw.circle(surface, pal["accent"], center, radius, 1)

    title_band = pygame.Rect(rect.x + 18, rect.bottom - 84, rect.w - 36, 54)
    pygame.draw.rect(surface, (10, 10, 18), title_band, border_radius=12)
    pygame.draw.rect(surface, pal["accent"], title_band, 1, border_radius=12)
    name = app.small_font.render(title, True, pal["ink"])
    surface.blit(name, name.get_rect(center=(title_band.centerx, title_band.y + 18)))
    if price_text:
        price = app.tiny_font.render(price_text, True, pal["accent"])
        surface.blit(price, price.get_rect(center=(title_band.centerx, title_band.y + 38)))
    if selected:
        marker = app.tiny_font.render("Pulso elegido", True, UI_THEME["gold"])
        surface.blit(marker, marker.get_rect(center=(rect.centerx, rect.y + 18)))
