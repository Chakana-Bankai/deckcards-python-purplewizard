from __future__ import annotations

import pygame


class SacredOverlayGenerator:
    """Generate sacred geometry overlays for enemy/boss presentation."""

    COLORS = {
        'void': (166, 82, 210),
        'guardian': (120, 208, 184),
        'celestial': (226, 194, 126),
        'archon': (188, 228, 250),
    }

    def render(self, overlay_kind: str, size: tuple[int, int], alpha: int = 70) -> pygame.Surface:
        w, h = max(48, int(size[0])), max(48, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        col = self.COLORS.get(str(overlay_kind or 'void').lower(), self.COLORS['void'])
        c = (*col, max(20, min(180, int(alpha))))

        cx, cy = w // 2, h // 2
        r = int(min(w, h) * 0.42)
        pygame.draw.circle(s, c, (cx, cy), r, max(1, w // 120))
        pygame.draw.circle(s, c, (cx, cy), int(r * 0.62), max(1, w // 140))
        pygame.draw.line(s, c, (cx, cy - r), (cx, cy + r), max(1, w // 160))
        pygame.draw.line(s, c, (cx - r, cy), (cx + r, cy), max(1, w // 160))
        pygame.draw.polygon(s, c, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], max(1, w // 150))
        return s
