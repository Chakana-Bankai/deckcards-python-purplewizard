from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import pygame

from game.core.paths import data_dir
from game.ui.system.layout import safe_area
from game.ui.system.typography import TITLE_FONT


class StudioIntroScreen:
    """Definitive cached arcane studio intro.

    Fast startup-safe signature sequence with skip and fallback.
    """

    MANIFEST_VERSION = "arcane_intro_v1"

    def __init__(self, app, next_fn, fade_in: float = 1.2, hold: float = 1.5, fade_out: float = 1.2):
        self.app = app
        self.next_fn = next_fn
        self.fade_in = float(fade_in)
        self.hold = float(hold)
        self.fade_out = float(fade_out)
        self.duration = 4.0
        self.t = 0.0
        self.variant = "A"
        self.seed = 0
        self.source = "generated"
        self.fallback_mode = False
        self._done = False
        self._logged_fallback = False
        self.particles = []
        self.dissolve = []
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

    def _pick_variant(self):
        force_refresh = bool(self.app.user_settings.get("force_regen_art", False))
        manifest = self._load_manifest()
        valid = (
            isinstance(manifest, dict)
            and manifest.get("version") == self.MANIFEST_VERSION
            and str(manifest.get("variant", "")) in {"A", "B", "C"}
        )
        if valid and not force_refresh:
            self.variant = str(manifest.get("variant"))
            self.seed = int(manifest.get("seed", 1337) or 1337)
            self.duration = float(manifest.get("duration", 4.0) or 4.0)
            self.source = "cache"
            print("[studio_intro] source=cache")
            return

        self.variant = random.choice(["A", "B", "C"])
        self.seed = int(time.time()) % 100000
        self.duration = {"A": 4.0, "B": 4.2, "C": 3.9}.get(self.variant, 4.0)
        self.source = "generated"
        self._save_manifest(
            {
                "version": self.MANIFEST_VERSION,
                "variant": self.variant,
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
        self._pick_variant()
        rng = random.Random(self.seed)

        self.particles = [
            {
                "x": rng.uniform(0, 1920),
                "y": rng.uniform(0, 1080),
                "vx": rng.uniform(-0.22, 0.22),
                "vy": rng.uniform(-0.18, 0.18),
                "r": rng.randint(1, 2),
            }
            for _ in range(40)
        ]
        self.dissolve = [
            {
                "a": rng.uniform(0, math.tau),
                "sp": rng.uniform(28.0, 78.0),
                "r": rng.randint(1, 2),
            }
            for _ in range(56)
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
            c = (int(2 + 8 * p), int(2 + 7 * p), int(8 + 18 * p))
            pygame.draw.line(surface, c, (0, y), (w, y))

    def _draw_energy_point(self, surface: pygame.Surface, cx: int, cy: int):
        if self.t < 0.18:
            return
        phase = pygame.time.get_ticks() / 220.0
        pulse = 0.5 + 0.5 * math.sin(phase)
        rr = int(5 + 5 * pulse)
        glow = pygame.Surface((84, 84), pygame.SRCALPHA)
        pygame.draw.circle(glow, (142, 94, 240, 128), (42, 42), 18 + rr)
        pygame.draw.circle(glow, (136, 220, 250, 92), (42, 42), 8 + rr // 2)
        surface.blit(glow, (cx - 42, cy - 42))
        pygame.draw.circle(surface, (232, 218, 255), (cx, cy), max(2, rr // 3))

    def _draw_chakana_geometry(self, surface: pygame.Surface, cx: int, cy: int, progress: float):
        p = max(0.0, min(1.0, progress))
        if p <= 0.0:
            return
        size = 124
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
        col = (170, 124, 255)
        for i in range(min(full, len(segs))):
            pygame.draw.line(surface, col, segs[i][0], segs[i][1], 2)
        if full < len(segs):
            a, b = segs[full]
            x = int(a[0] + (b[0] - a[0]) * rem)
            y = int(a[1] + (b[1] - a[1]) * rem)
            pygame.draw.line(surface, col, a, (x, y), 2)

        ring = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(ring, (110, 82, 182, 70), (210, 210), int(138 + 16 * p), 2)
        pygame.draw.circle(ring, (132, 208, 240, 64), (210, 210), int(84 + 8 * p), 1)
        surface.blit(ring, (cx - 210, cy - 210))

    def _draw_wizard(self, surface: pygame.Surface, cx: int, cy: int, alpha: int):
        if alpha <= 0:
            return
        avatar = self.app.assets.sprite("avatar", "menu", (228, 228), fallback=(86, 56, 132)).copy()
        tint = pygame.Surface(avatar.get_size(), pygame.SRCALPHA)
        tint.fill((84, 34, 156, 116))
        avatar.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        avatar.set_alpha(alpha)
        rect = avatar.get_rect(center=(cx, cy + 30))
        surface.blit(avatar, rect.topleft)

        # Hologram scanlines
        holo = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        for y in range(0, rect.h, 4):
            pygame.draw.line(holo, (154, 222, 242, max(8, alpha // 16)), (0, y), (rect.w, y), 1)
        surface.blit(holo, rect.topleft)

        # staff lift pulse around right hand area
        pulse_t = (self.t - 2.35) / 0.45
        if 0.0 <= pulse_t <= 1.2:
            pulse = max(0.0, min(1.0, pulse_t))
            px = rect.centerx + 42
            py = rect.centery - 18
            g = pygame.Surface((120, 120), pygame.SRCALPHA)
            pr = int(10 + 34 * pulse)
            pygame.draw.circle(g, (238, 210, 130, int(alpha * 0.28)), (60, 60), pr)
            pygame.draw.circle(g, (126, 220, 250, int(alpha * 0.24)), (60, 60), max(2, pr // 2))
            surface.blit(g, (px - 60, py - 60))

    def _draw_dissolve_particles(self, surface: pygame.Surface, cx: int, cy: int):
        t0 = 3.45
        if self.t < t0:
            return
        p = min(1.0, (self.t - t0) / 0.55)
        for d in self.dissolve:
            dist = d["sp"] * p
            x = int(cx + math.cos(d["a"]) * dist)
            y = int(cy + 30 + math.sin(d["a"]) * dist)
            a = int(180 * (1.0 - p))
            pygame.draw.circle(surface, (180, 146, 240, a), (x, y), int(d["r"]))

    def _draw_logo(self, surface: pygame.Surface, cx: int, cy: int, alpha: int):
        if alpha <= 0:
            return
        base_size = max(74, int(self.app.big_font.get_height() * 2.0))
        title_font = self.app.typography.get(TITLE_FONT, base_size)
        text = title_font.render("CHAKANA STUDIO", True, (246, 244, 255))
        title = pygame.Surface(text.get_size(), pygame.SRCALPHA)
        title.blit(text, (0, 0))
        title.set_alpha(alpha)

        glow = pygame.Surface((text.get_width() + 40, text.get_height() + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (116, 84, 182, min(70, alpha // 3)), glow.get_rect(), border_radius=12)
        surface.blit(glow, (cx - glow.get_width() // 2, cy - text.get_height() // 2 - 10))
        surface.blit(title, title.get_rect(center=(cx, cy)))

        sub = self.app.small_font.render("Purple Wizard Engine", True, (178, 206, 238))
        sub_s = pygame.Surface(sub.get_size(), pygame.SRCALPHA)
        sub_s.blit(sub, (0, 0))
        sub_s.set_alpha(int(alpha * 0.86))
        surface.blit(sub_s, sub_s.get_rect(center=(cx, cy + 46)))

    def _render_static_fallback(self, surface: pygame.Surface):
        w, h = surface.get_size()
        self._draw_bg(surface, w, h)
        area = safe_area(w, h, 20, 20)
        base_size = max(72, int(self.app.big_font.get_height() * 2.0))
        title_font = self.app.typography.get(TITLE_FONT, base_size)
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

            # Ambient particles
            phase = pygame.time.get_ticks() / 1000.0
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
                pygame.draw.circle(surface, (136, 132, 186), (int(p["x"]), int(p["y"])), int(p["r"]))

            self._draw_energy_point(surface, cx, cy)

            g_start, g_end = 0.6, 1.5
            g_prog = (self.t - g_start) / max(0.001, (g_end - g_start))
            if self.variant == "A":
                g_prog *= 1.12
            self._draw_chakana_geometry(surface, cx, cy, g_prog)

            w_start, w_end = 1.8, 3.6
            if self.variant == "B":
                w_start = 1.65
                w_end = 3.7
            if self.t < w_start:
                w_alpha = 0
            elif self.t <= 2.7:
                w_alpha = int(190 * min(1.0, (self.t - w_start) / max(0.001, (2.7 - w_start))))
            else:
                w_alpha = int(190 * max(0.0, 1.0 - (self.t - 2.7) / max(0.001, (w_end - 2.7))))
            self._draw_wizard(surface, cx, cy, w_alpha)

            l_start, l_end = 2.8, 4.0
            if self.variant == "C":
                l_start = 2.65
            l_alpha = int(255 * max(0.0, min(1.0, (self.t - l_start) / max(0.001, (l_end - l_start)))))
            self._draw_logo(surface, cx, cy, l_alpha)

            self._draw_dissolve_particles(surface, cx, cy)

            # Final fade out to menu
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
