from __future__ import annotations

import math
import pygame


class HolographicOracleUI:
    """Codec-style holographic oracle overlay.

    Non-intrusive bottom-left overlay with auto-fade, scanlines and subtle glitch.
    """

    def __init__(self):
        self.active = False
        self.timer = 0.0
        self.duration = 4.2
        self.fade_in = 0.28
        self.fade_out = 1.15
        self.title = "ORACULO CHAKANA"
        self.text = ""
        self.trigger = ""

    def show(self, text: str, trigger: str = "", title: str = "ORACULO CHAKANA"):
        self.active = True
        self.timer = 0.0
        self.title = str(title or "ORACULO CHAKANA")
        self.text = str(text or "")
        self.trigger = str(trigger or "")

    def update(self, dt: float):
        if not self.active:
            return
        self.timer += max(0.0, float(dt or 0.0))
        if self.timer >= self.duration:
            self.active = False

    def _alpha(self) -> int:
        if not self.active:
            return 0
        t = self.timer
        if t < self.fade_in:
            a = t / max(0.001, self.fade_in)
        elif t > self.duration - self.fade_out:
            a = (self.duration - t) / max(0.001, self.fade_out)
        else:
            a = 1.0
        return max(0, min(255, int(255 * a)))

    def _wrap(self, font: pygame.font.Font, text: str, width: int, max_lines: int = 3) -> list[str]:
        words = str(text or "").replace("\n", " ").split()
        if not words:
            return [""]
        lines = []
        cur = words[0]
        for w in words[1:]:
            cand = f"{cur} {w}"
            if font.size(cand)[0] <= width:
                cur = cand
            else:
                lines.append(cur)
                cur = w
                if len(lines) >= max_lines - 1:
                    break
        if len(lines) < max_lines:
            lines.append(cur)
        lines = lines[:max_lines]
        return lines

    def render(self, surface: pygame.Surface, app):
        alpha = self._alpha()
        if alpha <= 0:
            return

        sw, sh = surface.get_size()
        panel = pygame.Rect(24, sh - 210, min(520, sw // 2 - 40), 172)

        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        # soft mystical glow
        glow = pygame.Surface((panel.w + 30, panel.h + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow, (146, 86, 220, int(alpha * 0.16)), glow.get_rect(), border_radius=24)
        surface.blit(glow, (panel.x - 15, panel.y - 15))

        pygame.draw.rect(layer, (16, 12, 30, int(alpha * 0.80)), layer.get_rect(), border_radius=14)
        pygame.draw.rect(layer, (136, 98, 218, int(alpha * 0.92)), layer.get_rect(), 2, border_radius=14)

        # scanline overlay
        for y in range(2, panel.h, 4):
            pygame.draw.line(layer, (190, 150, 255, int(alpha * 0.09)), (8, y), (panel.w - 8, y), 1)

        # subtle glitch bar
        phase = pygame.time.get_ticks() * 0.015
        gy = int(50 + math.sin(phase) * 18)
        pygame.draw.rect(layer, (190, 120, 255, int(alpha * 0.12)), pygame.Rect(10, gy, panel.w - 20, 6), border_radius=3)

        # avatar frame
        av_rect = pygame.Rect(14, 18, 122, 136)
        pygame.draw.rect(layer, (30, 22, 54, int(alpha * 0.86)), av_rect, border_radius=10)
        pygame.draw.rect(layer, (126, 212, 246, int(alpha * 0.86)), av_rect, 1, border_radius=10)

        avatar = app.assets.sprite("avatar", "codex", (av_rect.w - 10, av_rect.h - 10), fallback=(86, 56, 132)).copy()
        avatar.set_alpha(int(alpha * 0.92))
        jx = int(math.sin(phase * 2.4) * 2)
        layer.blit(avatar, (av_rect.x + 5 + jx, av_rect.y + 5))

        # text bubble
        bubble = pygame.Rect(av_rect.right + 12, 18, panel.w - av_rect.right - 24, panel.h - 36)
        pygame.draw.rect(layer, (32, 24, 62, int(alpha * 0.74)), bubble, border_radius=10)
        pygame.draw.rect(layer, (138, 104, 228, int(alpha * 0.90)), bubble, 1, border_radius=10)

        title_font = getattr(app, "small_font", app.font)
        body_font = getattr(app, "tiny_font", app.font)
        tcol = (190, 240, 255)
        bcol = (230, 220, 248)

        title = title_font.render(self.title[:40], True, tcol)
        title.set_alpha(alpha)
        layer.blit(title, (bubble.x + 10, bubble.y + 8))

        lines = self._wrap(body_font, self.text, bubble.w - 20, max_lines=4)
        y = bubble.y + 38
        for line in lines:
            lbl = body_font.render(line, True, bcol)
            lbl.set_alpha(alpha)
            layer.blit(lbl, (bubble.x + 10, y))
            y += 22

        if self.trigger:
            trig = body_font.render(self.trigger.upper()[:30], True, (156, 126, 222))
            trig.set_alpha(int(alpha * 0.84))
            layer.blit(trig, (bubble.x + 10, bubble.bottom - 24))

        surface.blit(layer, panel.topleft)

