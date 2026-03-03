from __future__ import annotations

import pygame


class TypewriterBanner:
    def __init__(self):
        self.full_text: str = ""
        self.visible_text: str = ""
        self.index: int = 0
        self.timer: float = 0.0
        self.is_done: bool = True
        self.active: bool = False
        self.cps: float = 35.0
        self.duration: float = 2.2

    @property
    def current(self) -> str:
        return self.visible_text

    def set_text(self, text: str, reset: bool = True, duration: float | None = None, cps: float | None = None):
        self.full_text = str(text or "")
        if duration is not None:
            self.duration = max(0.1, float(duration))
        if cps is not None:
            self.cps = max(1.0, float(cps))

        if reset:
            self.index = 0
            self.timer = 0.0
            self.visible_text = ""

        if not self.full_text:
            self.is_done = True
            self.active = False
            self.visible_text = ""
            return

        self.is_done = False
        self.active = True

    def set(self, text: str, duration: float = 2.2):
        cps = max(1.0, len(str(text or "")) / max(0.1, duration)) if text else self.cps
        self.set_text(text, reset=True, duration=duration, cps=cps)

    def update(self, dt: float):
        if not self.active or self.is_done:
            return
        self.timer += max(0.0, float(dt))
        target_idx = min(len(self.full_text), int(self.timer * self.cps))
        if target_idx != self.index:
            self.index = target_idx
            self.visible_text = self.full_text[: self.index]
        if self.index >= len(self.full_text):
            self.visible_text = self.full_text
            self.is_done = True
            self.active = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, pos: tuple[int, int], color=(245, 245, 250)):
        txt = self.visible_text if self.visible_text else (self.full_text if self.is_done else "")
        if not txt:
            return
        surface.blit(font.render(txt, True, color), pos)

    def alpha(self) -> int:
        if not self.full_text:
            return 0
        if self.is_done:
            return 255
        t = max(0.0, min(1.0, self.timer / max(0.1, self.duration)))
        return int(255 * min(1.0, 0.3 + t * 0.7))
