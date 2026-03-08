from __future__ import annotations

import math
import pygame


class AvatarGenerator:
    """Generate Chakana avatar variants with readable silhouettes."""

    PALETTE = {
        'void': (14, 10, 26),
        'robe': (86, 50, 146),
        'robe_dark': (56, 32, 100),
        'gold': (230, 196, 116),
        'cyan': (112, 214, 235),
        'skin': (198, 156, 128),
        'staff': (120, 86, 64),
    }

    def render(self, variant: str, size: tuple[int, int], seed: int = 0) -> pygame.Surface:
        w, h = max(32, int(size[0])), max(32, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        px = max(1, w // 96)

        cx = w // 2
        ground = int(h * 0.86)

        # Aura / identity halo.
        pygame.draw.circle(s, (*self.PALETTE['cyan'], 44), (cx, int(h * 0.38)), int(min(w, h) * 0.28))
        pygame.draw.circle(s, (*self.PALETTE['gold'], 30), (cx, int(h * 0.42)), int(min(w, h) * 0.22), max(1, px))

        # Robe body.
        robe = [(cx, int(h * 0.25)), (int(w * 0.24), ground), (int(w * 0.76), ground)]
        pygame.draw.polygon(s, self.PALETTE['robe'], robe)
        pygame.draw.polygon(s, self.PALETTE['robe_dark'], robe, max(1, px))

        # Hat.
        hat = [(cx, int(h * 0.06)), (int(w * 0.34), int(h * 0.33)), (int(w * 0.66), int(h * 0.33))]
        pygame.draw.polygon(s, self.PALETTE['robe_dark'], hat)
        pygame.draw.polygon(s, self.PALETTE['gold'], hat, max(1, px))

        # Face.
        pygame.draw.circle(s, self.PALETTE['skin'], (cx, int(h * 0.37)), int(min(w, h) * 0.08))
        pygame.draw.circle(s, self.PALETTE['void'], (cx - 4 * px, int(h * 0.37)), max(1, px))
        pygame.draw.circle(s, self.PALETTE['void'], (cx + 4 * px, int(h * 0.37)), max(1, px))

        # Staff.
        sx = int(w * 0.74)
        pygame.draw.line(s, self.PALETTE['staff'], (sx, int(h * 0.34)), (sx, int(h * 0.82)), max(2, px + 1))
        pygame.draw.circle(s, self.PALETTE['gold'], (sx, int(h * 0.30)), max(3, px * 3))
        pygame.draw.circle(s, self.PALETTE['cyan'], (sx, int(h * 0.30)), max(1, px + 1), max(1, px))

        # Chakana symbol on chest.
        ccx, ccy = cx, int(h * 0.56)
        rr = max(4, int(min(w, h) * 0.06))
        pygame.draw.rect(s, self.PALETTE['gold'], (ccx - rr // 2, ccy - rr // 2, rr, rr), max(1, px))
        pygame.draw.line(s, self.PALETTE['gold'], (ccx - rr, ccy), (ccx + rr, ccy), max(1, px))
        pygame.draw.line(s, self.PALETTE['gold'], (ccx, ccy - rr), (ccx, ccy + rr), max(1, px))

        # Variant accents.
        v = str(variant or 'combat_hud').lower()
        if 'victory' in v:
            pygame.draw.circle(s, (*self.PALETTE['gold'], 50), (cx, int(h * 0.24)), int(min(w, h) * 0.18), max(1, px))
        elif 'defeat' in v:
            shade = pygame.Surface((w, h), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 58))
            s.blit(shade, (0, 0))
        elif 'menu' in v:
            pygame.draw.arc(s, self.PALETTE['cyan'], (int(w * 0.18), int(h * 0.18), int(w * 0.64), int(h * 0.64)), 0.2, math.pi - 0.2, max(1, px))
        return s
