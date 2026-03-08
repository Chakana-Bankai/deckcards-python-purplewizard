from __future__ import annotations

import math
import pygame


class HolographicOracleUI:
    """Non-intrusive holographic dialogue overlay with two speaker channels."""

    def __init__(self):
        self.active = False
        self.timer = 0.0
        self.duration = 4.2
        self.fade_in = 0.24
        self.fade_out = 1.10
        self.title = "ORACULO CHAKANA"
        self.text = ""
        self.trigger = ""
        self.speaker = "chakana"
        self.interference = False
        self.priority = 0

    def show(
        self,
        text: str,
        trigger: str = "",
        title: str = "ORACULO CHAKANA",
        speaker: str = "chakana",
        interference: bool = False,
        duration: float | None = None,
        priority: int = 0,
    ):
        self.active = True
        self.timer = 0.0
        if duration is not None:
            self.duration = max(2.4, min(6.8, float(duration)))
        self.title = str(title or "ORACULO CHAKANA")
        self.text = str(text or "")
        self.trigger = str(trigger or "")
        self.speaker = str(speaker or "chakana").lower()
        self.interference = bool(interference)
        self.priority = int(priority or 0)

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
        return lines[:max_lines]

    def render(self, surface: pygame.Surface, app):
        alpha = self._alpha()
        if alpha <= 0:
            return

        sw, sh = surface.get_size()
        panel = pygame.Rect(26, sh - 212, min(512, sw // 2 - 44), 170)

        is_archon = self.speaker == "archon"
        base_glow = (220, 84, 104) if is_archon else (146, 86, 220)
        border_col = (242, 120, 132) if is_archon else (136, 98, 218)
        accent_col = (252, 146, 160) if is_archon else (126, 212, 246)
        text_col = (255, 220, 224) if is_archon else (230, 220, 248)
        title_col = (255, 170, 182) if is_archon else (190, 240, 255)

        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        glow = pygame.Surface((panel.w + 30, panel.h + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*base_glow, int(alpha * 0.16)), glow.get_rect(), border_radius=24)
        surface.blit(glow, (panel.x - 15, panel.y - 15))

        pygame.draw.rect(layer, (16, 12, 30, int(alpha * 0.80)), layer.get_rect(), border_radius=14)
        pygame.draw.rect(layer, (*border_col, int(alpha * 0.92)), layer.get_rect(), 2, border_radius=14)

        for y in range(2, panel.h, 4):
            pygame.draw.line(layer, (*accent_col, int(alpha * 0.10)), (8, y), (panel.w - 8, y), 1)

        phase = pygame.time.get_ticks() * 0.015
        gy = int(50 + math.sin(phase) * 18)
        glitch_col = (252, 116, 132) if (is_archon or self.interference) else (190, 120, 255)
        pygame.draw.rect(layer, (*glitch_col, int(alpha * 0.12)), pygame.Rect(10, gy, panel.w - 20, 6), border_radius=3)

        av_rect = pygame.Rect(14, 18, 122, 136)
        pygame.draw.rect(layer, (30, 22, 54, int(alpha * 0.86)), av_rect, border_radius=10)
        pygame.draw.rect(layer, (*accent_col, int(alpha * 0.86)), av_rect, 1, border_radius=10)

        avatar = app.assets.sprite("avatar", "codex", (av_rect.w - 10, av_rect.h - 10), fallback=(86, 56, 132)).copy()
        avatar.set_alpha(int(alpha * 0.90))
        if is_archon:
            tint = pygame.Surface(avatar.get_size(), pygame.SRCALPHA)
            tint.fill((255, 84, 102, 130))
            avatar.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        jitter = 2 if self.interference else 1
        jx = int(math.sin(phase * 2.4) * jitter)
        jy = int(math.cos(phase * 1.8) * jitter) if self.interference else 0
        layer.blit(avatar, (av_rect.x + 5 + jx, av_rect.y + 5 + jy))

        bubble = pygame.Rect(av_rect.right + 12, 18, panel.w - av_rect.right - 24, panel.h - 36)
        pygame.draw.rect(layer, (32, 24, 62, int(alpha * 0.74)), bubble, border_radius=10)
        pygame.draw.rect(layer, (*border_col, int(alpha * 0.90)), bubble, 1, border_radius=10)

        title_font = getattr(app, "small_font", app.font)
        body_font = getattr(app, "tiny_font", app.font)
        speaker_font = body_font

        title = title_font.render(self.title[:40], True, title_col)
        title.set_alpha(alpha)
        layer.blit(title, (bubble.x + 10, bubble.y + 8))

        speaker_label = "CHAKANA" if not is_archon else "ARCONTE"
        tag = speaker_font.render(speaker_label, True, title_col)
        tag.set_alpha(int(alpha * 0.9))
        layer.blit(tag, (bubble.right - tag.get_width() - 10, bubble.y + 10))

        lines = self._wrap(body_font, self.text, bubble.w - 20, max_lines=4)
        y = bubble.y + 38
        for line in lines:
            lbl = body_font.render(line, True, text_col)
            lbl.set_alpha(alpha)
            layer.blit(lbl, (bubble.x + 10, y))
            y += 22

        if self.trigger:
            trig_col = (232, 136, 146) if is_archon else (156, 126, 222)
            trig = body_font.render(self.trigger.upper()[:30], True, trig_col)
            trig.set_alpha(int(alpha * 0.84))
            layer.blit(trig, (bubble.x + 10, bubble.bottom - 24))

        if self.interference:
            noise = pygame.Surface(panel.size, pygame.SRCALPHA)
            for i in range(18):
                nx = int((i * 37 + pygame.time.get_ticks() // 7) % max(1, panel.w - 30))
                ny = int((i * 19 + pygame.time.get_ticks() // 11) % max(1, panel.h - 6))
                pygame.draw.rect(noise, (255, 136, 146, int(alpha * 0.08)), pygame.Rect(nx, ny, 24, 2))
            surface.blit(noise, panel.topleft)

        surface.blit(layer, panel.topleft)
