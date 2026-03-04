from __future__ import annotations

import time


class TelemetryLogger:
    LEVELS = {"DEBUG": 10, "INFO": 20}

    def __init__(self, level: str = "INFO"):
        self.level = str(level or "INFO").upper()
        if self.level not in self.LEVELS:
            self.level = "INFO"

    def _enabled(self, level: str) -> bool:
        return self.LEVELS.get(level, 20) >= self.LEVELS.get(self.level, 20)

    def log(self, level: str, event: str, **fields):
        lvl = str(level or "INFO").upper()
        if not self._enabled(lvl):
            return
        ts = time.strftime("%H:%M:%S")
        payload = " ".join(f"{k}={fields[k]}" for k in sorted(fields.keys()))
        print(f"[telemetry][{lvl}] {ts} {event} {payload}".strip())

    def info(self, event: str, **fields):
        self.log("INFO", event, **fields)

    def debug(self, event: str, **fields):
        self.log("DEBUG", event, **fields)
