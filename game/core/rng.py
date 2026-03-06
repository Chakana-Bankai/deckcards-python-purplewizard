"""Seedable deterministic RNG wrapper."""

from random import Random


class SeededRNG:
    def __init__(self, seed: int = 1337):
        self._random = Random(seed)
        self.seed = seed

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def choice(self, seq):
        if not seq:
            return None
        return self._random.choice(seq)

    def shuffle(self, seq):
        self._random.shuffle(seq)

    def random(self) -> float:
        return self._random.random()
