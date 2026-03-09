from __future__ import annotations

from array import array
from typing import Callable

from .quality_evaluator import QualityEvaluator
from .style_guide import CreativeStyleGuide
from .variation_engine import VariationEngine


class CreativeMusicDirector:
    """Iterative music supervisor for procedural layer candidates."""

    def __init__(self):
        self.style = CreativeStyleGuide()
        self.variation = VariationEngine()
        self.evaluator = QualityEvaluator()

    def evolve_samples(
        self,
        *,
        context: str,
        variant: str,
        seconds: float,
        sample_rate: int,
        generate_samples_fn: Callable[[str, str, float, int], array],
        threshold: float = 0.58,
    ) -> tuple[array, dict]:
        base_seed = abs(hash(f"{context}:{variant}:{seconds}")) % (2**31 - 1)
        seeds = self.variation.seed_variations(base_seed, count=4, spread=617)
        best_samples: array | None = None
        best_meta: dict | None = None

        def _check(seed: int) -> tuple[array, dict]:
            candidate_variant = f"{variant}_cand_{seed & 0xFF}"
            samples = generate_samples_fn(context, candidate_variant, seconds, seed)
            score = self.evaluator.evaluate_music_samples(samples, sample_rate)
            return samples, {
                "seed": seed,
                "candidate_variant": candidate_variant,
                "score": score.overall,
                "metrics": score.metrics,
            }

        for seed in seeds:
            s, meta = _check(seed)
            if best_meta is None or float(meta["score"]) > float(best_meta["score"]):
                best_samples, best_meta = s, meta

        assert best_meta is not None and best_samples is not None

        p2 = self.variation.mutate_from_best(int(best_meta["seed"]), count=3, tightness=157)
        for seed in p2:
            s, meta = _check(seed)
            if float(meta["score"]) > float(best_meta["score"]):
                best_samples, best_meta = s, meta

        style = self.style.resolve_music_style(context)
        best_meta.update(
            {
                "context_style": style.context,
                "tempo": style.tempo,
                "rhythm": style.rhythm,
                "harmony": style.harmony,
                "ambient": style.ambient,
                "threshold_pass": float(best_meta["score"]) >= float(threshold),
            }
        )
        return best_samples, best_meta
