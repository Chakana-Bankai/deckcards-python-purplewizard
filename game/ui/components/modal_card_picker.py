from __future__ import annotations

import pygame

from game.ui.system.modals import CardGridModal


class ModalCardPicker:
    def __init__(self):
        self.open = False
        self.title = "Prever"
        self.help_text = "Mira cartas, elige 1 para mantener arriba y el resto ira al descarte."
        self.cards = []
        self.selected_index = None
        self.hover_index = None
        self.required_selections = 1
        self.on_confirm = None
        self.on_cancel = None
        self._modal = CardGridModal()

    def _sync_from_modal(self):
        self.open = self._modal.open
        self.cards = list(self._modal.cards)
        self.selected_index = self._modal.selected_index
        self.hover_index = self._modal.hover_index

    def _sync_to_modal(self):
        self._modal.title = self.title
        self._modal.message = self.help_text
        self._modal.confirm_label = "Confirmar"
        self._modal.cancel_label = "Cancelar"

    def show(self, cards, on_confirm=None, on_cancel=None, required_selections: int = 1):
        self.required_selections = max(1, int(required_selections or 1))
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self._modal.show_cards(self.title, self.help_text, list(cards or []), on_confirm=self._confirm, on_cancel=self._cancel)
        self._sync_from_modal()

    def close(self):
        self._modal.hide()
        self.cards = []
        self.selected_index = None
        self.hover_index = None
        self.open = False

    def _confirm(self):
        card = self._modal.selected_card()
        cb = self.on_confirm
        self.close()
        if callable(cb):
            cb(card)

    def _cancel(self):
        cb = self.on_cancel
        self.close()
        if callable(cb):
            cb()

    def handle_event(self, event, mapped_pos):
        if not self._modal.open:
            self.open = False
            return False
        surface = pygame.display.get_surface()
        if surface is None:
            return False
        self._sync_to_modal()
        used = self._modal.handle_event(event, mapped_pos, surface)
        self._sync_from_modal()
        return used

    def render(self, surface, app):
        if not self._modal.open:
            self.open = False
            return
        self._sync_to_modal()
        self._modal.render(surface, app)
        self._sync_from_modal()
