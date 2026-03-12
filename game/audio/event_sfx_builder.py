from __future__ import annotations

import json
import math
from array import array

from game.core.paths import project_root

SAMPLE_RATE = 32000


def load_audio_sfx_registry() -> dict:
    path = project_root() / 'data' / 'audio_sfx_registry.json'
    return json.loads(path.read_text(encoding='utf-8'))


def _triangle(phase: float) -> float:
    v = (phase / (2 * math.pi)) % 1.0
    return 4.0 * abs(v - 0.5) - 1.0


def _lookup_event(name: str) -> dict:
    registry = load_audio_sfx_registry()
    for section in ('ui_sounds', 'gameplay_sounds', 'meta_sounds'):
        payload = registry.get(section, {})
        if name in payload:
            return payload[name]
    raise KeyError(f'unknown_audio_event:{name}')


def compose_event_sfx(name: str) -> array:
    spec = _lookup_event(name)
    freq = float(spec['pitch'])
    seconds = float(spec['duration'])
    family = str(spec.get('family', 'default'))
    total = max(1, int(seconds * SAMPLE_RATE))
    out = array('h')

    for i in range(total):
        t = i / SAMPLE_RATE
        env = min(1.0, t / 0.008) * max(0.0, min(1.0, (seconds - t) / 0.08))
        body = 0.68 * math.sin(2 * math.pi * freq * t)
        harmonic = 0.18 * math.sin(2 * math.pi * (freq * 1.5) * t + 0.18)
        low = 0.10 * math.sin(2 * math.pi * max(52.0, freq * 0.5) * t)
        transient = 0.0

        if family in {'impact_light', 'impact_heavy', 'boss_warning'}:
            transient += 0.22 * _triangle(2 * math.pi * (freq * 0.72) * t)
        if family in {'ui_soft', 'ui_confirm', 'ascend', 'reward', 'reveal_rare', 'reveal_legendary'}:
            transient += 0.10 * math.sin(2 * math.pi * (freq * 2.0) * t + 0.3)
        if family in {'ritual', 'decay', 'warning'}:
            transient += 0.06 * math.sin(2 * math.pi * (freq * 0.25) * t)

        x = body + harmonic + low + transient
        out.append(int(max(-1.0, min(1.0, x * env * 0.82)) * 32767))

    return out
