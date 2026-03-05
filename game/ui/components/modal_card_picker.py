from __future__ import annotations

import pygame

from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.pixel_icons import draw_icon_with_value
from game.ui.theme import UI_THEME


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
        panel = pygame.Rect(120, 120, w - 240, h - 240)
        cards_area = pygame.Rect(panel.x + 26, panel.y + 108, 970, panel.h - 190)
        preview = pygame.Rect(cards_area.right + 16, panel.y + 108, panel.right - cards_area.right - 42, panel.h - 190)
        confirm = pygame.Rect(panel.right - 270, panel.bottom - 62, 230, 44)
        cancel = pygame.Rect(panel.right - 520, panel.bottom - 62, 220, 44)
        return panel, cards_area, preview, confirm, cancel

    def _confirm_enabled(self) -> bool:
        return self.selected_index is not None

    def handle_event(self, event, mapped_pos):
        if not self.open:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if self.selected_index is None:
                    self.selected_index = 0 if self.cards else None
                else:
                    self.selected_index = max(0, self.selected_index - 1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_d):
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
            surface = pygame.display.get_surface()
            if surface is None:
                return True
            _panel, cards_area, _preview, _confirm, _cancel = self._layout(surface)
            self.hover_index = None
            count = max(1, len(self.cards))
            gap = 10
            card_w = max(130, min(184, (cards_area.w - (count - 1) * gap) // count))
            card_h = cards_area.h
            for i, _ in enumerate(self.cards):
                r = pygame.Rect(cards_area.x + i * (card_w + gap), cards_area.y, card_w, card_h)
                if r.collidepoint(mapped_pos):
                    self.hover_index = i
                    break
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            surface = pygame.display.get_surface()
            if surface is None:
                return True
            panel, cards_area, _preview, confirm, cancel = self._layout(surface)
            if confirm.collidepoint(mapped_pos):
                if self._confirm_enabled():
                    self._confirm()
                return True
            if cancel.collidepoint(mapped_pos):
                self._cancel()
                return True
            if not panel.collidepoint(mapped_pos):
                return True

            count = max(1, len(self.cards))
            gap = 10
            card_w = max(130, min(184, (cards_area.w - (count - 1) * gap) // count))
            card_h = cards_area.h
            for i, _ in enumerate(self.cards):
                r = pygame.Rect(cards_area.x + i * (card_w + gap), cards_area.y, card_w, card_h)
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

        panel, cards_area, preview_rect, confirm, cancel = self._layout(surface)
        pygame.draw.rect(surface, UI_THEME["deep_purple"], panel, border_radius=14)
        pygame.draw.rect(surface, UI_THEME["gold"], panel, 2, border_radius=14)

        surface.blit(app.big_font.render(self.title, True, UI_THEME["gold"]), (panel.x + 24, panel.y + 18))
        help_text = "Prever: Mira cartas. Elige 1 para tu mano futura; el resto va al descarte."
        surface.blit(app.small_font.render(help_text, True, UI_THEME["muted"]), (panel.x + 26, panel.y + 68))

        count = max(1, len(self.cards))
        gap = 10
        card_w = max(130, min(184, (cards_area.w - (count - 1) * gap) // count))
        card_h = cards_area.h
        for i, c in enumerate(self.cards):
            r = pygame.Rect(cards_area.x + i * (card_w + gap), cards_area.y, card_w, card_h)
            sel = i == self.selected_index
            hover = i == self.hover_index
            pygame.draw.rect(surface, UI_THEME["panel"], r, border_radius=10)
            pulse = 1 + int(1.5 * (1 + pygame.math.Vector2(1, 0).rotate(self._pulse_t * 57).x))
            border_w = 3 if sel else (2 if hover else 1)
            color = UI_THEME["gold"] if (sel or hover) else UI_THEME["accent_violet"]
            pygame.draw.rect(surface, color, r, border_w + (pulse if sel else 0), border_radius=10)

            art = app.assets.sprite("cards", getattr(getattr(c, "definition", None), "id", ""), (r.w - 10, 170), fallback=(82, 52, 112))
            surface.blit(art, (r.x + 5, r.y + 6))
            name_key = getattr(getattr(c, "definition", None), "name_key", getattr(c, "id", "Carta"))
            name = app.loc.t(name_key)
            surface.blit(app.tiny_font.render(name[:20], True, UI_THEME["text"]), (r.x + 6, r.y + 182))
            cost = getattr(c, "cost", getattr(getattr(c, "definition", None), "cost", 0))
            surface.blit(app.tiny_font.render(f"Coste {cost}", True, UI_THEME["energy"]), (r.x + 6, r.y + 204))
            summary = summarize_card_effect(getattr(c, "definition", {}), card_instance=c, ctx=None)
            icon_data = CardPreviewPanel(app)._icon_row(summary)
            x_icon = r.x + 64
            for icon_name, val in icon_data[:2]:
                x_icon = draw_icon_with_value(surface, icon_name, val, UI_THEME["gold"], app.tiny_font, x_icon, r.y + 202, size=1)
            if sel:
                surface.blit(app.tiny_font.render("SE QUEDA ARRIBA", True, UI_THEME["good"]), (r.x + 6, r.bottom - 20))

        preview_card = None
        if self.selected_index is not None and self.selected_index < len(self.cards):
            preview_card = self.cards[self.selected_index]
        elif self.hover_index is not None and self.hover_index < len(self.cards):
            preview_card = self.cards[self.hover_index]
        CardPreviewPanel(app).render(surface, preview_rect, preview_card)

        enabled = self._confirm_enabled()
        pygame.draw.rect(surface, UI_THEME["violet"] if enabled else (82, 78, 104), confirm, border_radius=10)
        pygame.draw.rect(surface, UI_THEME["panel_2"], cancel, border_radius=10)
        surface.blit(app.small_font.render("Confirmar", True, UI_THEME["text"]), (confirm.x + 58, confirm.y + 10))
        surface.blit(app.small_font.render("Cancelar", True, UI_THEME["text"]), (cancel.x + 62, cancel.y + 10))
