from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import pygame

from game.core.paths import art_reference_dir


@dataclass
class ReferenceChoice:
    path: Path
    category: str
    cue: str
    avg_color: tuple[int, int, int]


class ReferenceSampler:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or art_reference_dir())

    def _files_for(self, category: str) -> list[Path]:
        folder = self.root / str(category or '').strip()
        if not folder.exists():
            return []
        return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}])

    def _score(self, path: Path, keywords: list[str]) -> int:
        stem = path.stem.lower()
        score = 0
        for kw in keywords:
            low = str(kw or '').strip().lower()
            if not low:
                continue
            if low in stem:
                score += 4
            else:
                for token in low.replace('-', ' ').replace('_', ' ').split():
                    if token and token in stem:
                        score += 1
        return score

    def _avg_color(self, path: Path) -> tuple[int, int, int]:
        try:
            surf = pygame.image.load(str(path)).convert()
        except Exception:
            try:
                surf = pygame.image.load(str(path))
            except Exception:
                return (110, 110, 110)
        w, h = surf.get_size()
        if w <= 0 or h <= 0:
            return (110, 110, 110)
        step_x = max(1, w // 8)
        step_y = max(1, h // 8)
        r = g = b = n = 0
        for x in range(0, w, step_x):
            for y in range(0, h, step_y):
                c = surf.get_at((x, y))
                r += int(c.r)
                g += int(c.g)
                b += int(c.b)
                n += 1
        if n <= 0:
            return (110, 110, 110)
        return (r // n, g // n, b // n)

    def pick(self, categories: list[str], keywords: list[str], seed: int) -> list[ReferenceChoice]:
        rng = random.Random(seed)
        scored: list[tuple[int, float, Path, str]] = []
        for category in categories:
            for path in self._files_for(category):
                score = self._score(path, keywords)
                scored.append((score, rng.random(), path, category))
        scored.sort(key=lambda row: (-row[0], row[1], row[2].name.lower()))
        out: list[ReferenceChoice] = []
        for score, _tie, path, category in scored[:6]:
            out.append(ReferenceChoice(path=path, category=category, cue=path.stem.replace('_', ' '), avg_color=self._avg_color(path)))
        return out
