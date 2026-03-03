from __future__ import annotations


class TypewriterBanner:
    def __init__(self):
        self.text = ""
        self.timer = 0.0
        self.duration = 0.0

    def set(self, text: str, duration: float = 2.2):
        self.text = text
        self.timer = duration
        self.duration = duration

    def update(self, dt: float):
        self.timer = max(0.0, self.timer - dt)

    def visible_text(self) -> str:
        if self.timer <= 0 or not self.text:
            return ""
        elapsed = self.duration - self.timer
        chars = int(elapsed * 35)
        return self.text[: max(1, chars)]

    def alpha(self) -> int:
        if self.timer <= 0:
            return 0
        t = self.timer / self.duration
        return int(255 * min(1.0, 1.5 * t))
