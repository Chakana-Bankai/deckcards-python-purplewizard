from __future__ import annotations

import pygame

from .icon_generator import IconGenerator


class RelicGenerator:
    """Generate relic identity visuals with rarity framing."""

    RARITY_COLORS = {
        'common': (146, 136, 176),
        'rare': (116, 186, 228),
        'major': (218, 176, 88),
        'legendary': (244, 210, 126),
    }

    def __init__(self):
        self.icon_gen = IconGenerator()

    def render(self, relic_id: str, rarity: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(48, int(size[0])), max(48, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        rarity_key = str(rarity or 'common').lower()
        col = self.RARITY_COLORS.get(rarity_key, self.RARITY_COLORS['common'])

        pygame.draw.rect(s, (24, 18, 38), (0, 0, w, h), border_radius=max(4, w // 18))
        pygame.draw.rect(s, col, (0, 0, w, h), max(1, w // 32), border_radius=max(4, w // 18))
        pygame.draw.circle(s, (*col, 52), (w // 2, h // 2), int(min(w, h) * 0.34))

        icon_name = 'relic'
        rid = str(relic_id or '').lower()
        if 'seal' in rid:
            icon_name = 'ritual'
        elif 'void' in rid:
            icon_name = 'rupture'
        elif 'solar' in rid or 'gold' in rid:
            icon_name = 'gold'

        icon = self.icon_gen.render(icon_name, (int(w * 0.42), int(h * 0.42)), color=col)
        s.blit(icon, icon.get_rect(center=(w // 2, h // 2)).topleft)

        # Geometry support.
        pygame.draw.line(s, col, (w // 2, int(h * 0.08)), (w // 2, int(h * 0.92)), max(1, w // 56))
        pygame.draw.line(s, col, (int(w * 0.08), h // 2), (int(w * 0.92), h // 2), max(1, w // 56))
        return s
