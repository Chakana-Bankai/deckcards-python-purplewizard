from __future__ import annotations

import pygame

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.system.icons import draw_icon_with_value, icon_for_effect
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
                "family": getattr(d, "family", "-"),
                "role": getattr(d, "role", ""),
            }
        if isinstance(card, dict):
            return {
                "id": card.get("id", "-"),
                "name_key": card.get("name_key", card.get("id", "-")),
                "text_key": card.get("text_key", "-"),
                "cost": card.get("cost", 0),
                "tags": list(card.get("tags", []) or []),
                "effects": list(card.get("effects", []) or []),
                "family": card.get("family", "-"),
                "role": card.get("role", ""),
            }
        return None

    def _wrap_clamp(self, font, text: str, width: int, max_lines: int):
        words = str(text or "").split()
        if not words:
            return [""]
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
                if len(lines) >= max_lines:
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)

        total_words = len(words)
        used_words = len(" ".join(lines).split())
        if used_words < total_words and lines:
            ell = "..."
            while font.size((lines[-1] + ell).strip())[0] > width and len(lines[-1]) > 1:
                lines[-1] = lines[-1][:-1]
            lines[-1] = lines[-1].rstrip(".") + ell
        return lines[:max_lines]

    def render(self, surface: pygame.Surface, rect: pygame.Rect, card=None, placeholder_text: str | None = None, last_played: str | None = None):
        pygame.draw.rect(surface, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        surface.blit(self.app.small_font.render("Detalle tactico", True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))
        payload = self._get_payload(card)
        if not payload:
            msg = placeholder_text or "Selecciona una carta para ver sus detalles."
            for i, line in enumerate(self._wrap_clamp(self.app.font, msg, rect.w - 32, 2)):
                surface.blit(self.app.font.render(line, True, UI_THEME["muted"]), (rect.x + 16, rect.y + 44 + i * 24))
            if last_played:
                surface.blit(self.app.tiny_font.render(f"Ultima jugada: {last_played}", True, UI_THEME["text"]), (rect.x + 16, rect.y + 96))
            return

        tx = rect.x + 16
        y = rect.y + 42
        max_w = rect.w - 30
        effects = [e for e in payload.get("effects", []) if isinstance(e, dict)]

        card_name = self.app.loc.t(payload["name_key"])
        for ln in self._wrap_clamp(self.app.small_font, card_name, max_w, 1):
            surface.blit(self.app.small_font.render(ln, True, UI_THEME["text"]), (tx, y))
            y += 24

        role = infer_card_role(payload)
        meta = f"Rol: {role.upper()}  |  Coste: {payload.get('cost',0)}"
        for ln in self._wrap_clamp(self.app.tiny_font, meta, max_w, 1):
            surface.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (tx, y))
            y += 20

        icons = []
        for ef in effects:
            icon = icon_for_effect(ef.get("type", ""))
            if icon == "unknown":
                continue
            amount = int(ef.get("amount", 1) or 1)
            icons.append((icon, max(1, amount)))
        # keep row readable
        unique_icons = []
        seen = set()
        for icon, val in icons:
            if icon in seen:
                continue
            seen.add(icon)
            unique_icons.append((icon, val))
        if unique_icons:
            x = tx
            for icon_name, val in unique_icons[:5]:
                x = draw_icon_with_value(surface, icon_name, val, UI_THEME["gold"], self.app.tiny_font, x, y - 2, size=1)
            y += 20

        summary = summarize_card_effect(payload, card_instance=card, ctx=None)
        header = str(summary.get("header") or "Efecto")
        for ln in self._wrap_clamp(self.app.tiny_font, header, max_w, 2):
            surface.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (tx, y))
            y += 18

        desc = self.app.loc.t(payload.get("text_key", ""))
        for ln in self._wrap_clamp(self.app.tiny_font, desc, max_w, 3):
            surface.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (tx, y))
            y += 18

        tags_txt = ", ".join(summary.get("tags", payload.get("tags", []))) or "-"
        tag_line = f"Etiquetas: {tags_txt}"
        for ln in self._wrap_clamp(self.app.tiny_font, tag_line, max_w, 1):
            if y <= rect.bottom - 24:
                surface.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (tx, y))

        if last_played:
            foot = self._wrap_clamp(self.app.tiny_font, f"Ultima jugada: {last_played}", max_w, 1)[0]
            surface.blit(self.app.tiny_font.render(foot, True, UI_THEME["muted"]), (tx, rect.bottom - 22))
