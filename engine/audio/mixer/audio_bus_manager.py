"""Mixer bus ownership and profile application for Chakana audio runtime."""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_BUSES = ("master", "music", "sfx", "stingers", "ambient", "ui", "dialogue")


@dataclass
class AudioBusManager:
    levels: dict[str, float] = field(default_factory=lambda: {
        "master": 1.0,
        "music": 0.75,
        "sfx": 0.85,
        "stingers": 0.90,
        "ambient": 0.60,
        "ui": 0.80,
        "dialogue": 0.85,
    })

    def set_level(self, bus: str, value: float) -> float:
        b = str(bus or "").lower()
        v = max(0.0, min(1.0, float(value)))
        self.levels[b] = v
        return v

    def get_level(self, bus: str, default: float = 1.0) -> float:
        return float(self.levels.get(str(bus or "").lower(), default))

    def apply_profile(self, profile: dict[str, float]) -> dict[str, float]:
        if not isinstance(profile, dict):
            return dict(self.levels)
        for bus, val in profile.items():
            self.set_level(str(bus), float(val))
        for bus in DEFAULT_BUSES:
            self.levels.setdefault(bus, 1.0)
        return dict(self.levels)

    def snapshot(self) -> dict[str, float]:
        return dict(self.levels)
