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

    def render(self, surface: pygame.Surface, rect: pygame.Rect, card=None):
        pygame.draw.rect(surface, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        surface.blit(self.app.small_font.render("Detalle", True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))
        payload = self._get_payload(card)
        if not payload:
            surface.blit(self.app.font.render("Selecciona una carta", True, UI_THEME["muted"]), (rect.x + 16, rect.y + 44))
            return

        art_w = max(120, int(rect.w * 0.42))
        art_h = max(96, int(rect.h * 0.40))
        art = self.app.assets.sprite("cards", payload["id"], (art_w, art_h), fallback=(70, 44, 105))
        surface.blit(art, (rect.x + 14, rect.y + 42))

        tx = rect.x + art_w + 28
        surface.blit(self.app.small_font.render(self.app.loc.t(payload["name_key"]), True, UI_THEME["text"]), (tx, rect.y + 42))
        surface.blit(self.app.tiny_font.render(f"Tipo: {payload.get('family','-')}", True, UI_THEME["muted"]), (tx, rect.y + 72))
        surface.blit(self.app.tiny_font.render(f"Coste: {payload.get('cost',0)}", True, UI_THEME["energy"]), (tx, rect.y + 94))

        dmg, blk, rup, en = self._kpis(payload)
        kpi = f"Daño {dmg}  Guardia {blk}  Ruptura {rup}  Energía {en}"
        surface.blit(self.app.tiny_font.render(kpi, True, UI_THEME["gold"]), (rect.x + 16, rect.y + art_h + 54))

        desc = self.app.loc.t(payload.get("text_key", "-"))
        y = rect.y + art_h + 82
        words = str(desc).split()
        cur = ""
        for w in words:
            nxt = (cur + " " + w).strip()
            if self.app.tiny_font.size(nxt)[0] <= rect.w - 30:
                cur = nxt
            else:
                surface.blit(self.app.tiny_font.render(cur, True, UI_THEME["text"]), (rect.x + 16, y))
                y += 18
                cur = w
            if y > rect.bottom - 52:
                break
        if cur and y <= rect.bottom - 52:
            surface.blit(self.app.tiny_font.render(cur, True, UI_THEME["text"]), (rect.x + 16, y))

        tags = ", ".join(payload.get("tags", [])) or "-"
        surface.blit(self.app.tiny_font.render(f"Tags: {tags}", True, UI_THEME["muted"]), (rect.x + 16, rect.bottom - 24))
