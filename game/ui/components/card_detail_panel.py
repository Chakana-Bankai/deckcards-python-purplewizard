from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class CardDetailPanel:
    def __init__(self, app):
        self.app = app

    def _get_payload(self, card):
        if card is None:
            return None
        if hasattr(card, "definition"):
            d = card.definition
            return {
                "id": getattr(d, "id", "-"),
                "name_key": getattr(d, "name_key", "-"),
                "text_key": getattr(d, "text_key", "-"),
                "cost": getattr(card, "cost", getattr(d, "cost", 0)),
                "tags": list(getattr(d, "tags", []) or []),
                "effects": list(getattr(d, "effects", []) or []),
                "family": getattr(d, "family", "-")
            }
        if isinstance(card, dict):
            return {
                "id": card.get("id", "-"),
                "name_key": card.get("name_key", card.get("id", "-")),
                "text_key": card.get("text_key", "-"),
                "cost": card.get("cost", 0),
                "tags": list(card.get("tags", []) or []),
                "effects": list(card.get("effects", []) or []),
                "family": card.get("family", "-")
            }
        return None

    def _kpis(self, payload):
        dmg = blk = rup = en = 0
        for ef in payload.get("effects", []):
            if not isinstance(ef, dict):
                continue
            typ = ef.get("type", "")
            amt = int(ef.get("amount", 0))
            if typ == "damage":
                dmg += amt
            elif typ == "block":
                blk += amt
            elif typ == "rupture":
                rup += amt
            elif typ == "energy":
                en += amt
        return dmg, blk, rup, en

    def render(self, surface: pygame.Surface, rect: pygame.Rect, card=None, placeholder_text: str | None = None, last_played: str | None = None):
        pygame.draw.rect(surface, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        surface.blit(self.app.small_font.render("Detalle", True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))
        payload = self._get_payload(card)
        if not payload:
            msg = placeholder_text or "Selecciona una carta para ver sus detalles."
            surface.blit(self.app.font.render(msg, True, UI_THEME["muted"]), (rect.x + 16, rect.y + 44))
            if last_played:
                surface.blit(self.app.tiny_font.render(f"Última jugada: {last_played}", True, UI_THEME["text"]), (rect.x + 16, rect.y + 76))
            return

        tx = rect.x + 16
        y = rect.y + 42
        surface.blit(self.app.small_font.render(self.app.loc.t(payload["name_key"]), True, UI_THEME["text"]), (tx, y)); y += 26
        surface.blit(self.app.tiny_font.render(f"Tipo: {payload.get('family','-')}", True, UI_THEME["muted"]), (tx, y)); y += 20
        surface.blit(self.app.tiny_font.render(f"Coste: {payload.get('cost',0)}", True, UI_THEME["energy"]), (tx, y)); y += 20

        dmg, blk, rup, _en = self._kpis(payload)
        surface.blit(self.app.tiny_font.render(f"Daño: {dmg}", True, UI_THEME["text"]), (tx, y)); y += 18
        surface.blit(self.app.tiny_font.render(f"Bloqueo: {blk}", True, UI_THEME["text"]), (tx, y)); y += 18
        surface.blit(self.app.tiny_font.render(f"Ruptura: {rup}", True, UI_THEME["text"]), (tx, y)); y += 18

        tags = ", ".join(payload.get("tags", [])) or "-"
        tag_line = f"Tags: {tags}"
        while self.app.tiny_font.size(tag_line)[0] > rect.w - 30 and len(tag_line) > 6:
            tag_line = tag_line[:-4] + "..."
        if y <= rect.bottom - 24:
            surface.blit(self.app.tiny_font.render(tag_line, True, UI_THEME["muted"]), (tx, min(y + 6, rect.bottom - 24)))
