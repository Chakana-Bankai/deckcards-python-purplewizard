"""Ambient playback scaffold."""

from __future__ import annotations


class AmbientPlayer:
    def __init__(self):
        self.current: str | None = None

    def set_context(self, context_id: str) -> str:
        self.current = str(context_id or "")
        return self.current
