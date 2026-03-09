from __future__ import annotations

import json
import math
import random
import time

import pygame

from game.core.paths import data_dir, assets_dir
from game.ui.system.layout import safe_area
from game.ui.system.typography import TITLE_FONT


class StudioIntroScreen:
    """Minimal cosmic studio intro with cached starfield and Chakana line reveal."""

    MANIFEST_VERSION = "studio_intro_cosmic_v2"

    def __init__(self, app, next_fn, fade_in: float = 1.2, hold: float = 1.5, fade_out: float = 1.2):
        self.app = app
        self.next_fn = next_fn
        self.fade_in = float(fade_in)
        self.hold = float(hold)
        self.fade_out = float(fade_out)
        self.duration = 4.0
        self.t = 0.0
        self.source = "generated"
        self.seed = 1337
        self._done = False
        self._logged_fallback = False
        self.fallback_mode = False
        self.manifest_path = data_dir() / "studio_intro_manifest.json"

        self.stars_far = []
        self.stars_near = []
        self.purple_dust = []
        self._curated_logo = None
        self._curated_emblem = None
        self._curated_glyph = None

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

    def _load_curated_brand_assets(self):
        croot = assets_dir() / "curated" / "studio"
        self._curated_logo = None
        self._curated_emblem = None
        self._curated_glyph = None
        try:
            logo = croot / "chakana_studio_logo.png"
            emblem = croot / "chakana_emblem.png"
            glyph = croot / "chakana_loading_glyph.png"
            if logo.exists():
                self._curated_logo = pygame.image.load(str(logo)).convert_alpha()
            if emblem.exists():
                self._curated_emblem = pygame.image.load(str(emblem)).convert_alpha()
            if glyph.exists():
                self._curated_glyph = pygame.image.load(str(glyph)).convert_alpha()
        except Exception:
            self._curated_logo = None
            self._curated_emblem = None
            self._curated_glyph = None

    def _prepare_cached_timeline(self):
        force_refresh = bool(self.app.user_settings.get("force_regen_art", False))
        manifest = self._load_manifest()
        valid = isinstance(manifest, dict) and manifest.get("version") == self.MANIFEST_VERSION
        if valid and not force_refresh:
            self.seed = int(manifest.get("seed", 1337) or 1337)
            self.duration = float(manifest.get("duration", 4.0) or 4.0)
            self.source = "cache"
            print("[studio_intro] source=cache")
            return

        self.seed = int(time.time()) % 100000
        self.duration = 4.0
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
        self._load_curated_brand_assets()

        rng = random.Random(self.seed)
        # Cached starfield assets: generated once per enter/seed, then reused each frame.
        self.stars_far = [
            {
                "x": rng.uniform(0, 1920),
                "y": rng.uniform(0, 1080),
                "s": rng.uniform(0.08, 0.18),
                "a": rng.randint(90, 150),
                "tw": rng.uniform(0.0, math.tau),
            }
            for _ in range(140)
        ]
        self.stars_near = [
            {
                "x": rng.uniform(0, 1920),
                "y": rng.uniform(0, 1080),
                "s": rng.uniform(0.20, 0.42),
                "a": rng.randint(130, 210),
                "tw": rng.uniform(0.0, math.tau),
            }
            for _ in range(72)
        ]
        self.purple_dust = [
            {
                "x": rng.uniform(0, 1920),
                "y": rng.uniform(0, 1080),
                "vx": rng.uniform(-0.03, 0.03),
                "vy": rng.uniform(-0.02, 0.02),
                "a": rng.randint(16, 36),
            }
            for _ in range(24)
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
        surface.fill((2, 2, 4))
        # Optional subtle purple nebula tint, very soft and sparse.
        nebula = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(nebula, (88, 44, 128, 12), (int(w * 0.10), int(h * 0.18), int(w * 0.46), int(h * 0.34)))
        pygame.draw.ellipse(nebula, (74, 40, 120, 10), (int(w * 0.54), int(h * 0.42), int(w * 0.34), int(h * 0.26)))
        surface.blit(nebula, (0, 0))

    def _draw_starfield(self, surface: pygame.Surface, w: int, h: int):
        t = self.t
        stars = pygame.Surface((w, h), pygame.SRCALPHA)

        # Slow parallax movement and gentle twinkle.
        for st in self.stars_far:
            x = (st["x"] - t * 3.0 * st["s"]) % (w + 8) - 4
            y = (st["y"] + t * 1.6 * st["s"]) % (h + 8) - 4
            tw = 0.5 + 0.5 * math.sin(t * 0.9 + st["tw"])
            a = int(st["a"] * (0.72 + 0.28 * tw))
            pygame.draw.circle(stars, (220, 224, 236, max(0, min(255, a))), (int(x), int(y)), 1)

        for st in self.stars_near:
            x = (st["x"] - t * 7.5 * st["s"]) % (w + 8) - 4
            y = (st["y"] + t * 3.2 * st["s"]) % (h + 8) - 4
            tw = 0.5 + 0.5 * math.sin(t * 1.5 + st["tw"])
            a = int(st["a"] * (0.70 + 0.30 * tw))
            pygame.draw.circle(stars, (244, 246, 250, max(0, min(255, a))), (int(x), int(y)), 1)

        dust = pygame.Surface((w, h), pygame.SRCALPHA)
        for p in self.purple_dust:
            px = (p["x"] + t * 5.0 * p["vx"]) % w
            py = (p["y"] + t * 5.0 * p["vy"]) % h
            pygame.draw.circle(dust, (126, 84, 176, p["a"]), (int(px), int(py)), 1)

        surface.blit(stars, (0, 0))
        surface.blit(dust, (0, 0))

    def _draw_center_circles(self, surface: pygame.Surface, cx: int, cy: int):
        # Circle formation starts after cosmic calm phase.
        start = 1.05
        p = max(0.0, min(1.0, (self.t - start) / 1.05))
        if p <= 0.0:
            return

        ring_spec = [
            (64, (238, 238, 246), 1),
            (92, (240, 240, 248), 1),
            (122, (242, 242, 250), 1),
            (150, (188, 164, 230), 1),
        ]
        for idx, (base_r, col, thick) in enumerate(ring_spec):
            local = max(0.0, min(1.0, p * 1.1 - idx * 0.12))
            if local <= 0:
                continue
            rr = int(base_r * (0.78 + 0.22 * local))
            alpha = int(190 * local)
            ring = pygame.Surface((rr * 2 + 10, rr * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*col, alpha), (ring.get_width() // 2, ring.get_height() // 2), rr, thick)
            surface.blit(ring, (cx - ring.get_width() // 2, cy - ring.get_height() // 2))

    def _draw_chakana_symbol(self, surface: pygame.Surface, cx: int, cy: int):
        # Simple clean symbol, line-trace draw inspired by loading icon language.
        start = 1.55
        end = 2.55
        p = max(0.0, min(1.0, (self.t - start) / max(0.001, end - start)))
        if p <= 0.0:
            return

        size = 64
        segs = [
            ((cx - size, cy), (cx + size, cy)),
            ((cx, cy - size), (cx, cy + size)),
            ((cx - size // 2, cy - size // 2), (cx + size // 2, cy - size // 2)),
            ((cx - size // 2, cy + size // 2), (cx + size // 2, cy + size // 2)),
            ((cx - size // 2, cy - size // 2), (cx - size // 2, cy + size // 2)),
            ((cx + size // 2, cy - size // 2), (cx + size // 2, cy + size // 2)),
            ((cx - size // 4, cy - size // 4), (cx + size // 4, cy - size // 4)),
            ((cx - size // 4, cy + size // 4), (cx + size // 4, cy + size // 4)),
            ((cx - size // 4, cy - size // 4), (cx - size // 4, cy + size // 4)),
            ((cx + size // 4, cy - size // 4), (cx + size // 4, cy + size // 4)),
        ]

        k = p * len(segs)
        full = int(k)
        rem = k - full

        for i in range(min(full, len(segs))):
            pygame.draw.line(surface, (250, 250, 255), segs[i][0], segs[i][1], 1)
        if full < len(segs):
            a, b = segs[full]
            x = int(a[0] + (b[0] - a[0]) * rem)
            y = int(a[1] + (b[1] - a[1]) * rem)
            pygame.draw.line(surface, (250, 250, 255), a, (x, y), 1)

        curated = self._curated_emblem or self._curated_glyph
        if curated is not None:
            target = max(84, int(size * 1.8))
            icon = pygame.transform.smoothscale(curated, (target, target)).copy()
            icon.set_alpha(int(190 * p))
            surface.blit(icon, icon.get_rect(center=(cx, cy)).topleft)

    def _draw_title(self, surface: pygame.Surface, cx: int, cy: int):
        # Symbol fades slightly while text appears.
        start = 2.45
        alpha = int(255 * max(0.0, min(1.0, (self.t - start) / 0.85)))
        if alpha <= 0:
            return

        title_font = self.app.typography.get(TITLE_FONT, max(72, int(self.app.big_font.get_height() * 1.95)))
        text = title_font.render("CHAKANA STUDIO", True, (248, 248, 252))
        label = pygame.Surface(text.get_size(), pygame.SRCALPHA)
        label.blit(text, (0, 0))
        label.set_alpha(alpha)
        tr = label.get_rect(center=(cx, cy + 92))
        surface.blit(label, tr.topleft)

        if self._curated_logo is not None:
            max_w = min(720, int(surface.get_width() * 0.45))
            scale = max(1.0, self._curated_logo.get_width())
            logo_h = max(40, int(self._curated_logo.get_height() * (max_w / scale)))
            logo = pygame.transform.smoothscale(self._curated_logo, (max_w, logo_h)).copy()
            logo.set_alpha(int(118 * (alpha / 255.0)))
            lrect = logo.get_rect(center=(cx, cy + 146))
            surface.blit(logo, lrect.topleft)

        # Slight purple particle dust around letters.
        dust = pygame.Surface((tr.w + 90, tr.h + 40), pygame.SRCALPHA)
        rng = random.Random(self.seed + 91)
        for _ in range(24):
            dx = rng.randint(0, dust.get_width() - 1)
            dy = rng.randint(0, dust.get_height() - 1)
            aa = int((24 + rng.randint(0, 34)) * (alpha / 255.0))
            dust.set_at((dx, dy), (150, 108, 212, aa))
        surface.blit(dust, (tr.x - 45, tr.y - 20))

    def _render_static_fallback(self, surface: pygame.Surface):
        w, h = surface.get_size()
        surface.fill((2, 2, 4))
        area = safe_area(w, h, 20, 20)
        title_font = self.app.typography.get(TITLE_FONT, max(72, int(self.app.big_font.get_height() * 1.95)))
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
            self._draw_starfield(surface, w, h)
            self._draw_center_circles(surface, cx, cy)
            self._draw_chakana_symbol(surface, cx, cy)
            self._draw_title(surface, cx, cy)

            # Clean fade to menu.
            tail = max(0.0, min(1.0, (self.t - 3.55) / 0.45))
            if tail > 0:
                fade = pygame.Surface((w, h), pygame.SRCALPHA)
                fade.fill((0, 0, 0, int(240 * tail)))
                surface.blit(fade, (0, 0))

        except Exception:
            self.fallback_mode = True
            if not self._logged_fallback:
                self._logged_fallback = True
                print("[studio_intro] fallback=static_logo")
            self._render_static_fallback(surface)
