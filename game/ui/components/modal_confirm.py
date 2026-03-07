from __future__ import annotations

import pygame

from game.ui.system.typography import BUTTON_FONT, LORE_FONT, ChakanaTypography
from game.ui.system.modals import ModalBase


class ModalConfirm:
    """Compatibility wrapper over centralized ModalBase."""

    def __init__(self):
        self.modal = ModalBase()

    @property
    def open(self):
        return self.modal.open

    def show(self, message: str, on_yes=None, on_no=None):
        self.modal.confirm_label = "Confirmar"
        self.modal.cancel_label = "Cancelar"
        self.modal.show("Confirmar accion", message, on_confirm=on_yes, on_cancel=on_no)

    def handle_event(self, pos):
        if not self.modal.open:
            return False
        surface = pygame.display.get_surface()
        if surface is None:
            return False
        return self.modal.handle_click(pos, surface)

    def render(self, surface, font, small_font):
        title_font = ChakanaTypography().get(BUTTON_FONT, 28)
        body_font = small_font if small_font is not None else ChakanaTypography().get(LORE_FONT, 22)
        self.modal.render(surface, title_font, body_font)

