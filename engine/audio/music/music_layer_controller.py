"""Layer activation scaffold for context/intensity based music."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LayerState:
    pad: bool = True
    bass: bool = True
    melody: bool = False
    percussion: bool = False
    fx: bool = False


@dataclass
class MusicLayerController:
    intensity: float = 0.25
    layers: LayerState = field(default_factory=LayerState)

    def set_intensity(self, value: float) -> LayerState:
        self.intensity = max(0.0, min(1.0, float(value)))
        self.layers.melody = self.intensity >= 0.35
        self.layers.percussion = self.intensity >= 0.55
        self.layers.fx = self.intensity >= 0.75
        return self.layers
