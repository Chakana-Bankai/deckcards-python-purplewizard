from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from .quality_evaluator import QualityEvaluator
from .style_guide import CreativeStyleGuide
from .variation_engine import VariationEngine


class CreativeArtDirector:
    """Iterative art supervisor: generate -> evaluate -> mutate -> regenerate."""

    def __init__(self):
        self.style = CreativeStyleGuide()
        self.variation = VariationEngine()
        self.evaluator = QualityEvaluator()

    def _candidate_path(self, out_path: Path, label: str) -> Path:
        return out_path.with_name(f"{out_path.stem}__{label}{out_path.suffix}")

    def evolve(
        self,
        *,
        card_id: str,
        set_id: str,
        base_seed: int,
        out_path: Path,
        generate_fn: Callable[[Path, int], dict],
        threshold: float = 0.62,
    ) -> dict:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        seeds = self.variation.seed_variations(base_seed, count=6, spread=991)
        best: dict | None = None
        candidates: list[Path] = []

        for i, seed in enumerate(seeds):
            cpath = self._candidate_path(out_path, f"pass1_{i}")
            data = generate_fn(cpath, seed) or {}
            score = self.evaluator.evaluate_art_file(cpath)
            data = dict(data)
            data.update({"seed": seed, "path": str(cpath), "score": score.overall, "metrics": score.metrics})
            candidates.append(cpath)
            if best is None or float(data["score"]) > float(best["score"]):
                best = data

        if best is None:
            # emergency single pass
            final = generate_fn(out_path, base_seed) or {}
            return {"selected_seed": base_seed, "score": 0.0, "fallback": True, **final}

        p2 = self.variation.mutate_from_best(int(best["seed"]), count=4, tightness=211)
        for i, seed in enumerate(p2):
            cpath = self._candidate_path(out_path, f"pass2_{i}")
            data = generate_fn(cpath, seed) or {}
            score = self.evaluator.evaluate_art_file(cpath)
            data = dict(data)
            data.update({"seed": seed, "path": str(cpath), "score": score.overall, "metrics": score.metrics})
            candidates.append(cpath)
            if float(data["score"]) > float(best["score"]):
                best = data

        best_path = Path(str(best.get("path", out_path)))
        if best_path.exists() and best_path != out_path:
            shutil.copy2(best_path, out_path)

        # cleanup candidate files to avoid artifact clutter
        for p in candidates:
            if p.exists() and p != out_path and p != best_path:
                try:
                    p.unlink()
                except Exception:
                    pass

        style = self.style.resolve_set_style(set_id)
        return {
            "selected_seed": int(best["seed"]),
            "score": float(best["score"]),
            "metrics": dict(best.get("metrics", {})),
            "set_style": style.set_id,
            "tone": style.tone,
            "threshold_pass": float(best["score"]) >= float(threshold),
            "path": str(out_path),
            "fallback": False,
        }
