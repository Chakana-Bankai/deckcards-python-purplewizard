from __future__ import annotations

import pygame

from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.pixel_icons import draw_icon_with_value
from game.ui.theme import UI_THEME, UI_SAFE_BOTTOM, UI_SAFE_SIDE


class ModalCardPicker:
    def __init__(self):
        self.open = False
        self.title = "Prever"
        self.help_text = "Mira cartas, elige 1 para mantener arriba y el resto irá al descarte."
        self.cards = []
        self.selected_index = None
        self.hover_index = None
        self.required_selections = 1
        self.on_confirm = None
        self.on_cancel = None
        self._pulse_t = 0.0

        self.panel = pygame.Rect(0, 0, 1, 1)
        self.left_rect = pygame.Rect(0, 0, 1, 1)
        self.preview_rect = pygame.Rect(0, 0, 1, 1)
        self.confirm_rect = pygame.Rect(0, 0, 230, 50)
        self.cancel_rect = pygame.Rect(0, 0, 220, 50)

    def show(self, cards, on_confirm=None, on_cancel=None, required_selections: int = 1):
        self.open = True
        self.cards = list(cards or [])
        self.selected_index = None
        self.hover_index = None
        self.required_selections = max(1, int(required_selections or 1))
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def close(self):
        self.open = False
        self.cards = []
        self.selected_index = None
        self.hover_index = None
        self.on_confirm = None
        self.on_cancel = None
        self._pulse_t = 0.0

    def _layout(self, surface: pygame.Surface):
        w, h = surface.get_size()
        self.panel = pygame.Rect(UI_SAFE_SIDE * 2, UI_SAFE_SIDE * 2, w - UI_SAFE_SIDE * 4, h - UI_SAFE_SIDE * 4)

        buttons_y = h - UI_SAFE_BOTTOM
        self.cancel_rect.size = (220, 48)
        self.confirm_rect.size = (230, 48)
        self.cancel_rect.center = (w // 2 - 160, buttons_y)
        self.confirm_rect.center = (w // 2 + 160, buttons_y)

        header_top = self.panel.y + 108
        content_bottom = buttons_y - 20
        content_h = max(260, content_bottom - header_top)

        left_w = int(self.panel.w * 0.60)
        self.left_rect = pygame.Rect(self.panel.x + 24, header_top, left_w - 30, content_h)
        self.preview_rect = pygame.Rect(self.left_rect.right + 18, header_top, self.panel.right - self.left_rect.right - 42, content_h)

    def _card_rects(self):
        count = max(1, len(self.cards))
        cols = min(3, count)
        rows = max(1, (count + cols - 1) // cols)

        gap_x = 14
        gap_y = 18
        usable_w = self.left_rect.w - 12
        usable_h = self.left_rect.h - 16

        card_w = max(220, min(350, (usable_w - (cols - 1) * gap_x) // cols))
        aspect = 350 / 520
        card_h = int(card_w / aspect)
        max_h_by_rows = (usable_h - (rows - 1) * gap_y) // rows
        if card_h > max_h_by_rows:
            card_h = max(250, max_h_by_rows)
            card_w = int(card_h * aspect)

        total_w = cols * card_w + (cols - 1) * gap_x
        start_x = self.left_rect.x + max(0, (self.left_rect.w - total_w) // 2)
        start_y = self.left_rect.y + 8

        rects = []
        for i in range(count):
            r = i // cols
            c = i % cols
            rects.append(pygame.Rect(start_x + c * (card_w + gap_x), start_y + r * (card_h + gap_y), card_w, card_h))
        return rects

    def _confirm_enabled(self) -> bool:
        return self.selected_index is not None

    def handle_event(self, event, mapped_pos):
        if not self.open:
            return False

        surface = pygame.display.get_surface()
        if surface is not None:
            self._layout(surface)

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
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._confirm_enabled():
                    self._confirm()
                return True
            if event.key == pygame.K_ESCAPE:
                self._cancel()
                return True

        if event.type == pygame.MOUSEMOTION:
            self.hover_index = None
            for i, r in enumerate(self._card_rects()):
                if r.collidepoint(mapped_pos):
                    self.hover_index = i
                    break
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_rect.collidepoint(mapped_pos):
                if self._confirm_enabled():
                    self._confirm()
                return True
            if self.cancel_rect.collidepoint(mapped_pos):
                self._cancel()
                return True
            if not self.panel.collidepoint(mapped_pos):
                return True
            for i, r in enumerate(self._card_rects()):
                if r.collidepoint(mapped_pos):
                    self.selected_index = i
                    return True
        return True

    def _confirm(self):
        idx = self.selected_index if self.selected_index is not None else 0
        idx = min(max(0, idx), max(0, len(self.cards) - 1))
        chosen = self.cards[idx] if self.cards else None
        cb = self.on_confirm
        self.close()
        if callable(cb):
            cb(chosen)

    def _cancel(self):
        cb = self.on_cancel
        self.close()
        if callable(cb):
            cb()

    def render(self, surface, app):
        if not self.open:
            return
        self._pulse_t += 0.08

        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 165))
        surface.blit(ov, (0, 0))

        self._layout(surface)
        pygame.draw.rect(surface, UI_THEME["deep_purple"], self.panel, border_radius=14)
        pygame.draw.rect(surface, UI_THEME["gold"], self.panel, 2, border_radius=14)

        surface.blit(app.big_font.render(self.title, True, UI_THEME["gold"]), (self.panel.x + 24, self.panel.y + 18))
        surface.blit(app.small_font.render(self.help_text, True, UI_THEME["muted"]), (self.panel.x + 26, self.panel.y + 68))

        for i, c in enumerate(self.cards):
            r = self._card_rects()[i]
            sel = i == self.selected_index
            hover = i == self.hover_index
            pygame.draw.rect(surface, UI_THEME["panel_2"] if hover else UI_THEME["panel"], r, border_radius=12)
            pulse = 1 + int(1.5 * (1 + pygame.math.Vector2(1, 0).rotate(self._pulse_t * 57).x))
            border_w = 3 if sel else (2 if hover else 1)
            color = UI_THEME["gold"] if (sel or hover) else UI_THEME["accent_violet"]
            pygame.draw.rect(surface, color, r, border_w + (pulse if sel else 0), border_radius=12)

            art_h = min(300, r.h - 90)
            art = app.assets.sprite("cards", getattr(getattr(c, "definition", None), "id", ""), (r.w - 20, art_h), fallback=(82, 52, 112))
            surface.blit(art, (r.x + 10, r.y + 8))

            name_key = getattr(getattr(c, "definition", None), "name_key", getattr(c, "id", "Carta"))
            name = app.loc.t(name_key)
            surface.blit(app.tiny_font.render(name[:24], True, UI_THEME["text"]), (r.x + 8, r.y + art_h + 22))
            cost = getattr(c, "cost", getattr(getattr(c, "definition", None), "cost", 0))
            surface.blit(app.tiny_font.render(f"Coste {cost}", True, UI_THEME["energy"]), (r.x + 8, r.y + art_h + 44))

            summary = summarize_card_effect(getattr(c, "definition", {}), card_instance=c, ctx=None)
            icon_data = CardPreviewPanel(app)._icon_row(summary)
            x_icon = r.x + 88
            for icon_name, val in icon_data[:3]:
                x_icon = draw_icon_with_value(surface, icon_name, val, UI_THEME["gold"], app.tiny_font, x_icon, r.y + art_h + 42, size=1)

            if sel:
                surface.blit(app.tiny_font.render("SE QUEDA ARRIBA", True, UI_THEME["good"]), (r.x + 8, r.bottom - 22))

        preview_card = None
        if self.selected_index is not None and self.selected_index < len(self.cards):
            preview_card = self.cards[self.selected_index]
        elif self.hover_index is not None and self.hover_index < len(self.cards):
            preview_card = self.cards[self.hover_index]
        CardPreviewPanel(app=app).render(surface, self.preview_rect, preview_card, app=app)

        enabled = self._confirm_enabled()
        pygame.draw.rect(surface, UI_THEME["violet"] if enabled else (82, 78, 104), self.confirm_rect, border_radius=10)
        pygame.draw.rect(surface, UI_THEME["panel_2"], self.cancel_rect, border_radius=10)
        surface.blit(app.small_font.render("Confirmar", True, UI_THEME["text"]), (self.confirm_rect.x + 58, self.confirm_rect.y + 10))
        surface.blit(app.small_font.render("Cancelar", True, UI_THEME["text"]), (self.cancel_rect.x + 62, self.cancel_rect.y + 10))
