"""Render layer order constants for predictable UI stacking."""

from __future__ import annotations


class Layers:
    """Render order.

    Hover cards must render above standard cards.
    Tooltips render above cards.
    Modals render above board/HUD.
    Transitions render above everything.
    """

    LAYER_BACKGROUND = 0
    LAYER_BOARD = 1
    LAYER_HUD = 2
    LAYER_CARDS = 3
    LAYER_MODALS = 4
    LAYER_TOOLTIPS = 5
    LAYER_TRANSITIONS = 6
