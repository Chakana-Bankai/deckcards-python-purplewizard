"""Centralized Chakana brand constants for reusable UI sizing and rhythm."""

from __future__ import annotations


class ChakanaBrand:
    """Brand-level constants shared by screens and widgets."""

    TITLE_FONT_SIZE = 72
    SUBTITLE_FONT_SIZE = 34
    HEADER_FONT_SIZE = 24
    BODY_FONT_SIZE = 18
    SMALL_FONT_SIZE = 14

    HP_FONT_SIZE = 36
    ENERGY_FONT_SIZE = 32
    TURN_FONT_SIZE = 28

    PANEL_PADDING = 16
    PANEL_GAP = 12
    SAFE_MARGIN = 20
    BOTTOM_SAFE_MARGIN = 56

    BORDER_RADIUS = 6
    PANEL_BORDER_WIDTH = 2

    CARD_SCALE_HOVER = 1.28

    COMPONENT_SIZES = {
        "button_h": 56,
        "chip_h": 24,
        "modal_min_w": 540,
        "modal_min_h": 320,
        "tooltip_max_w": 520,
    }

    TEXT_STYLES = {
        "premium_title": "title",
        "combat_numbers": "numeric",
        "map_info": "small",
        "lore_text": "body",
        "modal_buttons": "button",
    }
