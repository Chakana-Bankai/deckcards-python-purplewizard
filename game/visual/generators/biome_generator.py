from __future__ import annotations

import pygame

from .lore_motifs import MOTIF_LIBRARY


class BiomeGenerator:
    """Generate biome identity panels and sigils."""

    PALETTES = {
        "ukhu_pacha": ((10, 8, 22), (52, 34, 86), (118, 86, 182)),
        "kay_pacha": ((18, 14, 30), (74, 42, 112), (96, 198, 226)),
        "hanan_pacha": ((20, 22, 38), (90, 82, 146), (230, 196, 126)),
        "fractura_chakana": ((8, 6, 14), (88, 42, 102), (180, 242, 255)),
    }

    ALIASES = {
        "ukhu": "ukhu_pacha",
        "kay": "kay_pacha",
        "kaypacha": "kay_pacha",
        "hanan": "hanan_pacha",
        "fractura": "fractura_chakana",
        "fractura_de_la_chakana": "fractura_chakana",
        "umbral": "ukhu_pacha",
        "forest": "ukhu_pacha",
    }

    def _palette(self, biome_id: str):
        b = str(biome_id or "kay_pacha").lower()
        b = self.ALIASES.get(b, b)
        return self.PALETTES.get(b, self.PALETTES["kay_pacha"])

    def _draw_mountain_ridge(self, surface: pygame.Surface, color: tuple[int, int, int]):
        w, h = surface.get_size()
        ridge = [
            (0, int(h * 0.78)),
            (int(w * 0.18), int(h * 0.60)),
            (int(w * 0.36), int(h * 0.72)),
            (int(w * 0.54), int(h * 0.56)),
            (int(w * 0.74), int(h * 0.70)),
            (w, int(h * 0.58)),
            (w, h),
            (0, h),
        ]
        pygame.draw.polygon(surface, (*color, 42), ridge)

    def _draw_constellation(self, surface: pygame.Surface, color: tuple[int, int, int]):
        w, h = surface.get_size()
        pts = [
            (int(w * 0.20), int(h * 0.24)),
            (int(w * 0.34), int(h * 0.18)),
            (int(w * 0.50), int(h * 0.22)),
            (int(w * 0.66), int(h * 0.16)),
            (int(w * 0.80), int(h * 0.24)),
        ]
        for i in range(len(pts) - 1):
            pygame.draw.line(surface, (*color, 80), pts[i], pts[i + 1], 1)
        for p in pts:
            pygame.draw.circle(surface, (*color, 130), p, 2)

    def render_panel(self, biome_id: str, size: tuple[int, int], motif: str = "bg") -> pygame.Surface:
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

        biome_key = self.ALIASES.get(str(biome_id or "").lower(), str(biome_id or "").lower())
        if motif in {"bg", "mg"}:
            self._draw_mountain_ridge(s, c2)
            self._draw_constellation(s, c2)
            pygame.draw.circle(s, (*c2, 34), (w // 2, h // 2), int(min(w, h) * 0.28), max(1, w // 80))
            pygame.draw.line(s, (*c2, 58), (w // 2, int(h * 0.12)), (w // 2, int(h * 0.88)), max(1, w // 130))
            pygame.draw.line(s, (*c2, 58), (int(w * 0.12), h // 2), (int(w * 0.88), h // 2), max(1, w // 130))

        if motif in {"sigil", "fg"}:
            pygame.draw.polygon(s, c2, [(w // 2, int(h * 0.16)), (int(w * 0.84), h // 2), (w // 2, int(h * 0.84)), (int(w * 0.16), h // 2)], max(1, w // 84))
            if biome_key == "fractura_chakana":
                pygame.draw.line(s, (*c2, 190), (int(w * 0.30), int(h * 0.22)), (int(w * 0.72), int(h * 0.78)), 2)

        if "chakana" in " ".join(MOTIF_LIBRARY.get("chakana", {}).get("symbols", ())):
            step = max(6, min(w, h) // 20)
            cx, cy = w // 2, h // 2
            pygame.draw.rect(s, (*c2, 72), (cx - step // 2, cy - step // 2, step, step), 1)

        return s
