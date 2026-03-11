from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortraitSpec:
    composition: str
    crop_zoom: float
    source_focus_y: float
    target_focus_y: float
    pixel_divisor: int
    vignette_alpha: int
    tint_alpha: int
    scanline_alpha: int
    noise_alpha: int
    border_alpha: int
    marker_kind: str
    marker_scale: float
    rgb_shift: tuple[int, int]


def resolve_portrait_spec(role: str, style: str) -> PortraitSpec:
    family = str(role or "chakana_mage").split("__", 1)[0].strip().lower()
    style_key = str(style or "portrait").strip().lower()

    if family == "archon":
        base = PortraitSpec("ominous_bust", 1.18, 0.34, 0.38, 3, 84, 42, 20, 18, 210, "archon_sigil", 0.22, (1, -1))
    elif family == "guide":
        base = PortraitSpec("guide_bust", 1.10, 0.35, 0.40, 3, 62, 26, 14, 10, 190, "guide_halo", 0.20, (1, 0))
    elif family == "enemy":
        base = PortraitSpec("enemy_bust", 1.14, 0.35, 0.40, 3, 72, 30, 16, 14, 198, "enemy_core", 0.18, (1, -1))
    else:
        base = PortraitSpec("hero_bust", 1.16, 0.34, 0.39, 3, 68, 28, 14, 12, 196, "chakana_pendant", 0.19, (1, -1))

    if style_key == "concept":
        return PortraitSpec(
            base.composition,
            max(1.02, base.crop_zoom - 0.08),
            base.source_focus_y,
            min(0.43, base.target_focus_y + 0.03),
            max(4, base.pixel_divisor + 1),
            max(40, base.vignette_alpha - 14),
            max(18, base.tint_alpha - 8),
            0,
            max(0, base.noise_alpha - 8),
            max(160, base.border_alpha - 18),
            base.marker_kind,
            max(0.16, base.marker_scale - 0.02),
            (0, 0),
        )
    if style_key == "hologram":
        return PortraitSpec(
            base.composition,
            base.crop_zoom,
            base.source_focus_y,
            base.target_focus_y,
            base.pixel_divisor,
            max(44, base.vignette_alpha - 18),
            max(20, base.tint_alpha - 2),
            max(10, base.scanline_alpha),
            max(8, base.noise_alpha),
            base.border_alpha,
            base.marker_kind,
            base.marker_scale,
            base.rgb_shift,
        )
    if style_key == "mini":
        return PortraitSpec(
            base.composition,
            max(1.05, base.crop_zoom - 0.04),
            base.source_focus_y,
            min(0.43, base.target_focus_y + 0.02),
            max(4, base.pixel_divisor + 1),
            max(40, base.vignette_alpha - 16),
            max(16, base.tint_alpha - 6),
            max(8, base.scanline_alpha - 4),
            max(6, base.noise_alpha - 6),
            max(150, base.border_alpha - 28),
            base.marker_kind,
            max(0.14, base.marker_scale - 0.03),
            (0, 0),
        )
    return base
