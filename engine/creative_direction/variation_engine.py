from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class VariationConfig:
    count: int = 6
    spread: int = 997


class VariationEngine:
    """Deterministic seed variation helper for iterative generation."""

    def seed_variations(self, base_seed: int, *, count: int = 6, spread: int = 997) -> list[int]:
        rng = random.Random(int(base_seed))
        offsets = set()
        while len(offsets) < max(1, int(count)):
            offsets.add(rng.randint(-spread, spread))
        return [int(base_seed) + off for off in sorted(offsets)]

    def mutate_from_best(self, best_seed: int, *, count: int = 4, tightness: int = 211) -> list[int]:
        rng = random.Random(int(best_seed) ^ 0xA5A5A5)
        out = [int(best_seed)]
        while len(out) < max(1, int(count)):
            out.append(int(best_seed) + rng.randint(-tightness, tightness))
        return out
