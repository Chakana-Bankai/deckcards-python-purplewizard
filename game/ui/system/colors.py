"""Semantic color palette for Chakana UI."""

from __future__ import annotations


class UColors:
    """Semantic colors used across the UI system."""

    # Premium ritual base palette (yellow reserved for accents only).
    BACKGROUND = (18, 10, 31)  # #120A1F
    PANEL = (36, 21, 69)       # #241545
    PANEL_ALT = (26, 16, 48)   # #1A1030
    BORDER = (184, 140, 255)   # #B88CFF
    BORDER_SOFT = (112, 84, 164)

    TEXT = (243, 238, 255)      # #F3EEFF
    TEXT_DARK = (20, 14, 32)
    MUTED = (205, 189, 255)     # #CDBDFF

    HP = (236, 72, 106)
    ENERGY = (92, 214, 255)
    BLOCK = (110, 188, 255)
    HARMONY = (216, 184, 90)    # accent_confirm
    RUPTURE = (234, 132, 72)
    RITUAL = (220, 204, 255)
    FEED = (237, 233, 246)
    LORE = (205, 189, 255)
    WARNING = (178, 84, 96)
    SUCCESS = (108, 224, 186)

    COMMON = (176, 182, 204)
    RARE = (120, 182, 255)
    EPIC = (186, 122, 255)
    LEGENDARY = (229, 201, 107)  # accent_select

    ROLE = {
        "execute": (220, 68, 120),
        "seal": (198, 140, 246),
        "end_turn": (216, 184, 90),
        "invalid": (116, 102, 130),
        "menu": (72, 48, 116),
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
    "deep_purple": UColors.PANEL_ALT,
    "primary_purple": UColors.PANEL,
    "accent_violet": UColors.BORDER,
}
