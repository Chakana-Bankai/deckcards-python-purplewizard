"""Stinger playback scaffold for overlay one-shots."""

from __future__ import annotations


class StingerPlayer:
    def __init__(self):
        self.last: str | None = None

    def play(self, stinger_id: str) -> str:
        self.last = str(stinger_id or "")
        return self.last
