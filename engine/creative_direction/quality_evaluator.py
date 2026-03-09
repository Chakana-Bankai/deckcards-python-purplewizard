from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass(frozen=True)
class QualityScore:
    overall: float
    metrics: dict[str, float]


class QualityEvaluator:
    """Lightweight quality scoring for iterative creative generation."""

    def evaluate_art_file(self, path: Path) -> QualityScore:
        if not path.exists():
            return QualityScore(0.0, {"missing": 0.0})
        try:
            surf = pygame.image.load(str(path))
        except Exception:
            return QualityScore(0.0, {"load_error": 0.0})

        w, h = surf.get_width(), surf.get_height()
        if w <= 0 or h <= 0:
            return QualityScore(0.0, {"invalid_size": 0.0})

        step_x = max(1, w // 48)
        step_y = max(1, h // 48)

        center_lums: list[float] = []
        edge_lums: list[float] = []
        sat_samples: list[float] = []
        top_lums: list[float] = []
        bot_lums: list[float] = []

        cx0, cx1 = int(w * 0.25), int(w * 0.75)
        cy0, cy1 = int(h * 0.15), int(h * 0.75)

        for y in range(0, h, step_y):
            for x in range(0, w, step_x):
                c = surf.get_at((x, y))
                r, g, b = int(c.r), int(c.g), int(c.b)
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                maxc = max(r, g, b)
                minc = min(r, g, b)
                sat = 0.0 if maxc == 0 else (maxc - minc) / maxc
                sat_samples.append(sat)
                if cx0 <= x <= cx1 and cy0 <= y <= cy1:
                    center_lums.append(lum)
                else:
                    edge_lums.append(lum)
                if y < h * 0.33:
                    top_lums.append(lum)
                if y > h * 0.66:
                    bot_lums.append(lum)

        def _avg(vals: list[float]) -> float:
            return sum(vals) / max(1, len(vals))

        center = _avg(center_lums)
        edge = _avg(edge_lums)
        sat = _avg(sat_samples)
        depth = abs(_avg(top_lums) - _avg(bot_lums)) / 255.0
        center_contrast = min(1.0, max(0.0, abs(center - edge) / 72.0))

        composition_clarity = center_contrast
        subject_recognizability = min(1.0, 0.55 * center_contrast + 0.45 * sat)
        symbol_presence = min(1.0, 0.30 + 0.70 * center_contrast)
        color_harmony = min(1.0, 1.0 - abs(0.55 - sat))
        visual_depth = min(1.0, max(0.0, depth))

        metrics = {
            "composition_clarity": composition_clarity,
            "subject_recognizability": subject_recognizability,
            "symbol_presence": symbol_presence,
            "color_harmony": color_harmony,
            "visual_depth": visual_depth,
        }
        overall = (
            metrics["composition_clarity"] * 0.24
            + metrics["subject_recognizability"] * 0.24
            + metrics["symbol_presence"] * 0.16
            + metrics["color_harmony"] * 0.20
            + metrics["visual_depth"] * 0.16
        )
        return QualityScore(overall=float(overall), metrics=metrics)

    def evaluate_music_samples(self, samples: array, sample_rate: int) -> QualityScore:
        if not samples:
            return QualityScore(0.0, {"missing": 0.0})

        n = len(samples)
        float_s = [float(v) / 32767.0 for v in samples]

        def _rms(segment: list[float]) -> float:
            if not segment:
                return 0.0
            return math.sqrt(sum(v * v for v in segment) / len(segment))

        win = max(128, min(n // 16, sample_rate // 2))
        env = []
        for i in range(0, n, win):
            env.append(_rms(float_s[i : i + win]))

        if not env:
            return QualityScore(0.0, {"invalid": 0.0})

        env_avg = sum(env) / len(env)
        env_var = sum((e - env_avg) ** 2 for e in env) / len(env)
        rhythmic_variation = min(1.0, env_var * 12.0)

        zc = 0
        prev = float_s[0]
        for cur in float_s[1:]:
            if (prev >= 0 > cur) or (prev < 0 <= cur):
                zc += 1
            prev = cur
        zc_rate = zc / max(1, n)
        melodic_variation = min(1.0, zc_rate * 90.0)

        peak = max(abs(v) for v in float_s)
        base = max(1e-6, env_avg)
        crest = peak / base
        harmonic_richness = min(1.0, max(0.0, (crest - 1.2) / 3.0))

        edge = max(1, sample_rate)
        a = float_s[:edge]
        b = float_s[-edge:]
        loop_delta = abs(_rms(a) - _rms(b))
        loop_quality = min(1.0, max(0.0, 1.0 - loop_delta * 2.8))

        emotional_tone = min(1.0, max(0.0, 0.5 + (env_avg - 0.15) * 1.6))

        metrics = {
            "melody_variation": melodic_variation,
            "harmonic_progression": harmonic_richness,
            "rhythm_complexity": rhythmic_variation,
            "emotional_tone": emotional_tone,
            "loop_quality": loop_quality,
        }
        overall = (
            metrics["melody_variation"] * 0.23
            + metrics["harmonic_progression"] * 0.21
            + metrics["rhythm_complexity"] * 0.21
            + metrics["emotional_tone"] * 0.15
            + metrics["loop_quality"] * 0.20
        )
        return QualityScore(overall=float(overall), metrics=metrics)
