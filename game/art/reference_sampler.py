from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import pygame

from game.art.art_reference_catalog import expand_categories, iter_category_entries
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
        entries = iter_category_entries(self.root, category)
        return [entry.path for entry in entries]

    def _score(self, path: Path, keywords: list[str], category: str) -> int:
        stem = path.stem.lower()
        subgroup = str(path.parent.relative_to(self.root)).replace('\\', '/').lower() if path.exists() else ''
        score = 0
        for kw in keywords:
            low = str(kw or '').strip().lower()
            if not low:
                continue
            if low in stem:
                score += 5
            else:
                for token in low.replace('-', ' ').replace('_', ' ').split():
                    if token and (token in stem or token in subgroup):
                        score += 2
        if category == 'subjects':
            score += 10
        elif category == 'weapons':
            score += 7
        elif category == 'symbols':
            score += 4
        elif category == 'environments':
            score += 3
        elif category == 'palettes_mood':
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
        for category in expand_categories(categories):
            for path in self._files_for(category):
                score = self._score(path, keywords, category)
                scored.append((score, rng.random(), path, category))
        scored.sort(key=lambda row: (-row[0], row[1], row[2].name.lower()))
        out: list[ReferenceChoice] = []
        seen: set[Path] = set()
        for score, _tie, path, category in scored:
            if path in seen:
                continue
            seen.add(path)
            out.append(ReferenceChoice(path=path, category=category, cue=path.stem.replace('_', ' '), avg_color=self._avg_color(path)))
            if len(out) >= 6:
                break
        return out
