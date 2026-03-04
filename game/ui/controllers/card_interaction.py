from __future__ import annotations


class CardInteractionController:
    def __init__(self, logger=print):
        self.selected_index: int | None = None
        self.hover_index: int | None = None
        self.action_pressed = False
        self._log = logger

    def on_hover(self, idx: int | None):
        self.hover_index = idx

    def on_card_click(self, idx: int):
        self.selected_index = idx

    def clear_selection(self, reason: str):
        if self.selected_index is not None:
            self._log(f"[ui] selected_card cleared: reason={reason}")
        self.selected_index = None

    def validate_selection(self, hand_len: int):
        if self.selected_index is not None and self.selected_index >= hand_len:
            self.clear_selection("invalid_removed")
