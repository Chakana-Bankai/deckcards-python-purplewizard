from __future__ import annotations

import math
from array import array
from dataclasses import dataclass

SAMPLE_RATE = 32000

STINGER_FAMILIES = {
    'ui_confirm': (392.0, 494.0, 587.0),
    'ui_cancel': (220.0, 196.0, 174.0),
    'reward': (294.0, 392.0, 494.0),
    'pack_open': (268.0, 340.0, 428.0),
    'rare_reveal': (312.0, 416.0, 540.0),
    'legendary_reveal': (196.0, 294.0, 392.0, 523.0),
    'victory': (330.0, 440.0, 554.0),
    'defeat': (196.0, 156.0, 117.0),
    'ritual_trigger': (210.0, 280.0, 350.0),
    'boss_warning': (128.0, 170.0, 128.0),
    'draw_card': (360.0, 410.0),
    'play_card': (250.0, 330.0),
}

DURATIONS = {
    'ui_confirm': 0.20,
    'ui_cancel': 0.18,
    'reward': 0.55,
    'pack_open': 0.65,
    'rare_reveal': 0.75,
    'legendary_reveal': 1.10,
    'victory': 0.90,
    'defeat': 0.85,
    'ritual_trigger': 0.55,
    'boss_warning': 0.75,
    'draw_card': 0.16,
    'play_card': 0.22,
}

@dataclass(frozen=True)
class StingerResult:
    name: str
    seconds: float
    samples: array


def _triangle(phase: float) -> float:
    v = (phase / (2 * math.pi)) % 1.0
    return 4.0 * abs(v - 0.5) - 1.0


def compose_stinger(name: str) -> StingerResult:
    freqs = STINGER_FAMILIES[name]
    seconds = float(DURATIONS[name])
    total = max(1, int(seconds * SAMPLE_RATE))
    seg = max(1, total // len(freqs))
    out = array('h')
    for i in range(total):
        t = i / SAMPLE_RATE
        idx = min(len(freqs) - 1, i // seg)
        f = freqs[idx]
        env = min(1.0, t / 0.01) * max(0.0, min(1.0, (seconds - t) / 0.12))
        shimmer = 0.0 if name in {'ui_cancel', 'defeat', 'boss_warning'} else 0.12 * math.sin(2 * math.pi * (f * 1.5) * t + 0.2)
        body = 0.70 * math.sin(2 * math.pi * f * t) + 0.18 * _triangle(2 * math.pi * (f * 0.5) * t)
        bass = 0.12 * math.sin(2 * math.pi * max(48.0, f * 0.5) * t)
        x = body + shimmer + bass
        out.append(int(max(-1.0, min(1.0, x * env * 0.82)) * 32767))
    return StingerResult(name=name, seconds=seconds, samples=out)
