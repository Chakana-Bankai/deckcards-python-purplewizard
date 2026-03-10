from __future__ import annotations

import math
import pygame


class AvatarGenerator:
    """Generate serious Chakana/Archon avatar variants with readable silhouettes."""

    PALETTE = {
        "void": (14, 10, 26),
        "robe": (86, 50, 146),
        "robe_dark": (56, 32, 100),
        "gold": (230, 196, 116),
        "cyan": (112, 214, 235),
        "skin": (198, 156, 128),
        "staff": (120, 86, 64),
        "archon_red": (214, 86, 112),
        "archon_dark": (62, 20, 30),
    }

    def _scanlines(self, surface: pygame.Surface, color: tuple[int, int, int], alpha: int):
        w, h = surface.get_size()
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(1, h, 3):
            pygame.draw.line(layer, (*color, alpha), (2, y), (w - 3, y), 1)
        surface.blit(layer, (0, 0))

    def render(self, variant: str, size: tuple[int, int], seed: int = 0) -> pygame.Surface:
        w, h = max(32, int(size[0])), max(32, int(size[1]))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        px = max(1, w // 96)
        v = str(variant or "combat_hud").lower()
        is_archon = "archon" in v
        is_guardian = ("guardian" in v) or ("guardians" in v)
        is_oracle = ("oracle" in v) or ("oracles" in v)
        is_demon = ("demon" in v) or ("demons" in v) or ("void" in v)
        is_holo = is_oracle or ("holo" in v)

        cx = w // 2
        ground = int(h * 0.88)

        aura_core = self.PALETTE["archon_red"] if is_archon else ((88, 204, 172) if is_guardian else ((162, 132, 248) if is_oracle else ((182, 72, 92) if is_demon else self.PALETTE["cyan"])))
        aura_ring = self.PALETTE["archon_dark"] if is_archon else ((210, 238, 198) if is_guardian else ((220, 212, 255) if is_oracle else ((118, 36, 44) if is_demon else self.PALETTE["gold"])))
        pygame.draw.circle(s, (*aura_core, 36), (cx, int(h * 0.36)), int(min(w, h) * 0.26))
        pygame.draw.circle(s, (*aura_ring, 28), (cx, int(h * 0.40)), int(min(w, h) * 0.20), max(1, px))

        robe_main = self.PALETTE["archon_dark"] if is_archon else ((38, 88, 82) if is_guardian else ((76, 58, 150) if is_oracle else ((72, 24, 34) if is_demon else self.PALETTE["robe"])))
        robe_edge = self.PALETTE["archon_red"] if is_archon else ((112, 198, 170) if is_guardian else ((136, 114, 214) if is_oracle else ((184, 78, 96) if is_demon else self.PALETTE["robe_dark"])))
        robe = [(cx, int(h * 0.24)), (int(w * 0.23), ground), (int(w * 0.77), ground)]
        pygame.draw.polygon(s, robe_main, robe)
        pygame.draw.polygon(s, robe_edge, robe, max(1, px))

        hat = [(cx, int(h * 0.05)), (int(w * 0.35), int(h * 0.31)), (int(w * 0.65), int(h * 0.31))]
        pygame.draw.polygon(s, robe_edge, hat)
        pygame.draw.polygon(s, self.PALETTE["gold"] if not is_archon else self.PALETTE["archon_red"], hat, max(1, px))
        brim = pygame.Rect(int(w * 0.31), int(h * 0.30), int(w * 0.38), max(2, int(h * 0.03)))
        pygame.draw.ellipse(s, robe_edge, brim)

        face_cx, face_cy = cx, int(h * 0.38)
        frx, fry = max(4, int(w * 0.06)), max(4, int(h * 0.07))
        skin = (164, 100, 112) if is_archon else ((170, 164, 144) if is_guardian else ((184, 148, 132) if is_oracle else ((138, 92, 102) if is_demon else self.PALETTE["skin"])))
        pygame.draw.ellipse(s, skin, (face_cx - frx, face_cy - fry, frx * 2, fry * 2))
        cheek = (122, 64, 76) if is_archon else (164, 124, 100)
        pygame.draw.line(s, cheek, (face_cx - frx + 2 * px, face_cy + px), (face_cx - 2 * px, face_cy + 4 * px), max(1, px))
        pygame.draw.line(s, cheek, (face_cx + frx - 2 * px, face_cy + px), (face_cx + 2 * px, face_cy + 4 * px), max(1, px))

        eye_col = (250, 182, 192) if is_archon else self.PALETTE["void"]
        brow_col = (58, 38, 34)
        pygame.draw.line(s, brow_col, (face_cx - 6 * px, face_cy - 3 * px), (face_cx - 2 * px, face_cy - 4 * px), max(1, px))
        pygame.draw.line(s, brow_col, (face_cx + 2 * px, face_cy - 4 * px), (face_cx + 6 * px, face_cy - 3 * px), max(1, px))
        pygame.draw.circle(s, eye_col, (face_cx - 4 * px, face_cy - px), max(1, px))
        pygame.draw.circle(s, eye_col, (face_cx + 4 * px, face_cy - px), max(1, px))

        beard_col = (96, 58, 110) if is_archon else ((78, 122, 116) if is_guardian else ((104, 86, 156) if is_oracle else ((94, 52, 64) if is_demon else (110, 88, 132))))
        beard = [(face_cx - 7 * px, face_cy + 3 * px), (face_cx + 7 * px, face_cy + 3 * px), (face_cx + 3 * px, face_cy + 11 * px), (face_cx - 3 * px, face_cy + 11 * px)]
        pygame.draw.polygon(s, beard_col, beard)

        sx = int(w * 0.74)
        staff_col = (96, 52, 44) if is_archon else self.PALETTE["staff"]
        orb_col = self.PALETTE["archon_red"] if is_archon else ((194, 238, 204) if is_guardian else ((212, 208, 255) if is_oracle else ((214, 112, 124) if is_demon else self.PALETTE["gold"])))
        pygame.draw.line(s, staff_col, (sx, int(h * 0.33)), (sx, int(h * 0.82)), max(2, px + 1))
        pygame.draw.circle(s, orb_col, (sx, int(h * 0.29)), max(3, px * 3))

        ccx, ccy = cx, int(h * 0.57)
        rr = max(4, int(min(w, h) * 0.06))
        emblem_col = self.PALETTE["archon_red"] if is_archon else ((194, 238, 204) if is_guardian else ((212, 208, 255) if is_oracle else ((214, 112, 124) if is_demon else self.PALETTE["gold"])))
        pygame.draw.rect(s, emblem_col, (ccx - rr // 2, ccy - rr // 2, rr, rr), max(1, px))
        pygame.draw.line(s, emblem_col, (ccx - rr, ccy), (ccx + rr, ccy), max(1, px))
        pygame.draw.line(s, emblem_col, (ccx, ccy - rr), (ccx, ccy + rr), max(1, px))

        if "victory" in v:
            pygame.draw.circle(s, (*self.PALETTE["gold"], 44), (cx, int(h * 0.23)), int(min(w, h) * 0.17), max(1, px))
        elif "defeat" in v:
            shade = pygame.Surface((w, h), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 62))
            s.blit(shade, (0, 0))
        elif "menu" in v:
            arc_col = self.PALETTE["archon_red"] if is_archon else self.PALETTE["cyan"]
            pygame.draw.arc(s, arc_col, (int(w * 0.17), int(h * 0.17), int(w * 0.66), int(h * 0.66)), 0.2, math.pi - 0.2, max(1, px))

        if is_holo:
            holo = pygame.Surface((w, h), pygame.SRCALPHA)
            holo.fill((88, 142, 255, 28) if not is_archon else (255, 88, 112, 30))
            s.blit(holo, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self._scanlines(s, (126, 212, 246) if not is_archon else (246, 126, 146), 28)

        return s
