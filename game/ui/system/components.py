"""Reusable low-level UI components for Chakana screens."""

from __future__ import annotations

import pygame

from .brand import ChakanaBrand
from .colors import UColors


class UIPanel:
    def __init__(self, rect: pygame.Rect, title: str | None = None, variant: str = "default"):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.variant = variant

    def draw(self, surface: pygame.Surface, title_font: pygame.font.Font | None = None):
        fill = UColors.PANEL_ALT if self.variant == "alt" else UColors.PANEL
        pygame.draw.rect(surface, fill, self.rect, border_radius=ChakanaBrand.BORDER_RADIUS)
        pygame.draw.rect(surface, UColors.BORDER, self.rect, ChakanaBrand.PANEL_BORDER_WIDTH, border_radius=ChakanaBrand.BORDER_RADIUS)
        if self.title and title_font is not None:
            txt = title_font.render(self.title, True, UColors.TEXT)
            surface.blit(txt, (self.rect.x + ChakanaBrand.PANEL_PADDING, self.rect.y + 6))


class UIButton:
    def __init__(self, rect: pygame.Rect, label: str, role: str = "default", premium: bool = False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.role = role
        self.premium = premium
        self.disabled = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, hovered: bool = False, pressed: bool = False):
        role_col = UColors.ROLE.get(self.role, UColors.BORDER)
        accent = UColors.HARMONY

        # Premium buttons keep dark ritual base; accent is used for selection/highlight only.
        base = UColors.PANEL if self.premium else UColors.PANEL_ALT
        border = role_col if self.role in {"execute", "seal", "end_turn", "invalid"} else UColors.BORDER_SOFT

        if self.disabled:
            base = (64, 54, 86)
            border = UColors.BORDER_SOFT
        elif hovered:
            base = tuple(min(255, c + 10) for c in base)
            border = accent
        if pressed and not self.disabled:
            base = tuple(max(0, c - 16) for c in base)

        pygame.draw.rect(surface, base, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=10)
        label = font.render(self.label, True, UColors.TEXT)
        surface.blit(label, label.get_rect(center=self.rect.center))


class UILabel:
    @staticmethod
    def clamp(text: str, font: pygame.font.Font, width: int) -> str:
        out = str(text or "")
        while font.size(out)[0] > width and len(out) > 4:
            out = out[:-4] + "..."
        return out

    @staticmethod
    def wrap(text: str, font: pygame.font.Font, width: int, max_lines: int = 2) -> list[str]:
        words = str(text or "").split()
        lines, cur = [], ""
        for w in words:
            cand = (cur + " " + w).strip()
            if font.size(cand)[0] <= width:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
                if len(lines) >= max_lines:
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        return lines


class UIBar:
    def __init__(self, rect: pygame.Rect, value: int, max_value: int, color: tuple[int, int, int]):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.max_value = max(1, max_value)
        self.color = color

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (26, 22, 38), self.rect, border_radius=5)
        w = int(self.rect.w * max(0.0, min(1.0, self.value / self.max_value)))
        pygame.draw.rect(surface, self.color, pygame.Rect(self.rect.x, self.rect.y, w, self.rect.h), border_radius=5)


class UIOrbRow:
    def __init__(self, x: int, y: int, count: int, filled: int, color: tuple[int, int, int]):
        self.x = x
        self.y = y
        self.count = max(0, count)
        self.filled = max(0, filled)
        self.color = color

    def draw(self, surface: pygame.Surface):
        for i in range(self.count):
            cx = self.x + i * 18
            alpha = 220 if i < self.filled else 72
            pygame.draw.circle(surface, (*self.color, alpha), (cx, self.y), 6)
            pygame.draw.circle(surface, UColors.BORDER_SOFT, (cx, self.y), 6, 1)


class UITooltip:
    def __init__(self, rect: pygame.Rect, text: str):
        self.rect = pygame.Rect(rect)
        self.text = text

    def clamp_to_surface(self, surface: pygame.Surface):
        self.rect.x = max(8, min(surface.get_width() - self.rect.w - 8, self.rect.x))
        self.rect.y = max(8, min(surface.get_height() - self.rect.h - 8, self.rect.y))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        self.clamp_to_surface(surface)
        pygame.draw.rect(surface, UColors.PANEL, self.rect, border_radius=8)
        pygame.draw.rect(surface, UColors.BORDER, self.rect, 1, border_radius=8)
        txt = font.render(UILabel.clamp(self.text, font, self.rect.w - 12), True, UColors.TEXT)
        surface.blit(txt, (self.rect.x + 6, self.rect.y + 6))
