from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class ModalCardPicker:
    def __init__(self):
        self.open = False
        self.title = "Visión (Scry)"
        self.help_text = "Observa las próximas N cartas. Deja 1 arriba y envía el resto al descarte."
        self.cards = []
        self.selected_index = 0
        self.on_confirm = None
        self.on_cancel = None

    def show(self, cards, on_confirm=None, on_cancel=None):
        self.open = True
        self.cards = list(cards or [])
        self.selected_index = 0
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def close(self):
        self.open = False
        self.cards = []
        self.selected_index = 0
        self.on_confirm = None
        self.on_cancel = None

    def _layout(self, surface: pygame.Surface):
        w, h = surface.get_size()
        panel = pygame.Rect(w // 2 - 520, h // 2 - 250, 1040, 500)
        confirm = pygame.Rect(panel.right - 260, panel.bottom - 72, 220, 52)
        cancel = pygame.Rect(panel.x + 40, panel.bottom - 72, 220, 52)
        cards_area = pygame.Rect(panel.x + 30, panel.y + 122, panel.w - 60, panel.h - 220)
        return panel, cards_area, confirm, cancel

    def handle_event(self, event, mapped_pos):
        if not self.open:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected_index = max(0, self.selected_index - 1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected_index = min(max(0, len(self.cards) - 1), self.selected_index + 1)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()
                return True
            if event.key == pygame.K_ESCAPE:
                self._cancel()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
<<<<<<< ours
<<<<<<< ours
            panel, cards_area, confirm, cancel = self._layout(event.surface if hasattr(event, "surface") else pygame.display.get_surface())
=======
=======
>>>>>>> theirs
            surface = pygame.display.get_surface()
            if surface is None:
                return True
            panel, cards_area, confirm, cancel = self._layout(surface)
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
            if confirm.collidepoint(mapped_pos):
                self._confirm()
                return True
            if cancel.collidepoint(mapped_pos):
                self._cancel()
                return True

            count = max(1, len(self.cards))
            gap = 12
            card_w = max(130, min(180, (cards_area.w - (count - 1) * gap) // count))
            card_h = cards_area.h
            for i, _ in enumerate(self.cards):
                r = pygame.Rect(cards_area.x + i * (card_w + gap), cards_area.y, card_w, card_h)
                if r.collidepoint(mapped_pos):
                    self.selected_index = i
                    return True
        return True

    def _confirm(self):
        idx = min(self.selected_index, max(0, len(self.cards) - 1))
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
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 165))
        surface.blit(ov, (0, 0))

        panel, cards_area, confirm, cancel = self._layout(surface)
        pygame.draw.rect(surface, UI_THEME["deep_purple"], panel, border_radius=14)
        pygame.draw.rect(surface, UI_THEME["gold"], panel, 2, border_radius=14)

        surface.blit(app.big_font.render(self.title, True, UI_THEME["gold"]), (panel.x + 28, panel.y + 22))
        surface.blit(app.small_font.render(self.help_text, True, UI_THEME["muted"]), (panel.x + 30, panel.y + 78))

        count = max(1, len(self.cards))
        gap = 12
        card_w = max(130, min(180, (cards_area.w - (count - 1) * gap) // count))
        card_h = cards_area.h
        for i, c in enumerate(self.cards):
            r = pygame.Rect(cards_area.x + i * (card_w + gap), cards_area.y, card_w, card_h)
            sel = i == self.selected_index
            pygame.draw.rect(surface, UI_THEME["panel"], r, border_radius=10)
            pygame.draw.rect(surface, UI_THEME["gold"] if sel else UI_THEME["accent_violet"], r, 3 if sel else 1, border_radius=10)
            name_key = getattr(getattr(c, "definition", None), "name_key", getattr(c, "id", "Carta"))
            name = app.loc.t(name_key)
            txt = app.tiny_font.render(name[:24], True, UI_THEME["text"])
            surface.blit(txt, (r.x + 8, r.y + 10))
            cost = getattr(c, "cost", getattr(getattr(c, "definition", None), "cost", 0))
            surface.blit(app.tiny_font.render(f"Coste {cost}", True, UI_THEME["energy"]), (r.x + 8, r.y + 34))
            tag = "SE QUEDA ARRIBA" if sel else ""
            if tag:
                surface.blit(app.tiny_font.render(tag, True, UI_THEME["good"]), (r.x + 8, r.bottom - 24))

        pygame.draw.rect(surface, UI_THEME["violet"], confirm, border_radius=10)
        pygame.draw.rect(surface, UI_THEME["panel_2"], cancel, border_radius=10)
        surface.blit(app.small_font.render("Confirmar", True, UI_THEME["text"]), (confirm.x + 54, confirm.y + 14))
        surface.blit(app.small_font.render("Cancelar", True, UI_THEME["text"]), (cancel.x + 62, cancel.y + 14))
