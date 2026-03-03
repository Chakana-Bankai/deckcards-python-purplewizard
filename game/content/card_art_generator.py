from __future__ import annotations

from pathlib import Path
import random
import pygame

from game.core.paths import assets_dir


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _variance(self, surf: pygame.Surface) -> int:
        sample = []
        for y in range(0, 160, 10):
            for x in range(0, 256, 10):
                sample.append(surf.get_at((x, y))[:3])
        rs = [c[0] for c in sample]
        gs = [c[1] for c in sample]
        bs = [c[2] for c in sample]
        return (max(rs) - min(rs)) + (max(gs) - min(gs)) + (max(bs) - min(bs))

    def _render(self, card_id: str, tags: list[str], salt: int) -> pygame.Surface:
        rng = random.Random(f"{card_id}:{salt}")
        surf = pygame.Surface((256, 160))
        bg1 = (40 + rng.randint(0, 40), 20 + rng.randint(0, 25), 70 + rng.randint(0, 45))
        bg2 = (80 + rng.randint(0, 60), 35 + rng.randint(0, 35), 120 + rng.randint(0, 65))
        for y in range(160):
            t = y / 159.0
            for x in range(256):
                n = (x * 7 + y * 5 + rng.randint(0, 6)) & 1
                r = int(bg1[0] * (1 - t) + bg2[0] * t) + n * 2
                g = int(bg1[1] * (1 - t) + bg2[1] * t) + n * 2
                b = int(bg1[2] * (1 - t) + bg2[2] * t) + n * 2
                surf.set_at((x, y), (min(r, 255), min(g, 255), min(b, 255)))

        for _ in range(120):
            px, py = rng.randint(0, 255), rng.randint(0, 159)
            c = (170 + rng.randint(0, 70), 130 + rng.randint(0, 50), 200 + rng.randint(0, 55))
            surf.set_at((px, py), c)

        # chakana motif
        cx, cy = 128, 80
        col = (220, 190, 245)
        for i in range(-24, 25, 4):
            pygame.draw.rect(surf, col, (cx + i - 1, cy - 2, 3, 5))
            pygame.draw.rect(surf, col, (cx - 2, cy + i - 1, 5, 3))
        pygame.draw.rect(surf, (245, 235, 255), (cx - 9, cy - 9, 18, 18), 2)

        for _ in range(8):
            x1, y1 = rng.randint(10, 245), rng.randint(10, 150)
            x2, y2 = x1 + rng.randint(-30, 30), y1 + rng.randint(-30, 30)
            pygame.draw.line(surf, (200, 160, 245), (x1, y1), (x2, y2), 1)

        if "attack" in tags:
            for o in range(0, 6):
                pygame.draw.polygon(surf, (220 - o * 8, 120 - o * 6, 130), [(42 + o, 130), (128, 25 + o), (214 - o, 130)], 2)
        if "skill" in tags:
            pygame.draw.rect(surf, (110, 175, 230), (56, 36, 144, 92), 3)
        if "ritual" in tags or "arcane" in tags:
            pygame.draw.circle(surf, (210, 175, 255), (128, 80), 52, 2)
            pygame.draw.circle(surf, (210, 175, 255), (128, 80), 28, 2)

        pygame.draw.rect(surf, (240, 220, 255), surf.get_rect(), 3)
        return surf

    def ensure_art(self, card_id: str, tags: list[str]):
        path = self.out_dir / f"{card_id}.png"
        if path.exists():
            return
        surf = self._render(card_id, tags, 0)
        if self._variance(surf) < 60:
            surf = self._render(card_id, tags, 1)
        pygame.image.save(surf, str(path))
        print(f"[art] Generated card art: {card_id} -> {path}")


def export_prompts(cards: list[dict]):
    out = assets_dir() / "sprites" / "cards" / "prompts_cards.txt"
    lines = []
    for c in cards:
        cid = c.get("id", "unknown")
        lines.append(f"{cid}: 8-bit mystical andean glyphs, chakana sigil, purple mage, rune-lit card art")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[art] prompts exported -> {out}")
