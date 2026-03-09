from __future__ import annotations

import argparse
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / "game" / "assets" / "curated" / "avatars"

SRC_CANDIDATES = [
    CURATED / "chakana_mage_codec_reference.png",
    CURATED / "chakana_mage_reference.png",
    CURATED / "chakana_mage_radio_portrait.png",
]

OUT_CONCEPT = CURATED / "chakana_mage_master_concept.png"
OUT_PORTRAIT = CURATED / "chakana_mage_master_portrait.png"
OUT_HOLO = CURATED / "chakana_mage_master_hologram.png"


def _fit(src: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    w, h = size
    sw, sh = src.get_size()
    sc = min(w / max(1, sw), h / max(1, sh))
    tw, th = max(1, int(sw * sc)), max(1, int(sh * sc))
    img = pygame.transform.smoothscale(src, (tw, th))
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(img, (w // 2 - tw // 2, h // 2 - th // 2))
    return out


def _crop_focus_face(src: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    """Face/hood-focused square portrait for gameplay UI (512x512)."""
    sw, sh = src.get_size()
    side = min(sw, sh)
    # Bias to upper-center to avoid full body and keep face/hood dominant.
    cx = sw // 2
    cy = int(sh * 0.38)
    x = max(0, min(sw - side, cx - side // 2))
    y = max(0, min(sh - side, cy - side // 2))
    crop = pygame.Surface((side, side), pygame.SRCALPHA)
    crop.blit(src, (0, 0), area=pygame.Rect(x, y, side, side))
    return pygame.transform.smoothscale(crop, size)


def _draw_chakana_symbol(surf: pygame.Surface, center: tuple[int, int], size: int) -> None:
    cx, cy = center
    gold = (224, 188, 108)
    step = max(2, size // 5)
    for i in range(-2, 3):
        for j in range(-2, 3):
            if abs(i) == 2 or abs(j) == 2 or i == 0 or j == 0:
                r = pygame.Rect(cx + i * step - step // 2, cy + j * step - step // 2, step, step)
                pygame.draw.rect(surf, (*gold, 210), r, 1)


def _portraitize(src: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    out = _crop_focus_face(src, size)

    # Slight cinematic shade for depth.
    shade = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(size[1]):
        a = int(26 + 22 * (y / max(1, size[1] - 1)))
        pygame.draw.line(shade, (38, 20, 70, a), (0, y), (size[0], y), 1)
    out.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Subtle chest-area Chakana accent to keep identity.
    _draw_chakana_symbol(out, (size[0] // 2 + size[0] // 6, int(size[1] * 0.78)), max(14, size[0] // 18))

    pygame.draw.rect(out, (208, 180, 118), out.get_rect(), 2, border_radius=8)
    return out


def _hologramize(src: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    base = _portraitize(src, size)

    # Reduce white overlay; use cyan/violet transparent energy instead.
    tint = pygame.Surface(size, pygame.SRCALPHA)
    tint.fill((86, 164, 255, 42))
    base.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    violet = pygame.Surface(size, pygame.SRCALPHA)
    violet.fill((124, 82, 228, 26))
    base.blit(violet, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Scanline.
    for y in range(1, size[1], 3):
        pygame.draw.line(base, (102, 214, 246, 26), (2, y), (size[0] - 2, y), 1)

    # Soft glow.
    glow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (102, 214, 246, 32), (size[0] // 8, size[1] // 10, size[0] * 3 // 4, size[1] * 3 // 4))
    base.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Controlled RGB split (small offsets only).
    r = base.copy()
    b = base.copy()
    r.fill((255, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    b.fill((0, 0, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
    base.blit(r, (1, 0), special_flags=pygame.BLEND_RGBA_ADD)
    base.blit(b, (-1, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # Transparent energy wisps.
    energy = pygame.Surface(size, pygame.SRCALPHA)
    for i in range(12):
        x = (i * 37) % max(1, size[0] - 12)
        y = (i * 29) % max(1, size[1] - 10)
        pygame.draw.arc(energy, (120, 232, 255, 44), pygame.Rect(x, y, 24, 12), 0.1, 2.8, 1)
    base.blit(energy, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    pygame.draw.rect(base, (122, 236, 255, 160), base.get_rect(), 1, border_radius=8)
    return base


def _resolve_source(source_arg: str | None) -> Path | None:
    if source_arg:
        p = Path(source_arg).expanduser().resolve()
        if p.exists() and p.is_file():
            return p
        print(f"[avatar_master] source_arg_not_found={p}")
        return None
    return next((p for p in SRC_CANDIDATES if p.exists()), None)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Chakana master avatar pipeline from a reference image")
    parser.add_argument("--source", type=str, default=None, help="Absolute or relative path to reference image (.png/.jpg)")
    return parser


def main() -> int:
    args = _parser().parse_args()
    CURATED.mkdir(parents=True, exist_ok=True)
    src_path = _resolve_source(args.source)
    if src_path is None:
        print("[avatar_master] source_missing")
        for p in SRC_CANDIDATES:
            print(f"[avatar_master] expected_source={p}")
        return 1

    pygame.init()
    pygame.display.set_mode((1, 1))
    src = pygame.image.load(str(src_path)).convert_alpha()

    # Keep concept large for codex/lore.
    concept = _fit(src, (768, 1024))

    # Portrait requirement: strict 512x512 focused face/hood/symbol.
    portrait = _portraitize(src, (512, 512))

    # Hologram runtime-friendly square keeps identity continuity.
    holo = _hologramize(src, (512, 512))

    pygame.image.save(concept, str(OUT_CONCEPT))
    pygame.image.save(portrait, str(OUT_PORTRAIT))
    pygame.image.save(holo, str(OUT_HOLO))

    print(f"[avatar_master] source={src_path}")
    print(f"[avatar_master] wrote={OUT_CONCEPT.name} size=768x1024")
    print(f"[avatar_master] wrote={OUT_PORTRAIT.name} size=512x512")
    print(f"[avatar_master] wrote={OUT_HOLO.name} size=512x512")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
