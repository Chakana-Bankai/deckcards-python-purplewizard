from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict

from game.audio.audio_stack_tools import analyze_audio_file


class LoopRefinementReport(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_path: str
    target_path: str
    duration_seconds: float
    refined_duration_seconds: float
    trim_seconds: float
    tempo_bpm: float
    variation_score: float
    fade_seconds: float
    loop_smoothness_before: float
    loop_smoothness_after: float


def _rms_frames(mono: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    frame_count = max(1, 1 + max(0, (len(mono) - frame_length) // hop_length))
    values = np.empty(frame_count, dtype=np.float32)
    for i in range(frame_count):
        start = i * hop_length
        frame = mono[start:start + frame_length]
        values[i] = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
    return values


def _pick_trim_seconds(duration_seconds: float, tempo_bpm: float, rms_frames: np.ndarray, sample_rate: int, hop_length: int) -> float:
    analysis_window = min(duration_seconds, 24.0)
    beat_seconds = 60.0 / tempo_bpm if tempo_bpm > 1.0 else 0.75
    half_beat = max(0.18, beat_seconds / 2.0)
    target = min(duration_seconds - 0.25, analysis_window)
    search_start = max(8.0, target - beat_seconds * 2.0)
    search_end = min(duration_seconds - 0.12, target + beat_seconds * 1.5)

    start_idx = max(0, int(search_start * sample_rate / hop_length))
    end_idx = min(len(rms_frames), max(start_idx + 1, int(search_end * sample_rate / hop_length)))
    window = rms_frames[start_idx:end_idx]
    if window.size == 0:
        return max(4.0, target)

    local_floor = float(np.percentile(window, 25))
    candidates = []
    for idx in range(start_idx, end_idx):
        sec = idx * hop_length / float(sample_rate)
        if sec <= search_start or sec >= search_end:
            continue
        energy = float(rms_frames[idx])
        proximity = abs(sec - target)
        beat_offset = abs(((sec - search_start) / half_beat) - round((sec - search_start) / half_beat))
        score = energy * 3.5 + proximity * 0.55 + beat_offset * 0.25
        if energy <= local_floor * 1.35:
            score *= 0.7
        candidates.append((score, sec))

    if not candidates:
        return max(4.0, target)
    return max(4.0, min(duration_seconds - 0.08, min(candidates)[1]))


def refine_runtime_loop(source_path: Path, target_path: Path, *, fade_seconds: float = 0.12) -> LoopRefinementReport:
    info = sf.info(str(source_path))
    sample_rate = int(info.samplerate)
    data, _ = sf.read(str(source_path), always_2d=True)
    mono = data.mean(axis=1).astype(np.float32)
    analysis = analyze_audio_file(source_path)

    frame_length = max(512, sample_rate // 20)
    hop_length = max(256, frame_length // 2)
    rms = _rms_frames(mono, frame_length, hop_length)
    trim_seconds = _pick_trim_seconds(float(info.frames) / float(sample_rate), analysis.tempo_bpm, rms, sample_rate, hop_length)
    trim_frames = min(len(data), max(1, int(trim_seconds * sample_rate)))
    trimmed = np.array(data[:trim_frames], copy=True)

    fade_frames = min(trim_frames, max(64, int(sample_rate * fade_seconds)))
    if fade_frames > 1:
        envelope = np.linspace(1.0, 0.0, fade_frames, dtype=np.float32)
        trimmed[-fade_frames:, :] *= envelope[:, None]

    target_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(target_path), trimmed, sample_rate, subtype=info.subtype or 'PCM_16')

    before_gap = max(0.0, analysis.duration_seconds - analysis.loop_end_seconds)
    before_smoothness = max(0.0, 1.0 - min(1.0, before_gap / max(1.0, analysis.duration_seconds)))
    refined_duration = trim_frames / float(sample_rate)
    after_gap = max(0.0, refined_duration - max(0.0, refined_duration - fade_seconds))
    after_smoothness = max(0.0, 1.0 - min(1.0, after_gap / max(1.0, refined_duration)))

    return LoopRefinementReport(
        source_path=source_path.as_posix(),
        target_path=target_path.as_posix(),
        duration_seconds=round(analysis.duration_seconds, 4),
        refined_duration_seconds=round(refined_duration, 4),
        trim_seconds=round(trim_seconds, 4),
        tempo_bpm=analysis.tempo_bpm,
        variation_score=analysis.variation_score,
        fade_seconds=round(fade_seconds, 4),
        loop_smoothness_before=round(before_smoothness, 4),
        loop_smoothness_after=round(after_smoothness, 4),
    )
