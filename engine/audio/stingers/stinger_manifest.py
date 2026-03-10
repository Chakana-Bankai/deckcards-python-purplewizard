"""Stinger manifest scaffold."""

from __future__ import annotations

from pathlib import Path
import json


class StingerManifest:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}

    def load(self) -> dict:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}
        return self.data
