from __future__ import annotations

import pygame

from game.ui.system.layout import safe_area
from game.ui.system.typography import BUTTON_FONT, LORE_FONT, ChakanaTypography
from game.ui.system.modals import ModalBase


class _CompactConfirmModal(ModalBase):
    """Small centered confirm modal used only by ModalConfirm wrapper."""

    def _base_layout(self, surface: pygame.Surface):
        area = safe_area(surface.get_width(), surface.get_height(), 20, 56)
        panel = pygame.Rect(0, 0, min(640, int(area.w * 0.56)), min(280, int(area.h * 0.34)))
        panel.center = area.center

        header_h = 64
        footer_h = 64
        header = pygame.Rect(panel.x + 14, panel.y + 12, panel.w - 28, header_h)
        body = pygame.Rect(panel.x + 14, header.bottom + 6, panel.w - 28, panel.h - header_h - footer_h - 24)
        footer = pygame.Rect(panel.x + 14, panel.bottom - footer_h - 8, panel.w - 28, footer_h)

        btn_w = max(130, min(170, (footer.w - 22) // 2))
        btn_h = 42
        gap = 22
        cancel_rect = pygame.Rect(footer.centerx - gap // 2 - btn_w, footer.y + footer.h // 2 - btn_h // 2, btn_w, btn_h)
        confirm_rect = pygame.Rect(footer.centerx + gap // 2, footer.y + footer.h // 2 - btn_h // 2, btn_w, btn_h)
        return panel, header, body, footer, confirm_rect, cancel_rect


class ModalConfirm:
    """Compatibility wrapper over centralized ModalBase."""

    def __init__(self):
        self.modal = _CompactConfirmModal()

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
        title_font = ChakanaTypography().get(BUTTON_FONT, 26)
        body_font = small_font if small_font is not None else ChakanaTypography().get(LORE_FONT, 20)
        self.modal.render(surface, title_font, body_font)
