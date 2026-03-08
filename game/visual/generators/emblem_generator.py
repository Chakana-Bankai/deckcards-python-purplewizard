from __future__ import annotations

import pygame

from .icon_generator import IconGenerator


class EmblemGenerator:
    """Generate archetype emblem and badge versions."""

    ARCHETYPE = {
        'cosmic_warrior': ('damage', (214, 86, 132)),
        'harmony_guardian': ('block', (126, 198, 180)),
        'oracle_of_fate': ('scry', (168, 140, 244)),
    }

    def __init__(self):
        self.icon_gen = IconGenerator()

    def render(self, archetype_id: str, size: tuple[int, int], mini: bool = False) -> pygame.Surface:
        w, h = max(24, int(size[0])), max(24, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        key = str(archetype_id or 'cosmic_warrior').lower()
        icon_name, col = self.ARCHETYPE.get(key, ('ritual', (180, 150, 230)))

        pygame.draw.rect(s, (20, 16, 32), (0, 0, w, h), border_radius=max(4, w // 10))
        pygame.draw.rect(s, col, (0, 0, w, h), max(1, w // 28), border_radius=max(4, w // 10))
        icon_size = int(min(w, h) * (0.48 if mini else 0.56))
        icon = self.icon_gen.render(icon_name, (icon_size, icon_size), color=col)
        s.blit(icon, icon.get_rect(center=(w // 2, h // 2)).topleft)
        return s
