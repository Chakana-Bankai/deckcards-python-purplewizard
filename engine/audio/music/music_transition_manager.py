"""Transition policy scaffold between music states."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionPolicy:
    default_fade_out_ms: int = 350
    default_fade_in_ms: int = 350
    boundary_aware: bool = True


class MusicTransitionManager:
    def __init__(self, policy: TransitionPolicy | None = None):
        self.policy = policy or TransitionPolicy()

    def resolve(self, from_state: str, to_state: str) -> dict[str, int | bool | str]:
        return {
            "from": from_state,
            "to": to_state,
            "fade_out_ms": self.policy.default_fade_out_ms,
            "fade_in_ms": self.policy.default_fade_in_ms,
            "boundary_aware": self.policy.boundary_aware,
        }
