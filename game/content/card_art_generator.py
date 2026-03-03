from __future__ import annotations

from pathlib import Path
import pygame

from game.core.paths import assets_dir


class CardArtGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "cards"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def ensure_art(self, card_id: str, tags: list[str]):
        path = self.out_dir / f"{card_id}.png"
        if path.exists():
            return
        surf = pygame.Surface((256, 160))
        base = (48, 34, 82)
        for y in range(160):
            for x in range(256):
                tone = (x * 2 + y * 3 + len(card_id) * 17) % 28
                c = (base[0] + tone, base[1] + tone // 2, base[2] + tone)
                surf.set_at((x, y), c)
        for i in range(28):
            px = (i * 37 + len(card_id) * 9) % 256
            py = (i * 23 + len(tags) * 13) % 160
            pygame.draw.circle(surf, (170, 120, 220), (px, py), 2)
        if "attack" in tags:
            pygame.draw.polygon(surf, (210, 110, 130), [(42, 120), (128, 28), (212, 120)], 3)
        if "skill" in tags:
            pygame.draw.rect(surf, (110, 160, 220), (64, 36, 128, 88), 3)
        if "ritual" in tags or "arcane" in tags:
            pygame.draw.line(surf, (205, 175, 255), (128, 18), (128, 142), 2)
            pygame.draw.line(surf, (205, 175, 255), (28, 80), (228, 80), 2)
        pygame.draw.rect(surf, (225, 200, 245), surf.get_rect(), 2)
        pygame.image.save(surf, str(path))


def export_prompts(cards: list[dict]):
    out = assets_dir() / "sprites" / "cards" / "prompts_cards.txt"
    lines = []
    for c in cards:
        cid = c.get("id", "unknown")
        lines.append(f"{cid}: pixel art mystical andean gothic purple mage sigils, dramatic light, chakana symbol")
    out.write_text("\n".join(lines), encoding="utf-8")
