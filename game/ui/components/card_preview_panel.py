from __future__ import annotations

import pygame

from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.theme import UI_THEME


class CardPreviewPanel:
    def __init__(self, app):
        self.app = app

    def _wrap(self, font, text: str, width: int, max_lines: int = 8):
        words = str(text or "").split()
        out = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if font.size(cand)[0] <= width:
                cur = cand
            else:
                if cur:
                    out.append(cur)
                cur = w
                if len(out) >= max_lines:
                    break
        if cur and len(out) < max_lines:
            out.append(cur)
        return out

    def _payload(self, card):
        if card is None:
            return None, None
        if hasattr(card, "definition"):
            payload = {
                "id": getattr(card.definition, "id", "carta"),
                "name_key": getattr(card.definition, "name_key", "carta"),
                "text_key": getattr(card.definition, "text_key", ""),
                "rarity": getattr(card.definition, "rarity", "common"),
                "cost": getattr(card, "cost", getattr(card.definition, "cost", 0)),
                "tags": list(getattr(card.definition, "tags", []) or []),
                "effects": list(getattr(card.definition, "effects", []) or []),
            }
            return payload, card
        return card, None

    def render(self, surface: pygame.Surface, rect: pygame.Rect, card):
        pygame.draw.rect(surface, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], rect, 2, border_radius=12)

        payload, inst = self._payload(card)
        if not payload:
            surface.blit(self.app.small_font.render("Previsualización de carta", True, UI_THEME["gold"]), (rect.x + 16, rect.y + 14))
            surface.blit(self.app.small_font.render("Pasa el cursor sobre una carta.", True, UI_THEME["muted"]), (rect.x + 16, rect.y + 50))
            return

        name = self.app.loc.t(payload.get("name_key", payload.get("id", "Carta")))
        desc = self.app.loc.t(payload.get("text_key", ""))
        summary = summarize_card_effect(payload, card_instance=inst, ctx=None)
        card_id = payload.get("id", "")
        art_rect = pygame.Rect(rect.x + 16, rect.y + 54, 260, 360)
        art = self.app.assets.sprite("cards", card_id, (art_rect.w, art_rect.h), fallback=(76, 46, 110))
        surface.blit(art, art_rect.topleft)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], art_rect, 2, border_radius=8)

        tx = art_rect.right + 18
        max_w = rect.right - tx - 14
        y = rect.y + 18
        for ln in self._wrap(self.app.small_font, name, max_w, 2):
            surface.blit(self.app.small_font.render(ln, True, UI_THEME["gold"]), (tx, y))
            y += 24

        meta = f"Coste {payload.get('cost', 0)}  •  Tipo {summary.get('type','-')}"
        surface.blit(self.app.tiny_font.render(meta, True, UI_THEME["energy"]), (tx, y))
        y += 22

        rarity = str(payload.get("rarity", "common"))
        rarity_es = {"common": "Común", "uncommon": "Rara", "rare": "Épica", "legendary": "Legendaria", "basic": "Común"}.get(rarity, rarity.title())
        surface.blit(self.app.tiny_font.render(f"Rareza: {rarity_es}", True, UI_THEME["muted"]), (tx, y))
        y += 24

        for line in summary.get("lines", [])[:5]:
            for w in self._wrap(self.app.tiny_font, f"• {line}", max_w, 2):
                surface.blit(self.app.tiny_font.render(w, True, UI_THEME["text"]), (tx, y))
                y += 18

        y += 4
        for ln in self._wrap(self.app.tiny_font, desc, max_w, 5):
            if y > rect.bottom - 26:
                break
            surface.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (tx, y))
            y += 18
