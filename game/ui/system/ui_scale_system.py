"""Global UI scale tokens for consistent Full HD readability."""

from __future__ import annotations

FONT_TITLE = 32
FONT_SECTION = 24
FONT_LABEL = 18
FONT_SMALL = 14
FONT_TINY = 10

ICON_HUD_SMALL = 18
ICON_HUD_MEDIUM = 24
ICON_HUD_LARGE = 30

ICON_CARD_SMALL = 14
ICON_CARD_MEDIUM = 18
ICON_CARD_KPI = 20
ICON_TOOLTIP = 18

PANEL_OUTER_MARGIN = 12
PANEL_INNER_PADDING = 10
SECTION_GAP = 6
TEXT_SAFE_PADDING = 8

FONT_CONTEXT_SIZES: dict[str, int] = {
    "combat_title": FONT_SECTION,
    "combat_label": FONT_LABEL,
    "combat_value": FONT_SECTION,
    "card_title": 28,
    "card_type": FONT_SMALL,
    "card_effect": FONT_SMALL,
    "card_lore": FONT_SMALL,
    "card_footer": FONT_TINY,
    "codex_header": FONT_SECTION,
    "map_label": FONT_SMALL,
    "shop_header": FONT_SECTION,
}

ICON_SIZE_PROFILE: dict[str, int] = {
    "small": ICON_HUD_SMALL,
    "medium": ICON_HUD_MEDIUM,
    "large": ICON_HUD_LARGE,
}


def icon_px(profile: str, fallback: int = ICON_HUD_MEDIUM) -> int:
    return int(ICON_SIZE_PROFILE.get(str(profile or "").lower(), fallback))
