from __future__ import annotations

import pygame


class BiomeGenerator:
    """Generate biome identity panels and sigils."""

    PALETTES = {
        'ukhu_pacha': ((10, 8, 22), (52, 34, 86), (118, 86, 182)),
        'kay_pacha': ((18, 14, 30), (74, 42, 112), (96, 198, 226)),
        'hanan_pacha': ((20, 22, 38), (90, 82, 146), (230, 196, 126)),
        'fractura_chakana': ((8, 6, 14), (88, 42, 102), (180, 242, 255)),
    }

    ALIASES = {
        'ukhu': 'ukhu_pacha',
        'kay': 'kay_pacha',
        'kaypacha': 'kay_pacha',
        'hanan': 'hanan_pacha',
        'fractura': 'fractura_chakana',
        'fractura_de_la_chakana': 'fractura_chakana',
        'umbral': 'ukhu_pacha',
        'forest': 'ukhu_pacha',
    }

    def _palette(self, biome_id: str):
        b = str(biome_id or 'kay_pacha').lower()
        b = self.ALIASES.get(b, b)
        return self.PALETTES.get(b, self.PALETTES['kay_pacha'])

    def render_panel(self, biome_id: str, size: tuple[int, int], motif: str = 'bg') -> pygame.Surface:
        w, h = max(48, int(size[0])), max(48, int(size[1]))
        c0, c1, c2 = self._palette(biome_id)
        s = pygame.Surface((w, h), pygame.SRCALPHA)

        for y in range(h):
            p = y / max(1, h - 1)
            col = (
                int(c0[0] + (c1[0] - c0[0]) * p),
                int(c0[1] + (c1[1] - c0[1]) * p),
                int(c0[2] + (c1[2] - c0[2]) * p),
            )
            pygame.draw.line(s, col, (0, y), (w, y))

        if motif in {'bg', 'mg'}:
            pygame.draw.circle(s, (*c2, 34), (w // 2, h // 2), int(min(w, h) * 0.28), max(1, w // 80))
            pygame.draw.line(s, (*c2, 58), (w // 2, int(h * 0.12)), (w // 2, int(h * 0.88)), max(1, w // 130))
            pygame.draw.line(s, (*c2, 58), (int(w * 0.12), h // 2), (int(w * 0.88), h // 2), max(1, w // 130))
        if motif in {'sigil', 'fg'}:
            pygame.draw.polygon(s, c2, [(w // 2, int(h * 0.16)), (int(w * 0.84), h // 2), (w // 2, int(h * 0.84)), (int(w * 0.16), h // 2)], max(1, w // 84))
        return s
