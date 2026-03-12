from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from game.core.paths import project_root


@lru_cache(maxsize=1)
def load_art_style_lock() -> dict[str, object]:
    path = Path(project_root()) / 'data' / 'art_identity' / 'art_style_lock.json'
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def symbolic_style_active() -> bool:
    data = load_art_style_lock()
    return str(data.get('style_mode', '')).lower() == 'symbolic_origami' and bool(data.get('principles', {}).get('template_driven_subjects', False))
