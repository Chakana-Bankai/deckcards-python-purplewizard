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
    def render(self, surface: pygame.Surface, app, left_rect: pygame.Rect, center_rect: pygame.Rect, right_rect: pygame.Rect, left: str, center: str, subtitle: str, timer_text: str, turn_text: str):
        topbar = left_rect.unionall([center_rect, right_rect]).inflate(20, 8)
        pygame.draw.rect(surface, UI_THEME["panel"], topbar, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], topbar, 2, border_radius=12)

        surface.blit(app.small_font.render(left, True, UI_THEME["gold"]), (left_rect.x + 6, left_rect.y + 14))
        center_main = app.small_font.render(center, True, UI_THEME["text"])
        surface.blit(center_main, center_main.get_rect(center=(center_rect.centerx, center_rect.y + 22)))
        center_sub = app.tiny_font.render((subtitle or "Sin narración disponible.")[:86], True, UI_THEME["muted"])
        surface.blit(center_sub, center_sub.get_rect(center=(center_rect.centerx, center_rect.y + 48)))
        timer_main = app.font.render(timer_text, True, UI_THEME["text"])
        turn_sub = app.tiny_font.render(turn_text, True, UI_THEME["gold"])
        surface.blit(timer_main, (right_rect.right - timer_main.get_width() - 8, right_rect.y + 8))
        surface.blit(turn_sub, (right_rect.right - turn_sub.get_width() - 8, right_rect.y + 42))
