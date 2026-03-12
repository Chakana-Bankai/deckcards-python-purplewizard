"""Music state machine for Chakana runtime integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MusicState = Literal[
    "menu",
    "map",
    "combat",
    "boss",
    "shop",
    "reward",
    "dialogue",
    "codex",
    "credits",
    "defeat",
    "victory",
]


@dataclass
class TransitionRequest:
    target: MusicState
    fade_out_ms: int = 350
    fade_in_ms: int = 350


class MusicStateMachine:
    def __init__(self, initial: MusicState = "menu"):
        self.current: MusicState = initial

    def transition(self, req: TransitionRequest) -> MusicState:
        if req.target not in {
            "menu",
            "map",
            "combat",
            "boss",
            "shop",
            "reward",
            "dialogue",
            "codex",
            "credits",
            "defeat",
            "victory",
        }:
            raise ValueError(f"unsupported_music_state:{req.target}")
        self.current = req.target
        return self.current
