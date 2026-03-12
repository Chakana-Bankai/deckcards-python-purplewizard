from __future__ import annotations

from array import array
from pathlib import Path
import os

os.environ.setdefault('LIBROSA_DISABLE_NUMBA', '1')

import librosa
import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, Field


class AudioAssetSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    item_id: str
    item_type: str
    seconds: float = Field(gt=0.0)
    sample_rate: int = Field(gt=8000)
    channels: int = Field(default=1, ge=1, le=2)
    subtype: str = Field(default='PCM_16')


class AudioAnalysisReport(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    duration_seconds: float
    sample_rate: int
    channels: int
    peak_db: float
    rms_db: float
    tempo_bpm: float
    onset_count: int
    loop_end_seconds: float
    monotony_score: float
    variation_score: float
    librosa_available: bool
    analysis_mode: str


def write_wav_soundfile(path: Path, samples: array, sample_rate: int, *, channels: int = 1, subtype: str = 'PCM_16') -> None:
    spec = AudioAssetSpec(
        item_id=path.stem,
        item_type=path.parent.name,
        seconds=max(1.0 / sample_rate, len(samples) / float(sample_rate * max(1, channels))),
        sample_rate=sample_rate,
        channels=channels,
        subtype=subtype,
    )
    data = np.asarray(samples, dtype=np.int16)
    if spec.channels > 1:
        data = data.reshape((-1, spec.channels))
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), data, spec.sample_rate, subtype=spec.subtype)


def analyze_audio_file(path: Path) -> AudioAnalysisReport:
    info = sf.info(str(path))
    sample_rate = int(info.samplerate)
    channels = int(info.channels)
    max_analysis_seconds = 24.0
    max_frames = max(1, int(sample_rate * max_analysis_seconds))
    data, _ = sf.read(str(path), frames=max_frames, always_2d=False)
    if isinstance(data, np.ndarray) and data.ndim > 1:
        mono = data.mean(axis=1)
    else:
        mono = np.asarray(data, dtype=np.float32)
    mono = mono.astype(np.float32)
    duration_seconds = float(info.frames) / float(sample_rate) if sample_rate else 0.0
    if mono.size <= 0:
        return AudioAnalysisReport(
            duration_seconds=0.0,
            sample_rate=int(sample_rate),
            channels=channels,
            peak_db=-120.0,
            rms_db=-120.0,
            tempo_bpm=0.0,
            onset_count=0,
            loop_end_seconds=0.0,
            monotony_score=1.0,
            variation_score=0.0,
            librosa_available=True,
            analysis_mode='soundfile_fallback',
        )
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    peak_db = 20.0 * np.log10(max(1e-6, peak))
    rms_db = 20.0 * np.log10(max(1e-6, rms))
    envelope = np.abs(mono)
    window = max(32, sample_rate // 40)
    kernel = np.ones(window, dtype=np.float32) / float(window)
    smoothed = np.convolve(envelope, kernel, mode='same')
    delta = np.diff(smoothed, prepend=smoothed[0])
    onset_threshold = float(np.mean(delta) + np.std(delta) * 1.75)
    onset_indices = np.where(delta > onset_threshold)[0]
    min_gap = max(1, sample_rate // 8)
    filtered_onsets = []
    last = -min_gap
    for idx in onset_indices.tolist():
        if idx - last >= min_gap:
            filtered_onsets.append(idx)
            last = idx
    onset_count = len(filtered_onsets)
    tempo_bpm = float(onset_count * 60.0 / max(duration_seconds, 1e-6)) if onset_count else 0.0
    frame_length = max(256, sample_rate // 40)
    hop_length = max(128, frame_length // 2)
    frame_count = max(1, 1 + max(0, (len(mono) - frame_length) // hop_length))
    rms_frames = np.empty(frame_count, dtype=np.float32)
    for i in range(frame_count):
        start = i * hop_length
        frame = mono[start:start + frame_length]
        if frame.size == 0:
            rms_frames[i] = 0.0
        else:
            rms_frames[i] = float(np.sqrt(np.mean(np.square(frame))))
    variation_score = float(min(1.0, np.std(rms_frames) * 8.0)) if rms_frames.size else 0.0
    monotony_score = float(max(0.0, 1.0 - variation_score))
    active = np.where(rms_frames > (np.mean(rms_frames) * 0.35))[0]
    loop_end_seconds = float(((int(active[-1]) if active.size else max(0, frame_count - 1)) * hop_length) / sample_rate)
    _ = librosa.__version__
    return AudioAnalysisReport(
        duration_seconds=round(duration_seconds, 4),
        sample_rate=int(sample_rate),
        channels=channels,
        peak_db=round(peak_db, 4),
        rms_db=round(rms_db, 4),
        tempo_bpm=round(tempo_bpm, 4),
        onset_count=onset_count,
        loop_end_seconds=round(min(duration_seconds, max(0.0, loop_end_seconds)), 4),
        monotony_score=round(monotony_score, 4),
        variation_score=round(variation_score, 4),
        librosa_available=True,
        analysis_mode='soundfile_numpy_guarded_librosa',
    )
