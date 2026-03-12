from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pygame

from game.core.paths import project_root


@lru_cache(maxsize=1)
def load_identity_lock() -> dict[str, object]:
    path = Path(project_root()) / 'data' / 'art_identity' / 'art_style_lock.json'
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def load_geometric_domain() -> dict[str, object]:
    path = Path(project_root()) / 'data' / 'art_identity' / 'geometric_art_domain.json'
    return json.loads(path.read_text(encoding='utf-8'))


def validate_identity_lock(subject_rect: pygame.Rect, object_rect: pygame.Rect, canvas_size: tuple[int, int], silhouette_integrity: float) -> dict[str, object]:
    w, h = canvas_size
    occ_subject = round((subject_rect.width * subject_rect.height) / max(1, w * h), 4)
    occ_object = round((object_rect.width * object_rect.height) / max(1, w * h), 4) if object_rect.width > 0 and object_rect.height > 0 else 0.0
    subject_height_ratio = round(subject_rect.height / max(1, h), 4)
    subject_width_ratio = round(subject_rect.width / max(1, w), 4)
    object_height_ratio = round(object_rect.height / max(1, h), 4) if object_rect.height > 0 else 0.0

    domain = load_geometric_domain().get('composition_rules', {})
    target_subject_ratio = float(domain.get('subject_ratio', 0.45))
    target_internal_ratio = float(domain.get('internal_elements_ratio', 0.30))

    subject_ok = (target_subject_ratio - 0.12) <= subject_height_ratio <= (target_subject_ratio + 0.10)
    subject_width_ok = subject_width_ratio <= 0.35
    object_ok = object_height_ratio <= target_internal_ratio and object_rect.height <= int(subject_rect.height * 0.60)
    identity_ok = silhouette_integrity >= 0.75

    return {
        'target_quality': load_identity_lock().get('target_quality', 'playable_placeholder_with_identity'),
        'occ_subject': occ_subject,
        'occ_object': occ_object,
        'subject_height_ratio': subject_height_ratio,
        'subject_width_ratio': subject_width_ratio,
        'object_height_ratio': object_height_ratio,
        'silhouette_integrity': round(float(silhouette_integrity), 4),
        'subject_ok': subject_ok,
        'subject_width_ok': subject_width_ok,
        'object_ok': object_ok,
        'identity_ok': identity_ok,
        'passed': subject_ok and subject_width_ok and object_ok and identity_ok,
    }
