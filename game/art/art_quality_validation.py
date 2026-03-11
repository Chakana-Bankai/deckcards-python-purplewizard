from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from engine.creative_direction.quality_evaluator import QualityEvaluator


@dataclass(slots=True)
class ArtQualityMetrics:
    silhouette_readability: float
    subject_recognizability: float
    environment_clarity: float
    palette_coherence: float
    excessive_noise: float
    lore_alignment: float

    def to_dict(self) -> dict[str, float]:
        return {
            'silhouette_readability': round(self.silhouette_readability, 4),
            'subject_recognizability': round(self.subject_recognizability, 4),
            'environment_clarity': round(self.environment_clarity, 4),
            'palette_coherence': round(self.palette_coherence, 4),
            'excessive_noise': round(self.excessive_noise, 4),
            'lore_alignment': round(self.lore_alignment, 4),
        }


@dataclass(slots=True)
class ArtQualityResult:
    card_id: str
    path: str
    overall: float
    accepted: bool
    retries: int
    metrics: ArtQualityMetrics


def _target_score(value: float, low: float, high: float) -> float:
    if value < low:
        return max(0.0, value / max(low, 1e-6))
    if value > high:
        return max(0.0, 1.0 - min(1.0, (value - high) / max(1e-6, 1.0 - high)) * 0.65)
    return 1.0


def _noise_score(path: Path) -> float:
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
    except Exception:
        return 0.0
    w, h = surf.get_size()
    if w <= 1 or h <= 1:
        return 0.0
    step_x = max(1, w // 64)
    step_y = max(1, h // 64)
    samples = 0
    high_delta = 0
    for y in range(0, h - step_y, step_y):
        for x in range(0, w - step_x, step_x):
            c0 = surf.get_at((x, y))
            c1 = surf.get_at((x + step_x, y))
            c2 = surf.get_at((x, y + step_y))
            d1 = abs(int(c0.r) - int(c1.r)) + abs(int(c0.g) - int(c1.g)) + abs(int(c0.b) - int(c1.b))
            d2 = abs(int(c0.r) - int(c2.r)) + abs(int(c0.g) - int(c2.g)) + abs(int(c0.b) - int(c2.b))
            samples += 2
            if d1 > 170:
                high_delta += 1
            if d2 > 170:
                high_delta += 1
    if samples <= 0:
        return 0.0
    ratio = high_delta / samples
    return round(max(0.0, 1.0 - min(1.0, ratio * 3.2)), 4)


def _lore_alignment_score(card: dict, semantic: dict, references_used: list[str], palette_id: str) -> float:
    card_id = str(card.get('id', '') or '').lower()
    set_id = str(card.get('set', '') or '').lower()
    archetype = str(card.get('archetype', '') or '').lower()
    score = 0.0

    subject_kind = str(semantic.get('subject_kind', '') or '').lower()
    object_kind = str(semantic.get('object_kind', '') or '').lower()
    environment_kind = str(semantic.get('environment_kind', '') or '').lower()
    if subject_kind:
        score += 0.20
    if object_kind:
        score += 0.15
    if environment_kind:
        score += 0.15
    if len(references_used) >= 2:
        score += 0.15
    if len(references_used) >= 3:
        score += 0.05

    is_archon = set_id in {'arconte', 'archon'} or archetype == 'archon_war' or card_id.startswith('arc_')
    is_hyper = set_id in {'hiperborea', 'hiperboria'} or card_id.startswith('hip_')
    if is_archon and palette_id == 'archon':
        score += 0.20
    elif is_hyper and palette_id == 'hyperborea':
        score += 0.20
    elif not is_archon and not is_hyper and palette_id == 'chakana':
        score += 0.20

    if is_archon and 'archon' in subject_kind:
        score += 0.10
    elif is_hyper and ('hyperborean' in subject_kind or environment_kind == 'citadel'):
        score += 0.10
    elif not is_archon and not is_hyper and subject_kind in {'warrior_foreground', 'weapon_bearer', 'guardian_bearer', 'oracle_totem'}:
        score += 0.10
    return min(1.0, round(score, 4))


def evaluate_generated_art(*, card: dict, path: Path, semantic: dict, scene_type: str, environment_preset: str, palette_id: str, references_used: list[str], occ_subject: float, occ_object: float, occ_fx: float) -> ArtQualityResult:
    evaluator = QualityEvaluator()
    q = evaluator.evaluate_art_file(path)
    q_metrics = q.metrics

    silhouette_occ = _target_score(float(occ_subject or 0.0), 0.22, 0.55)
    object_occ = _target_score(float(occ_object or 0.0), 0.05, 0.22)
    fx_occ = 1.0 - min(1.0, max(0.0, float(occ_fx or 0.0) - 0.12) / 0.25)

    silhouette_readability = min(1.0, 0.55 * float(q_metrics.get('composition_clarity', 0.0)) + 0.30 * silhouette_occ + 0.15 * object_occ)
    subject_recognizability = min(1.0, 0.65 * float(q_metrics.get('subject_recognizability', 0.0)) + 0.20 * silhouette_occ + 0.15 * object_occ)
    environment_clarity = min(1.0, 0.55 * float(q_metrics.get('visual_depth', 0.0)) + 0.20 * (1.0 if scene_type else 0.0) + 0.15 * (1.0 if environment_preset else 0.0) + 0.10 * float(q_metrics.get('composition_clarity', 0.0)))
    palette_coherence = min(1.0, 0.75 * float(q_metrics.get('color_harmony', 0.0)) + 0.25 * (1.0 if palette_id else 0.0))
    excessive_noise = min(1.0, 0.70 * _noise_score(path) + 0.30 * fx_occ)
    lore_alignment = _lore_alignment_score(card, semantic, references_used, palette_id)

    metrics = ArtQualityMetrics(
        silhouette_readability=silhouette_readability,
        subject_recognizability=subject_recognizability,
        environment_clarity=environment_clarity,
        palette_coherence=palette_coherence,
        excessive_noise=excessive_noise,
        lore_alignment=lore_alignment,
    )
    overall = (
        metrics.silhouette_readability * 0.22
        + metrics.subject_recognizability * 0.22
        + metrics.environment_clarity * 0.16
        + metrics.palette_coherence * 0.16
        + metrics.excessive_noise * 0.10
        + metrics.lore_alignment * 0.14
    )
    accepted = overall >= 0.56 and metrics.silhouette_readability >= 0.42 and metrics.subject_recognizability >= 0.40 and metrics.excessive_noise >= 0.45
    return ArtQualityResult(
        card_id=str(card.get('id', '') or ''),
        path=str(path),
        overall=round(overall, 4),
        accepted=accepted,
        retries=0,
        metrics=metrics,
    )
