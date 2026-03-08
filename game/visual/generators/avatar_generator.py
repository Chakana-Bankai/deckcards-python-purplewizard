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
        ground = int(h * 0.88)

        # Aura halo with controlled glow.
        pygame.draw.circle(s, (*self.PALETTE['cyan'], 36), (cx, int(h * 0.36)), int(min(w, h) * 0.26))
        pygame.draw.circle(s, (*self.PALETTE['gold'], 24), (cx, int(h * 0.40)), int(min(w, h) * 0.20), max(1, px))

        # Robe silhouette.
        robe = [(cx, int(h * 0.24)), (int(w * 0.23), ground), (int(w * 0.77), ground)]
        pygame.draw.polygon(s, self.PALETTE['robe'], robe)
        pygame.draw.polygon(s, self.PALETTE['robe_dark'], robe, max(1, px))

        # Hat and brim for older sage silhouette.
        hat = [(cx, int(h * 0.05)), (int(w * 0.35), int(h * 0.31)), (int(w * 0.65), int(h * 0.31))]
        pygame.draw.polygon(s, self.PALETTE['robe_dark'], hat)
        pygame.draw.polygon(s, self.PALETTE['gold'], hat, max(1, px))
        brim = pygame.Rect(int(w * 0.31), int(h * 0.30), int(w * 0.38), max(2, int(h * 0.03)))
        pygame.draw.ellipse(s, self.PALETTE['robe_dark'], brim)
        pygame.draw.ellipse(s, self.PALETTE['gold'], brim, max(1, px))

        # Face: defined jaw/cheekbones, calm intense expression.
        face_cx, face_cy = cx, int(h * 0.38)
        frx, fry = max(4, int(w * 0.06)), max(4, int(h * 0.07))
        pygame.draw.ellipse(s, self.PALETTE['skin'], (face_cx - frx, face_cy - fry, frx * 2, fry * 2))
        cheek = (164, 124, 100)
        pygame.draw.line(s, cheek, (face_cx - frx + 2 * px, face_cy + 1 * px), (face_cx - 2 * px, face_cy + 4 * px), max(1, px))
        pygame.draw.line(s, cheek, (face_cx + frx - 2 * px, face_cy + 1 * px), (face_cx + 2 * px, face_cy + 4 * px), max(1, px))
        eye_col = self.PALETTE['void']
        brow_col = (58, 38, 34)
        pygame.draw.line(s, brow_col, (face_cx - 6 * px, face_cy - 3 * px), (face_cx - 2 * px, face_cy - 4 * px), max(1, px))
        pygame.draw.line(s, brow_col, (face_cx + 2 * px, face_cy - 4 * px), (face_cx + 6 * px, face_cy - 3 * px), max(1, px))
        pygame.draw.circle(s, eye_col, (face_cx - 4 * px, face_cy - 1 * px), max(1, px))
        pygame.draw.circle(s, eye_col, (face_cx + 4 * px, face_cy - 1 * px), max(1, px))

        # Beard for wise mentor look.
        beard_col = (110, 88, 132)
        beard = [(face_cx - 7 * px, face_cy + 3 * px), (face_cx + 7 * px, face_cy + 3 * px), (face_cx + 3 * px, face_cy + 11 * px), (face_cx - 3 * px, face_cy + 11 * px)]
        pygame.draw.polygon(s, beard_col, beard)

        # Staff with arcane orb.
        sx = int(w * 0.74)
        pygame.draw.line(s, self.PALETTE['staff'], (sx, int(h * 0.33)), (sx, int(h * 0.82)), max(2, px + 1))
        pygame.draw.circle(s, self.PALETTE['gold'], (sx, int(h * 0.29)), max(3, px * 3))
        pygame.draw.circle(s, self.PALETTE['cyan'], (sx, int(h * 0.29)), max(1, px + 1), max(1, px))

        # Chakana emblem on chest.
        ccx, ccy = cx, int(h * 0.57)
        rr = max(4, int(min(w, h) * 0.06))
        pygame.draw.rect(s, self.PALETTE['gold'], (ccx - rr // 2, ccy - rr // 2, rr, rr), max(1, px))
        pygame.draw.line(s, self.PALETTE['gold'], (ccx - rr, ccy), (ccx + rr, ccy), max(1, px))
        pygame.draw.line(s, self.PALETTE['gold'], (ccx, ccy - rr), (ccx, ccy + rr), max(1, px))

        # Variant accents.
        v = str(variant or 'combat_hud').lower()
        if 'victory' in v:
            pygame.draw.circle(s, (*self.PALETTE['gold'], 44), (cx, int(h * 0.23)), int(min(w, h) * 0.17), max(1, px))
        elif 'defeat' in v:
            shade = pygame.Surface((w, h), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 62))
            s.blit(shade, (0, 0))
        elif 'menu' in v:
            pygame.draw.arc(s, self.PALETTE['cyan'], (int(w * 0.17), int(h * 0.17), int(w * 0.66), int(h * 0.66)), 0.2, math.pi - 0.2, max(1, px))
        return s
