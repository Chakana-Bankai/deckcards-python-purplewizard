"""Semantic color palette for Chakana UI."""

from __future__ import annotations


class UColors:
    """Semantic colors used across the UI system."""

    BACKGROUND = (9, 8, 18)
    PANEL = (29, 20, 46)
    PANEL_ALT = (40, 28, 62)
    BORDER = (173, 110, 255)
    BORDER_SOFT = (108, 84, 156)

    TEXT = (241, 236, 252)
    TEXT_DARK = (20, 14, 32)
    MUTED = (190, 176, 224)

    HP = (236, 72, 106)
    ENERGY = (92, 214, 255)
    BLOCK = (110, 188, 255)
    HARMONY = (214, 177, 74)
    RUPTURE = (234, 132, 72)
    RITUAL = (220, 204, 255)
    FEED = (237, 233, 246)
    LORE = (200, 184, 230)
    WARNING = (178, 84, 96)
    SUCCESS = (108, 224, 186)

    COMMON = (176, 182, 204)
    RARE = (120, 182, 255)
    EPIC = (186, 122, 255)
    LEGENDARY = (248, 210, 118)

    ROLE = {
        "execute": (220, 68, 120),
        "seal": (198, 140, 246),
        "end_turn": (214, 177, 74),
        "invalid": (116, 102, 130),
    }


# Compatibility mapping for legacy screens still using UI_THEME keys.
LEGACY_THEME = {
    "bg": UColors.BACKGROUND,
    "panel": UColors.PANEL,
    "panel_2": UColors.PANEL_ALT,
    "card_bg": (34, 24, 50),
    "card_text": UColors.TEXT,
    "card_border": UColors.BORDER_SOFT,
    "card_selected": UColors.BORDER,
    "shadow": (0, 0, 0, 120),
    "text": UColors.TEXT,
    "text_dark": UColors.TEXT_DARK,
    "muted": UColors.MUTED,
    "good": UColors.SUCCESS,
    "bad": UColors.WARNING,
    "gold": UColors.HARMONY,
    "energy": UColors.ENERGY,
    "block": UColors.BLOCK,
    "hp": UColors.HP,
    "violet": UColors.BORDER,
    "rupture": UColors.RUPTURE,
    "deep_purple": (26, 16, 42),
    "primary_purple": (50, 20, 82),
    "accent_violet": UColors.BORDER,
}
