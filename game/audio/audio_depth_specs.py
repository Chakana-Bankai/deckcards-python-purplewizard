from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game.core.paths import project_root


def audio_depth_specs_path() -> Path:
    return project_root() / 'data' / 'music_specs' / 'audio_depth_context_specs.json'


def load_audio_depth_specs() -> dict[str, dict[str, Any]]:
    path = audio_depth_specs_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))
