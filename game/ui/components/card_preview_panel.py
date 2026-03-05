from __future__ import annotations

import pygame

from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.theme import UI_THEME


class CardPreviewPanel:
    def __init__(self, rect=None, fonts=None, theme=None, app=None):
        self.rect = rect
        self.fonts = fonts or {}
        self.theme = theme or UI_THEME
        self.app = app
        self._card = None
        self._summary = None
        self._art = None

    def set_card(self, card_instance_or_def, summary_dict=None, art_surface=None):
        self._card = card_instance_or_def
        self._summary = summary_dict
        self._art = art_surface

    def clear(self):
        self._card = None
        self._summary = None
        self._art = None

    def _font(self, name):
        if name in self.fonts:
            return self.fonts[name]
        if self.app is None:
            return None
        return {
            "title": self.app.small_font,
            "body": self.app.tiny_font,
            "small": self.app.tiny_font,
        }.get(name, self.app.tiny_font)

    def _placeholder_art(self, w: int, h: int):
        surf = pygame.Surface((max(32, int(w)), max(32, int(h))), pygame.SRCALPHA)
        surf.fill((34, 24, 52))
        pygame.draw.rect(surf, self.theme.get("accent_violet", (120, 80, 170)), surf.get_rect(), 2, border_radius=8)
        if self.app is not None:
            txt = self.app.small_font.render("✦", True, self.theme.get("gold", (220, 190, 110)))
            surf.blit(txt, txt.get_rect(center=surf.get_rect().center))
        return surf

    def set_card_safe(self, card, app=None, ctx=None):
        _ = ctx
        if app is not None:
            self.app = app
        if card is None:
            self.clear()
            return
        try:
            payload, inst = self._payload(card)
            if payload is None:
                self.clear()
                return
            summary = summarize_card_effect(payload, card_instance=inst, ctx=None)
            art = None
            if self.app is not None:
                cid = payload.get("id", "")
                art = self.app.assets.sprite("cards", cid, (320, 220), fallback=(76, 46, 110))
            self.set_card(card, summary_dict=summary, art_surface=art)
        except Exception:
            self.clear()

    def _wrap(self, font, text: str, width: int, max_lines: int = 6):
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

    def _icon_row(self, summary: dict):
        stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
        icon_data = []
        if stats.get("damage", 0) > 0:
            icon_data.append(("⚔", stats.get("damage", 0)))
        if stats.get("block", 0) > 0:
            icon_data.append(("🛡", stats.get("block", 0)))
        if stats.get("rupture", 0) > 0:
            icon_data.append(("🔥", stats.get("rupture", 0)))
        if stats.get("harmony", 0) > 0:
            icon_data.append(("✦", stats.get("harmony", 0)))
        if stats.get("scry", 0) > 0:
            icon_data.append(("🔮", stats.get("scry", 0)))
        if stats.get("draw", 0) > 0:
            icon_data.append(("📜", stats.get("draw", 0)))
        if stats.get("energy", 0) > 0:
            icon_data.append(("⚡", stats.get("energy", 0)))
        return icon_data[:3]

    def render(self, surface: pygame.Surface, rect: pygame.Rect | None = None, card=None, app=None):
        try:
            if app is not None:
                self.app = app
            if rect is None:
                rect = self.rect
            if rect is None:
                return
            if card is not None:
                self.set_card_safe(card, app=self.app)

            pygame.draw.rect(surface, self.theme["panel"], rect, border_radius=12)
            pygame.draw.rect(surface, self.theme["accent_violet"], rect, 2, border_radius=12)

            title_font = self._font("title")
            body_font = self._font("body")
            if title_font is None or body_font is None:
                return

            payload, inst = self._payload(self._card)
            if not payload:
                surface.blit(title_font.render("Previsualización", True, self.theme["gold"]), (rect.x + 14, rect.y + 12))
                surface.blit(body_font.render("Pasa el cursor sobre una carta.", True, self.theme["muted"]), (rect.x + 14, rect.y + 40))
                return

            summary = self._summary or summarize_card_effect(payload, card_instance=inst, ctx=None)
            name = self.app.loc.t(payload.get("name_key", payload.get("id", "Carta"))) if self.app else payload.get("id", "Carta")
            desc = self.app.loc.t(payload.get("text_key", "")) if self.app else payload.get("text_key", "")

            y = rect.y + 12
            max_w = rect.w - 24
            for line in self._wrap(title_font, name, max_w, 1):
                surface.blit(title_font.render(line, True, self.theme["gold"]), (rect.x + 12, y))
                y += 24

            icons = self._icon_row(summary)
            icon_txt = "   ".join([f"{g} {v}" for g, v in icons])
            meta = f"Coste {payload.get('cost',0)}"
            if icon_txt:
                meta += f"   {icon_txt}"
            surface.blit(body_font.render(meta, True, self.theme["energy"]), (rect.x + 12, y))
            y += 24

            art_rect = pygame.Rect(rect.x + 12, y, rect.w - 24, min(290, rect.h // 2))
            art = self._art
            if art is None and self.app:
                art = self.app.assets.sprite("cards", payload.get("id", ""), (art_rect.w, art_rect.h), fallback=(76, 46, 110))
            if art is not None:
                surface.blit(art, art_rect.topleft)
            pygame.draw.rect(surface, self.theme["accent_violet"], art_rect, 2, border_radius=8)

            y = art_rect.bottom + 10
            for line in (summary.get("lines", []) if isinstance(summary, dict) else [])[:4]:
                for w in self._wrap(body_font, f"• {line}", max_w, 2):
                    if y > rect.bottom - 56:
                        break
                    surface.blit(body_font.render(w, True, self.theme["text"]), (rect.x + 12, y))
                    y += 18

            tags = ", ".join(payload.get("tags", []))
            if tags and y <= rect.bottom - 36:
                surface.blit(body_font.render(f"Tags: {tags}", True, self.theme["muted"]), (rect.x + 12, y))
                y += 18

            if y <= rect.bottom - 20:
                for w in self._wrap(body_font, desc, max_w, 2):
                    if y > rect.bottom - 20:
                        break
                    surface.blit(body_font.render(w, True, self.theme["muted"]), (rect.x + 12, y))
                    y += 18
        except Exception:
            if rect is None:
                return
            pygame.draw.rect(surface, self.theme.get("panel", (30, 24, 44)), rect, border_radius=12)
            pygame.draw.rect(surface, self.theme.get("accent_violet", (120, 80, 170)), rect, 2, border_radius=12)
            if self.app is not None:
                surface.blit(self.app.small_font.render("Preview no disponible", True, self.theme.get("muted", (180, 170, 200))), (rect.x + 14, rect.y + 14))
