from __future__ import annotations

import random

import pygame

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.ui.components.loading_widget import LoadingWidget


class LoadingScreen:
    def __init__(self, title_font, body_font, lang: str = "es"):
        self.title_font = title_font
        self.body_font = body_font
        self.label = "Iniciando..."
        self.pct = 0.0
        self.widget = LoadingWidget(self._load_hints(lang))
        self.particles = [{"x": random.randint(0, 1919), "y": random.randint(0, 1079), "vx": random.uniform(-10, 10), "vy": random.uniform(8, 20)} for _ in range(18)]


    def _load_hints(self, lang: str) -> list[str]:
        candidates = [f"hints_{str(lang or 'es').lower()}.json", "hints_es.json"]
        for name in candidates:
            payload = load_json(data_dir() / name, default=[])
            if not isinstance(payload, list):
                continue
            hints = [str(item.get("text", "")).strip() for item in payload if isinstance(item, dict)]
            hints = [h for h in hints if h]
            if hints:
                return hints
        return [
            "La Chakana representa los tres mundos del espíritu.",
            "Kay Pacha, Hanan Pacha y Ukhu Pacha giran en equilibrio.",
            "Cada símbolo abre un sendero en la Trama.",
        ]

    def set_step(self, label: str, pct: float):
        self.label = label
        self.pct = max(0.0, min(1.0, float(pct)))
        self.widget.set_hint(label)

    def draw(self, screen: pygame.Surface, dt: float = 0.016):
        w, h = screen.get_size()
        for y in range(h):
            t = y / max(1, h - 1)
            c = (int(14 + 20 * t), int(10 + 16 * t), int(28 + 26 * t))
            pygame.draw.line(screen, c, (0, y), (w, y))

        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] > h + 10:
                p["y"] = -10
            if p["x"] < -10:
                p["x"] = w + 10
            if p["x"] > w + 10:
                p["x"] = -10
            pygame.draw.circle(screen, (130, 120, 190), (int(p["x"]), int(p["y"])), 2)

        title = self.title_font.render("CARGANDO TRAMA", True, (236, 221, 158))
        screen.blit(title, title.get_rect(center=(w // 2, 160)))

        self.widget.tick(dt)
        self.widget.draw(screen, self.body_font, hint_text=None)


class DataLoadingScreen:
    def __init__(self, app, next_fn, duration: float = 1.6):
        self.app = app
        self.next_fn = next_fn
        self.duration = float(duration)
        self.t = 0.0

    def on_enter(self):
        self.t = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self.t = self.duration + 0.01

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration:
            self.next_fn()

    def render(self, surface):
        self.app.loading_screen.draw(surface, 1.0 / 60.0)
