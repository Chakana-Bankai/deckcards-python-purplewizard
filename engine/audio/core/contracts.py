"""Core audio contracts and shared types for Chakana Audio Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AudioKind = Literal["music", "sfx", "stinger", "ambient", "ui", "dialogue"]


@dataclass(frozen=True)
class AudioEvent:
    kind: AudioKind
    event_id: str
    context: str
    priority: int = 0
