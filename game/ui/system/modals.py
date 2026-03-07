"""Reusable modal framework for Chakana screens."""

from __future__ import annotations

import pygame

from .brand import ChakanaBrand
from .colors import UColors
from .components import UIButton, UIPanel, UILabel
from .layout import build_modal_preview_layout, safe_area


class ModalBase:
    def __init__(self):
        self.open = False
        self.title = ""
        self.message = ""
        self.confirm_label = "Confirmar"
        self.cancel_label = "Cancelar"
        self.on_confirm = None
        self.on_cancel = None

    def show(self, title: str, message: str = "", on_confirm=None, on_cancel=None):
        self.open = True
        self.title = str(title or "")
        self.message = str(message or "")
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def hide(self):
        self.open = False

    def _layout(self, surface: pygame.Surface):
        area = safe_area(surface.get_width(), surface.get_height(), ChakanaBrand.SAFE_MARGIN, ChakanaBrand.BOTTOM_SAFE_MARGIN)
        panel = pygame.Rect(0, 0, max(ChakanaBrand.COMPONENT_SIZES["modal_min_w"], int(area.w * 0.56)), max(ChakanaBrand.COMPONENT_SIZES["modal_min_h"], int(area.h * 0.44)))
        panel.center = area.center
        confirm = pygame.Rect(panel.centerx - 190, panel.bottom - 70, 180, 48)
        cancel = pygame.Rect(panel.centerx + 10, panel.bottom - 70, 180, 48)
        return panel, confirm, cancel

    def handle_click(self, pos: tuple[int, int], surface: pygame.Surface):
        if not self.open:
            return False
        panel, confirm, cancel = self._layout(surface)
        _ = panel
        if confirm.collidepoint(pos):
            self.open = False
            if callable(self.on_confirm):
                self.on_confirm()
            return True
        if cancel.collidepoint(pos):
            self.open = False
            if callable(self.on_cancel):
                self.on_cancel()
            return True
        return True

    def render(self, surface: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font):
        if not self.open:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        panel, confirm_rect, cancel_rect = self._layout(surface)
        UIPanel(panel, variant="alt").draw(surface)
        surface.blit(title_font.render(self.title, True, UColors.TEXT), (panel.x + 20, panel.y + 20))
        lines = UILabel.wrap(self.message, body_font, panel.w - 40, max_lines=4)
        y = panel.y + 64
        for line in lines:
            surface.blit(body_font.render(line, True, UColors.MUTED), (panel.x + 20, y))
            y += 28
        UIButton(confirm_rect, self.confirm_label, role="seal", premium=True).draw(surface, body_font)
        UIButton(cancel_rect, self.cancel_label, role="default", premium=False).draw(surface, body_font)


class ChoiceModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.choices: list[str] = []
        self.selected_index: int | None = None


class CardGridModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.hover_index: int | None = None


class LoreModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.portrait = None


def modal_preview_columns(panel_rect: pygame.Rect):
    """Helper for card/lore modals with preview columns."""
    return build_modal_preview_layout(panel_rect)
