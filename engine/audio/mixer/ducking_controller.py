"""Ducking policy with per-source aggregation."""

from __future__ import annotations


class DuckingController:
    def __init__(self):
        # target_bus -> {source: amount}
        self.active: dict[str, dict[str, float]] = {}

    def apply(self, target_bus: str, amount: float, source: str = "default") -> float:
        bus = str(target_bus or "").lower()
        src = str(source or "default").lower()
        val = max(0.0, min(1.0, float(amount)))
        bucket = self.active.setdefault(bus, {})
        bucket[src] = val
        return self.get_amount(bus)

    def clear(self, target_bus: str, source: str | None = None) -> None:
        bus = str(target_bus or "").lower()
        if bus not in self.active:
            return
        if source is None:
            self.active.pop(bus, None)
            return
        src = str(source or "default").lower()
        self.active[bus].pop(src, None)
        if not self.active[bus]:
            self.active.pop(bus, None)

    def get_amount(self, target_bus: str) -> float:
        bus = str(target_bus or "").lower()
        bucket = self.active.get(bus, {})
        if not bucket:
            return 0.0
        # strongest duck source wins
        return max(0.0, min(1.0, max(bucket.values())))

    def snapshot(self) -> dict[str, float]:
        return {bus: self.get_amount(bus) for bus in self.active}
