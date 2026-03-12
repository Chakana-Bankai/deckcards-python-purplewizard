from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from random import Random

from game.audio.audio_depth_specs import load_audio_depth_specs

SAMPLE_RATE = 32000
MOTIF = [0, 2, 4, 2, 5, 4, 2, 0]
DENSITY_WEIGHTS = {
    'low': {'pad': 0.34, 'harmony': 0.18, 'melody': 0.20, 'bass': 0.12, 'percussion': 0.05, 'ornament': 0.07},
    'low_to_mid': {'pad': 0.30, 'harmony': 0.18, 'melody': 0.20, 'bass': 0.14, 'percussion': 0.08, 'ornament': 0.08},
    'mid': {'pad': 0.24, 'harmony': 0.18, 'melody': 0.22, 'bass': 0.16, 'percussion': 0.12, 'ornament': 0.08},
    'mid_to_high': {'pad': 0.20, 'harmony': 0.18, 'melody': 0.22, 'bass': 0.18, 'percussion': 0.16, 'ornament': 0.08},
    'high': {'pad': 0.16, 'harmony': 0.18, 'melody': 0.22, 'bass': 0.18, 'percussion': 0.20, 'ornament': 0.08},
}

@dataclass(frozen=True)
class LayeredThemeResult:
    context: str
    seconds: float
    samples: array
    layer_presence: dict[str, float]


def _triangle(phase: float) -> float:
    v = (phase / (2 * math.pi)) % 1.0
    return 4.0 * abs(v - 0.5) - 1.0


def _tempo_seconds(tempo_bpm: float) -> float:
    return 60.0 / max(1.0, tempo_bpm)


def build_layered_theme(context: str, *, seconds: float | None = None, seed: int = 0) -> LayeredThemeResult:
    specs = load_audio_depth_specs()
    spec = specs[context]
    seconds = float(seconds or spec['loop_length_seconds'])
    tempo = float(spec['tempo_bpm'])
    beat = _tempo_seconds(tempo)
    total = max(1, int(seconds * SAMPLE_RATE))
    density = DENSITY_WEIGHTS.get(str(spec['density']), DENSITY_WEIGHTS['mid'])
    roots = [110.0, 123.47, 138.59, 146.83, 164.81]
    rng = Random(abs(hash((context, seed, 'layered_theme_v2'))) % (2**31 - 1))
    rng.shuffle(roots)
    section = max(4.0, seconds / 4.0)
    phrase_len = len(MOTIF)
    motif_step = beat * (0.5 if 'combat' in context else 0.75)
    samples = array('h')
    prev = 0.0
    prev2 = 0.0

    for i in range(total):
        t = i / SAMPLE_RATE
        root = roots[int(t / section) % len(roots)]
        chord = (root, root * 1.25, root * 1.5)
        motif_idx = int(t / motif_step) % phrase_len
        melody_freq = root * (2 ** (MOTIF[motif_idx] / 12.0))
        beat_phase = (t / beat) % 1.0
        sub_phase = (t / (beat * 0.5)) % 1.0

        pad = density['pad'] * (
            0.62 * math.sin(2 * math.pi * chord[0] * t)
            + 0.24 * math.sin(2 * math.pi * chord[1] * t + 0.4)
            + 0.12 * math.sin(2 * math.pi * chord[2] * t + 1.2)
        )
        harmony = density['harmony'] * (
            0.55 * math.sin(2 * math.pi * (chord[1] * 0.5) * t)
            + 0.45 * math.sin(2 * math.pi * (chord[2] * 0.75) * t + 0.2)
        )
        melody = density['melody'] * (
            0.66 * math.sin(2 * math.pi * melody_freq * t + 0.18 * math.sin(t * 0.33))
            + 0.18 * math.sin(2 * math.pi * (melody_freq * 2.0) * t)
        )
        bass = density['bass'] * math.sin(2 * math.pi * (root * 0.5) * t + 0.08 * math.sin(t * 0.5))
        perc_env = 1.0 if beat_phase < 0.08 else (0.6 if sub_phase < 0.05 and density['percussion'] >= 0.12 else 0.0)
        percussion = density['percussion'] * perc_env * (
            0.7 * _triangle(2 * math.pi * 68.0 * t) + 0.3 * math.sin(2 * math.pi * 124.0 * t)
        )
        ornament_gate = 1.0 if ((motif_idx % 4 == 3) and beat_phase < 0.2) else 0.0
        ornament = density['ornament'] * ornament_gate * math.sin(2 * math.pi * (melody_freq * 1.5) * t + 0.6)

        x = pad + harmony + melody + bass + percussion + ornament
        x = 0.84 * x + 0.16 * prev
        x = 0.92 * x + 0.08 * prev2
        prev2 = prev
        prev = x
        fade_in = min(1.0, t / 1.2)
        fade_out = min(1.0, (seconds - t) / 0.75)
        amp = max(0.0, min(1.0, fade_in * fade_out))
        samples.append(int(max(-1.0, min(1.0, x * amp * 0.78)) * 32767))

    return LayeredThemeResult(context=context, seconds=seconds, samples=samples, layer_presence=density)
