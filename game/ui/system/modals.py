"""Reusable modal framework for Chakana screens."""

from __future__ import annotations

import pygame

from game.ui.components.card_renderer import render_card_medium
from game.ui.components.card_preview_panel import CardPreviewPanel

from .brand import ChakanaBrand
from .colors import UColors
from .components import UIButton, UIPanel, UILabel
from .layout import build_modal_preview_layout, inset, safe_area


class ModalBase:
    def __init__(self):
        self.open = False
        self.title = ""
        self.message = ""
        self.confirm_label = "Confirmar"
        self.cancel_label = "Cancelar"
        self.on_confirm = None
        self.on_cancel = None
        self.allow_empty_confirm = False

    def show(self, title: str, message: str = "", on_confirm=None, on_cancel=None):
        self.open = True
        self.title = str(title or "")
        self.message = str(message or "")
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def hide(self):
        self.open = False

    # Legacy aliases used by older wrappers.
    def close(self):
        self.hide()

    def dismiss(self):
        self.hide()

    def _base_layout(self, surface: pygame.Surface):
        area = safe_area(surface.get_width(), surface.get_height(), ChakanaBrand.SAFE_MARGIN, ChakanaBrand.BOTTOM_SAFE_MARGIN)
        panel = pygame.Rect(
            0,
            0,
            max(ChakanaBrand.COMPONENT_SIZES["modal_min_w"], int(area.w * 0.78)),
            max(ChakanaBrand.COMPONENT_SIZES["modal_min_h"], int(area.h * 0.78)),
        )
        panel.center = area.center
        header_h = 86
        footer_h = 78
        header = pygame.Rect(panel.x + 16, panel.y + 16, panel.w - 32, header_h)
        body = pygame.Rect(panel.x + 16, header.bottom + 10, panel.w - 32, panel.h - header_h - footer_h - 36)
        footer = pygame.Rect(panel.x + 16, panel.bottom - footer_h - 12, panel.w - 32, footer_h)

        btn_w = 220
        btn_h = 48
        gap = 22
        cancel_rect = pygame.Rect(footer.centerx - gap // 2 - btn_w, footer.y + footer.h // 2 - btn_h // 2, btn_w, btn_h)
        confirm_rect = pygame.Rect(footer.centerx + gap // 2, footer.y + footer.h // 2 - btn_h // 2, btn_w, btn_h)
        return panel, header, body, footer, confirm_rect, cancel_rect

    def _confirm_enabled(self) -> bool:
        return True

    def _confirm(self):
        self.open = False
        if callable(self.on_confirm):
            self.on_confirm()

    def _cancel(self):
        self.open = False
        if callable(self.on_cancel):
            self.on_cancel()

    def _handle_base_event(self, event, mapped_pos, surface: pygame.Surface):
        if not self.open:
            return False
        panel, _header, _body, _footer, confirm_rect, cancel_rect = self._base_layout(surface)
        _ = panel
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,):
                self._cancel()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._confirm_enabled() or self.allow_empty_confirm:
                    self._confirm()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if confirm_rect.collidepoint(mapped_pos):
                if self._confirm_enabled() or self.allow_empty_confirm:
                    self._confirm()
                return True
            if cancel_rect.collidepoint(mapped_pos):
                self._cancel()
                return True
        return False

    def _render_chrome(self, surface: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font):
        if not self.open:
            return None
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        panel, header, body, footer, confirm_rect, cancel_rect = self._base_layout(surface)
        UIPanel(panel, variant="alt").draw(surface)
        pygame.draw.rect(surface, UColors.PANEL_ALT, header, border_radius=10)
        pygame.draw.rect(surface, UColors.BORDER_SOFT, header, 1, border_radius=10)
        pygame.draw.rect(surface, UColors.PANEL, body, border_radius=10)
        pygame.draw.rect(surface, UColors.BORDER_SOFT, body, 1, border_radius=10)

        surface.blit(title_font.render(self.title, True, UColors.TEXT), (header.x + 12, header.y + 10))
        y = header.y + 42
        for line in UILabel.wrap(self.message, body_font, header.w - 24, max_lines=2):
            surface.blit(body_font.render(line, True, UColors.MUTED), (header.x + 12, y))
            y += 22

        confirm_btn = UIButton(confirm_rect, self.confirm_label, role="seal", premium=True)
        confirm_btn.disabled = not (self._confirm_enabled() or self.allow_empty_confirm)
        confirm_btn.draw(surface, body_font)
        UIButton(cancel_rect, self.cancel_label, role="default", premium=False).draw(surface, body_font)

        return panel, header, body, footer, confirm_rect, cancel_rect

    # Legacy compatibility adapter for callers that dispatch full pygame events.
    def handle_event(self, event, mapped_pos=None, surface: pygame.Surface | None = None):
        if not self.open:
            return False
        if surface is None:
            surface = pygame.display.get_surface()
            if surface is None:
                return False
        if mapped_pos is None:
            mapped_pos = getattr(event, "pos", pygame.mouse.get_pos())
        return self._handle_base_event(event, mapped_pos, surface)

    # Legacy compatibility adapter for older callers.
    def handle_click(self, pos: tuple[int, int], surface: pygame.Surface):
        if not self.open:
            return False
        _panel, _header, _body, _footer, confirm_rect, cancel_rect = self._base_layout(surface)
        if confirm_rect.collidepoint(pos):
            if self._confirm_enabled() or self.allow_empty_confirm:
                self._confirm()
            return True
        if cancel_rect.collidepoint(pos):
            self._cancel()
            return True
        return True

    # Legacy compatibility adapter for callers that still use modal.render(...).
    def render(self, surface: pygame.Surface, title_font=None, body_font=None):
        if title_font is None or not hasattr(title_font, "render"):
            title_font = pygame.font.Font(None, 28)
        if body_font is None or not hasattr(body_font, "render"):
            body_font = pygame.font.Font(None, 22)
        self._render_chrome(surface, title_font, body_font)

    def update(self, dt: float):
        _ = dt
        return None


class ChoiceModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.choices: list[dict] = []
        self.selected_index: int | None = None
        self.hover_index: int | None = None
        self.max_choices = 5

    def show_choices(self, title: str, message: str, choices: list[dict], on_confirm=None, on_cancel=None):
        self.show(title, message, on_confirm=on_confirm, on_cancel=on_cancel)
        self.choices = list(choices or [])[: self.max_choices]
        self.selected_index = None
        self.hover_index = None

    def _confirm_enabled(self) -> bool:
        return self.selected_index is not None

    def choice_rects(self, body_rect: pygame.Rect):
        count = max(1, min(self.max_choices, len(self.choices)))
        gap = 10
        row_h = max(64, min(96, (body_rect.h - (count - 1) * gap) // count))
        out = []
        for i in range(count):
            out.append(pygame.Rect(body_rect.x + 8, body_rect.y + 8 + i * (row_h + gap), body_rect.w - 16, row_h))
        return out

    def handle_event(self, event, mapped_pos=None, surface: pygame.Surface | None = None):
        if not self.open:
            return False
        if surface is None:
            surface = pygame.display.get_surface()
            if surface is None:
                return False
        if mapped_pos is None:
            mapped_pos = getattr(event, "pos", pygame.mouse.get_pos())
        if self._handle_base_event(event, mapped_pos, surface):
            return True

        panel, header, body, _footer, _confirm, _cancel = self._base_layout(surface)
        _ = panel, header
        rects = self.choice_rects(body)

        if event.type == pygame.MOUSEMOTION:
            self.hover_index = None
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.hover_index = i
                    break
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.selected_index = None if self.selected_index == i else i
                    return True
            return True
        return True

    def render(self, surface: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font):
        chrome = self._render_chrome(surface, title_font, body_font)
        if chrome is None:
            return
        _panel, _header, body, _footer, _confirm, _cancel = chrome
        rects = self.choice_rects(body)
        for i, rr in enumerate(rects):
            opt = self.choices[i] if i < len(self.choices) else {}
            selected = i == self.selected_index
            hovered = i == self.hover_index
            fill = UColors.PANEL_ALT if hovered else UColors.PANEL
            pygame.draw.rect(surface, fill, rr, border_radius=10)
            border = UColors.HARMONY if selected else UColors.BORDER_SOFT
            pygame.draw.rect(surface, border, rr, 2 if selected else 1, border_radius=10)
            title = str(opt.get("title", opt.get("label", f"Opcion {i + 1}")))
            subtitle = str(opt.get("subtitle", opt.get("effect_label", "")))
            surface.blit(body_font.render(UILabel.clamp(title, body_font, rr.w - 22), True, UColors.TEXT), (rr.x + 10, rr.y + 10))
            if subtitle:
                surface.blit(body_font.render(UILabel.clamp(subtitle, body_font, rr.w - 22), True, UColors.MUTED), (rr.x + 10, rr.y + 34))


class CardGridModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.selected_index: int | None = None
        self.hover_index: int | None = None
        self.preview = CardPreviewPanel()
        self.cols = 3

    def show_cards(self, title: str, message: str, cards: list, on_confirm=None, on_cancel=None):
        self.show(title, message, on_confirm=on_confirm, on_cancel=on_cancel)
        self.cards = list(cards or [])
        self.selected_index = None
        self.hover_index = None

    def _confirm_enabled(self) -> bool:
        return self.selected_index is not None

    def selected_card(self):
        if self.selected_index is None:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.cards):
            return None
        return self.cards[self.selected_index]

    def _columns(self, body_rect: pygame.Rect):
        left, right = build_modal_preview_layout(body_rect)
        return left, right

    def card_rects(self, body_rect: pygame.Rect):
        left, _ = self._columns(body_rect)
        count = max(1, len(self.cards))
        cols = min(max(1, self.cols), count)
        rows = max(1, (count + cols - 1) // cols)
        gap_x = 12
        gap_y = 14
        usable = inset(left, 6)
        card_w = max(190, min(320, (usable.w - (cols - 1) * gap_x) // cols))
        card_h = max(250, min(460, (usable.h - (rows - 1) * gap_y) // rows))
        out = []
        for i in range(count):
            r = i // cols
            c = i % cols
            out.append(pygame.Rect(usable.x + c * (card_w + gap_x), usable.y + r * (card_h + gap_y), card_w, card_h))
        return out

    def handle_event(self, event, mapped_pos=None, surface: pygame.Surface | None = None):
        if not self.open:
            return False
        if surface is None:
            surface = pygame.display.get_surface()
            if surface is None:
                return False
        if mapped_pos is None:
            mapped_pos = getattr(event, "pos", pygame.mouse.get_pos())
        if self._handle_base_event(event, mapped_pos, surface):
            return True

        _panel, _header, body, _footer, _confirm, _cancel = self._base_layout(surface)
        rects = self.card_rects(body)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                if self.selected_index is None:
                    self.selected_index = 0 if self.cards else None
                else:
                    self.selected_index = max(0, self.selected_index - 1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                if self.selected_index is None:
                    self.selected_index = 0 if self.cards else None
                else:
                    self.selected_index = min(max(0, len(self.cards) - 1), self.selected_index + 1)
                return True

        if event.type == pygame.MOUSEMOTION:
            self.hover_index = None
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.hover_index = i
                    break
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rr in enumerate(rects):
                if rr.collidepoint(mapped_pos):
                    self.selected_index = None if self.selected_index == i else i
                    return True
            return True
        return True

    def render(self, surface: pygame.Surface, app):
        chrome = self._render_chrome(surface, app.big_font, app.small_font)
        if chrome is None:
            return
        _panel, _header, body, _footer, _confirm, _cancel = chrome
        left, right = self._columns(body)
        rects = self.card_rects(body)

        for i, rr in enumerate(rects):
            if i >= len(self.cards):
                break
            card = self.cards[i]
            render_card_medium(
                surface,
                rr,
                card,
                theme=None,
                state={
                    "app": app,
                    "ctx": None,
                    "selected": i == self.selected_index,
                    "hovered": i == self.hover_index,
                },
            )

        preview_card = self.selected_card()
        if preview_card is None and self.hover_index is not None and 0 <= self.hover_index < len(self.cards):
            preview_card = self.cards[self.hover_index]
        self.preview.render(surface, right, preview_card, app=app)


class LoreModal(ModalBase):
    def __init__(self):
        super().__init__()
        self.portrait_group = "guides"
        self.portrait_id = ""
        self.lines: list[str] = []

    def show_lore(self, title: str, message: str, lines: list[str] | None = None, portrait_group: str = "guides", portrait_id: str = "", on_confirm=None, on_cancel=None):
        self.show(title, message, on_confirm=on_confirm, on_cancel=on_cancel)
        self.lines = list(lines or [])
        self.portrait_group = portrait_group
        self.portrait_id = portrait_id
        self.allow_empty_confirm = True

    def handle_event(self, event, mapped_pos=None, surface: pygame.Surface | None = None):
        # Lore modal is confirm/cancel-only in current flow; safely no-op when closed.
        return super().handle_event(event, mapped_pos=mapped_pos, surface=surface)

    def render(self, surface: pygame.Surface, app=None, title_font=None, body_font=None):
        if app is not None and hasattr(app, "big_font") and hasattr(app, "small_font"):
            title_font = app.big_font
            body_font = app.small_font
        if title_font is None or not hasattr(title_font, "render"):
            title_font = pygame.font.Font(None, 28)
        if body_font is None or not hasattr(body_font, "render"):
            body_font = pygame.font.Font(None, 22)
        chrome = self._render_chrome(surface, title_font, body_font)
        if chrome is None:
            return
        _panel, _header, body, _footer, _confirm, _cancel = chrome
        left, right = build_modal_preview_layout(body)

        pygame.draw.rect(surface, UColors.PANEL_ALT, left, border_radius=10)
        pygame.draw.rect(surface, UColors.BORDER_SOFT, left, 1, border_radius=10)
        sprite = None
        if app is not None and hasattr(app, "assets"):
            sprite = app.assets.sprite(self.portrait_group, self.portrait_id, (left.w - 20, left.h - 20), fallback=(42, 32, 62))
        if sprite is not None:
            surface.blit(sprite, (left.x + 10, left.y + 10))

        pygame.draw.rect(surface, UColors.PANEL, right, border_radius=10)
        pygame.draw.rect(surface, UColors.BORDER_SOFT, right, 1, border_radius=10)
        y = right.y + 12
        text_font = getattr(app, "font", None) if app is not None else None
        if text_font is None or not hasattr(text_font, "render"):
            text_font = body_font
        for ln in self.lines[:8]:
            for part in UILabel.wrap(str(ln), text_font, right.w - 20, max_lines=2):
                if y > right.bottom - 24:
                    break
                surface.blit(text_font.render(part, True, UColors.TEXT), (right.x + 10, y))
                y += 24


def modal_preview_columns(panel_rect: pygame.Rect):
    """Helper for card/lore modals with preview columns."""
    return build_modal_preview_layout(panel_rect)
