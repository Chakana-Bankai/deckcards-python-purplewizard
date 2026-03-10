"""Manifest adapter scaffold for music state-to-track resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class MusicTrackRef:
    state: str
    track_id: str
    file_path: str
    layers: tuple[str, ...] = ()


class MusicManifest:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}

    def load(self) -> dict:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}
        return self.data

    def resolve(self, state: str) -> MusicTrackRef | None:
        items = self.data.get("items", {}) if isinstance(self.data, dict) else {}
        row = items.get(state)
        if not isinstance(row, dict):
            return None
        return MusicTrackRef(
            state=state,
            track_id=str(row.get("track_id", state)),
            file_path=str(row.get("path", "")),
            layers=tuple(row.get("layers", []) or []),
        )
