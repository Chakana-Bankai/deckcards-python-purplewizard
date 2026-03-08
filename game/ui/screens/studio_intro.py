from __future__ import annotations

import json
import math
import random
import time

import pygame

from game.core.paths import data_dir
from game.ui.system.layout import safe_area
from game.ui.system.typography import TITLE_FONT


class StudioIntroScreen:
    """Clean cached studio intro with white Chakana reveal and subtle purple FX."""

    MANIFEST_VERSION = "identity_feedback_intro_v1"

    def __init__(self, app, next_fn, fade_in: float = 1.2, hold: float = 1.5, fade_out: float = 1.2):
        self.app = app
        self.next_fn = next_fn
        self.fade_in = float(fade_in)
        self.hold = float(hold)
        self.fade_out = float(fade_out)
        self.duration = 4.1
        self.t = 0.0
        self.source = "generated"
        self.seed = 1337
        self._done = False
        self._logged_fallback = False
        self.fallback_mode = False
        self.particles = []
        self.manifest_path = data_dir() / "studio_intro_manifest.json"

    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _save_manifest(self, payload: dict):
        try:
            self.manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _prepare_cached_timeline(self):
        force_refresh = bool(self.app.user_settings.get("force_regen_art", False))
        manifest = self._load_manifest()
        valid = isinstance(manifest, dict) and manifest.get("version") == self.MANIFEST_VERSION
        if valid and not force_refresh:
            self.seed = int(manifest.get("seed", 1337) or 1337)
            self.duration = float(manifest.get("duration", 4.1) or 4.1)
            self.source = "cache"
            print("[studio_intro] source=cache")
            return

        self.seed = int(time.time()) % 100000
        self.duration = 4.1
        self.source = "generated"
        self._save_manifest(
            {
                "version": self.MANIFEST_VERSION,
                "seed": self.seed,
                "duration": self.duration,
                "updated_at": int(time.time()),
            }
        )
        print("[studio_intro] visual=generated")

    def on_enter(self):
        self.t = 0.0
        self._done = False
        self.fallback_mode = False
        self._logged_fallback = False
        self._prepare_cached_timeline()

        rng = random.Random(self.seed)
        self.particles = [
            {
                "x": rng.uniform(0, 1920),
                "y": rng.uniform(0, 1080),
                "vx": rng.uniform(-0.12, 0.12),
                "vy": rng.uniform(-0.09, 0.09),
                "r": rng.randint(1, 2),
            }
            for _ in range(34)
        ]

        try:
            if hasattr(self.app, "sfx"):
                self.app.sfx.play("studio_intro")
            print("[studio_intro] audio=ok")
        except Exception:
            print("[studio_intro] audio=missing")

    def _finish(self):
        if self._done:
            return
        self._done = True
        self.next_fn()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self._finish()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in {1, 2, 3}:
            self._finish()
            return

    def update(self, dt):
        self.t += max(0.0, float(dt or 0.0))
        if self.t >= self.duration:
            self._finish()

    def _draw_bg(self, surface: pygame.Surface, w: int, h: int):
        for y in range(h):
            p = y / max(1, h - 1)
            c = (0, 0, int(2 + 8 * p))
            pygame.draw.line(surface, c, (0, y), (w, y))

    def _draw_particles(self, surface: pygame.Surface, w: int, h: int):
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < -8:
                p["x"] = w + 8
            if p["x"] > w + 8:
                p["x"] = -8
            if p["y"] < -8:
                p["y"] = h + 8
            if p["y"] > h + 8:
                p["y"] = -8
            pygame.draw.circle(surface, (112, 88, 168), (int(p["x"]), int(p["y"])), int(p["r"]))

    def _draw_energy_point(self, surface: pygame.Surface, cx: int, cy: int):
        if self.t < 0.20:
            return
        phase = pygame.time.get_ticks() / 230.0
        pulse = 0.5 + 0.5 * math.sin(phase)
        rr = int(4 + 4 * pulse)
        glow = pygame.Surface((72, 72), pygame.SRCALPHA)
        pygame.draw.circle(glow, (150, 104, 230, 76), (36, 36), 14 + rr)
        pygame.draw.circle(glow, (255, 255, 255, 58), (36, 36), 5 + rr // 2)
        surface.blit(glow, (cx - 36, cy - 36))
        pygame.draw.circle(surface, (250, 250, 255), (cx, cy), max(2, rr // 2))

    def _draw_chakana(self, surface: pygame.Surface, cx: int, cy: int):
        start, end = 0.45, 2.00
        p = max(0.0, min(1.0, (self.t - start) / max(0.001, end - start)))
        if p <= 0.0:
            return

        size = 112
        segs = [
            ((cx - size, cy), (cx + size, cy)),
            ((cx, cy - size), (cx, cy + size)),
            ((cx - size // 2, cy - size // 2), (cx + size // 2, cy - size // 2)),
            ((cx - size // 2, cy + size // 2), (cx + size // 2, cy + size // 2)),
            ((cx - size // 2, cy - size // 2), (cx - size // 2, cy + size // 2)),
            ((cx + size // 2, cy - size // 2), (cx + size // 2, cy + size // 2)),
        ]
        k = p * len(segs)
        full = int(k)
        rem = k - full
        col = (246, 246, 255)
        for i in range(min(full, len(segs))):
            pygame.draw.line(surface, col, segs[i][0], segs[i][1], 2)
        if full < len(segs):
            a, b = segs[full]
            x = int(a[0] + (b[0] - a[0]) * rem)
            y = int(a[1] + (b[1] - a[1]) * rem)
            pygame.draw.line(surface, col, a, (x, y), 2)

        # Subtle purple energy around symbol.
        ring = pygame.Surface((360, 360), pygame.SRCALPHA)
        energy = int(30 + 28 * p)
        pygame.draw.circle(ring, (130, 86, 212, energy), (180, 180), int(134 - 8 * p), 2)
        surface.blit(ring, (cx - 180, cy - 180))

    def _draw_symbol_dissolve(self, surface: pygame.Surface, cx: int, cy: int):
        start = 2.05
        if self.t < start:
            return
        p = max(0.0, min(1.0, (self.t - start) / 0.75))
        mask = pygame.Surface((320, 320), pygame.SRCALPHA)
        alpha = int(180 * p)
        pygame.draw.circle(mask, (0, 0, 0, alpha), (160, 160), int(46 + 112 * p))
        surface.blit(mask, (cx - 160, cy - 160))

    def _draw_logo(self, surface: pygame.Surface, cx: int, cy: int):
        start = 2.55
        alpha = int(255 * max(0.0, min(1.0, (self.t - start) / 0.85)))
        if alpha <= 0:
            return

        title_font = self.app.typography.get(TITLE_FONT, max(74, int(self.app.big_font.get_height() * 2.0)))
        text = title_font.render("CHAKANA STUDIO", True, (250, 250, 255))
        gl = pygame.Surface((text.get_width() + 30, text.get_height() + 22), pygame.SRCALPHA)
        pygame.draw.rect(gl, (126, 92, 196, min(66, alpha // 4)), gl.get_rect(), border_radius=10)
        surface.blit(gl, (cx - gl.get_width() // 2, cy - text.get_height() // 2 - 10))

        title = pygame.Surface(text.get_size(), pygame.SRCALPHA)
        title.blit(text, (0, 0))
        title.set_alpha(alpha)
        surface.blit(title, title.get_rect(center=(cx, cy + 2)))

    def _render_static_fallback(self, surface: pygame.Surface):
        w, h = surface.get_size()
        self._draw_bg(surface, w, h)
        area = safe_area(w, h, 20, 20)
        title_font = self.app.typography.get(TITLE_FONT, max(72, int(self.app.big_font.get_height() * 2.0)))
        label = title_font.render("CHAKANA STUDIO", True, (245, 245, 252))
        surface.blit(label, label.get_rect(center=(area.centerx, area.centery)))

    def render(self, surface):
        if self.fallback_mode:
            self._render_static_fallback(surface)
            return

        try:
            w, h = surface.get_size()
            area = safe_area(w, h, 20, 20)
            cx, cy = area.centerx, area.centery
            self._draw_bg(surface, w, h)
            self._draw_particles(surface, w, h)
            self._draw_energy_point(surface, cx, cy)
            self._draw_chakana(surface, cx, cy)
            self._draw_symbol_dissolve(surface, cx, cy)
            self._draw_logo(surface, cx, cy)

            # Minimal fade out tail.
            tail = max(0.0, min(1.0, (self.t - (self.duration - 0.45)) / 0.45))
            if tail > 0:
                fade = pygame.Surface((w, h), pygame.SRCALPHA)
                fade.fill((0, 0, 0, int(220 * tail)))
                surface.blit(fade, (0, 0))

        except Exception:
            self.fallback_mode = True
            if not self._logged_fallback:
                self._logged_fallback = True
                print("[studio_intro] fallback=static_logo")
            self._render_static_fallback(surface)
