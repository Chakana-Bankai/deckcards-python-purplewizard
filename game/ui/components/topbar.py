from __future__ import annotations

import pygame

from game.ui.theme import UI_THEME


class CombatTopBar:
    def render(self, surface: pygame.Surface, app, layout, left: str, center: str, subtitle: str, timer_text: str, turn_text: str):
        pygame.draw.rect(surface, UI_THEME["panel"], layout.topbar_rect)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], layout.topbar_rect, 2)
        surface.blit(app.small_font.render(left, True, UI_THEME["gold"]), (layout.topbar_left.x + 16, layout.topbar_left.y + 16))

        center_main = app.small_font.render(center, True, UI_THEME["text"])
        surface.blit(center_main, center_main.get_rect(center=(layout.topbar_center.centerx, layout.topbar_center.y + 22)))
        center_sub = app.tiny_font.render((subtitle or "Sin narración disponible.")[:86], True, UI_THEME["muted"])
        surface.blit(center_sub, center_sub.get_rect(center=(layout.topbar_center.centerx, layout.topbar_center.y + 48)))

        timer_main = app.font.render(timer_text, True, UI_THEME["text"])
        turn_sub = app.tiny_font.render(turn_text, True, UI_THEME["gold"])
        timer_x = layout.topbar_right.right - timer_main.get_width() - 16
        surface.blit(timer_main, (timer_x, layout.topbar_right.y + 10))
        surface.blit(turn_sub, (layout.topbar_right.right - turn_sub.get_width() - 16, layout.topbar_right.y + 44))


class MapTopBar:
    def render(self, surface: pygame.Surface, app, topbar: pygame.Rect, left: str, center: str, subtitle: str, right: str):
        pygame.draw.rect(surface, UI_THEME["panel"], topbar, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], topbar, 2, border_radius=12)

        surface.blit(app.small_font.render(left, True, UI_THEME["gold"]), (topbar.x + 14, topbar.y + 12))

        center_main = app.small_font.render(center, True, UI_THEME["text"])
        surface.blit(center_main, center_main.get_rect(center=(topbar.centerx, topbar.y + 24)))

        center_sub = app.tiny_font.render((subtitle or "Sin narración disponible.")[:104], True, UI_THEME["muted"])
        surface.blit(center_sub, center_sub.get_rect(center=(topbar.centerx, topbar.y + 50)))

        right_txt = app.small_font.render(right, True, UI_THEME["gold"])
        surface.blit(right_txt, (topbar.right - right_txt.get_width() - 14, topbar.y + 12))
