"""High-level reusable Chakana widgets."""

from __future__ import annotations

import pygame

from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.pixel_icons import draw_icon_with_value

from .colors import UColors
from .components import UILabel, UIPanel, UIBar, UIOrbRow


class CardPreviewWidget:
    def render(self, surface: pygame.Surface, rect: pygame.Rect, app, card):
        UIPanel(rect, variant="alt").draw(surface)
        if card is None:
            return
        art = app.assets.sprite("cards", card.definition.id, (rect.w - 20, int(rect.h * 0.58)), fallback=(88, 66, 120))
        surface.blit(art, (rect.x + 10, rect.y + 10))
        summary = summarize_card_effect(card.definition, card_instance=card, ctx=None)
        title = UILabel.clamp(app.loc.t(card.definition.name_key), app.small_font, rect.w - 20)
        surface.blit(app.small_font.render(title, True, UColors.TEXT), (rect.x + 10, rect.y + int(rect.h * 0.60)))
        x = rect.x + 12
        for icon_name, val in [(k, v) for k, v in (summary.get("key_stats") or [])[:3]]:
            x = draw_icon_with_value(surface, icon_name, val, UColors.HARMONY, app.tiny_font, x, rect.y + int(rect.h * 0.70), size=1)


class DeckGeometryWidget:
    def render(self, surface: pygame.Surface, rect: pygame.Rect, app, profile: dict):
        UIPanel(rect, title="Geometria", variant="alt").draw(surface, app.tiny_font)
        keys = ["attack", "defense", "control", "ritual", "tempo", "harmony"]
        center = (rect.centerx, rect.centery + 10)
        radius = min(rect.w, rect.h) // 3
        pts = []
        for i, k in enumerate(keys):
            a = -1.57 + (6.283 * i / len(keys))
            v = max(0.0, min(1.0, float(profile.get(k, 0)) / 5.0))
            pts.append((center[0] + int(radius * v * pygame.math.Vector2(1, 0).rotate_rad(a).x), center[1] + int(radius * v * pygame.math.Vector2(1, 0).rotate_rad(a).y)))
        for ring in range(1, 4):
            pygame.draw.circle(surface, UColors.BORDER_SOFT, center, int(radius * ring / 3), 1)
        pygame.draw.polygon(surface, (*UColors.BORDER, 86), pts)
        pygame.draw.polygon(surface, UColors.BORDER, pts, 2)


class EnemyIntentWidget:
    def render(self, surface: pygame.Surface, rect: pygame.Rect, app, intent_text: str, boss: bool = False):
        UIPanel(rect, variant="alt").draw(surface)
        col = UColors.WARNING if boss else UColors.TEXT
        txt = UILabel.clamp(intent_text, app.small_font, rect.w - 12)
        surface.blit(app.small_font.render(txt, True, col), (rect.x + 6, rect.y + 6))


class ChakanaStatusWidget:
    def render(self, surface: pygame.Surface, rect: pygame.Rect, app, player: dict, piles: dict, turn: int, fatigue: int, energy_cap: int):
        UIPanel(rect).draw(surface)
        hp = int(player.get("hp", 0))
        max_hp = int(player.get("max_hp", 1))
        energy = int(player.get("energy", 0))
        harmony = int(player.get("harmony_current", 0))
        hmax = int(player.get("harmony_max", 1))
        hthr = int(player.get("harmony_ready_threshold", 6))

        surface.blit(app.tiny_font.render("Vitalidad", True, UColors.MUTED), (rect.x + 10, rect.y + 8))
        surface.blit(app.small_font.render(f"{hp}/{max_hp}", True, UColors.HP), (rect.x + 10, rect.y + 24))
        UIBar(pygame.Rect(rect.x + 10, rect.y + 48, rect.w - 20, 8), hp, max_hp, UColors.HP).draw(surface)

        surface.blit(app.tiny_font.render(f"Turno {turn}", True, UColors.HARMONY), (rect.x + 10, rect.y + 64))
        surface.blit(app.tiny_font.render(f"Mazo {piles.get('draw',0)}  Mano {piles.get('hand',0)}  Ecos {piles.get('discard',0)}", True, UColors.MUTED), (rect.x + 10, rect.y + 84))
        surface.blit(app.tiny_font.render(f"Armonia {harmony}/{hmax}  Umbral {hthr}  Desgaste {fatigue}", True, UColors.LORE), (rect.x + 10, rect.y + 102))
        UIOrbRow(rect.x + 12, rect.y + 128, max(3, min(8, energy_cap)), energy, UColors.ENERGY).draw(surface)


class CombatFeedWidget:
    def render(self, surface: pygame.Surface, rect: pygame.Rect, app, entries: list[str], enemy_line: str = "", hero_line: str = ""):
        UIPanel(rect, variant="alt").draw(surface)
        y = rect.y + 8
        if enemy_line:
            surface.blit(app.tiny_font.render(UILabel.clamp(enemy_line, app.tiny_font, rect.w - 16), True, (244, 154, 172)), (rect.x + 8, y))
            y += 18
        if hero_line:
            surface.blit(app.tiny_font.render(UILabel.clamp(hero_line, app.tiny_font, rect.w - 16), True, (170, 240, 198)), (rect.x + 8, y))
            y += 18
        for e in entries[-4:]:
            surface.blit(app.tiny_font.render(UILabel.clamp(f"- {e}", app.tiny_font, rect.w - 16), True, UColors.FEED), (rect.x + 8, y))
            y += 16
