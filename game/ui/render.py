from __future__ import annotations

import pygame
from pathlib import Path

from game.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT, COLORS, ASSETS_DIR


class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.cooldowns = {}
        for name in ["ui_click", "card_play", "hit", "shield", "exhaust"]:
            path = Path(ASSETS_DIR) / "sfx" / f"{name}.wav"
            self.sounds[name] = pygame.mixer.Sound(str(path)) if path.exists() else None

    def play(self, name: str, cooldown=80):
        now = pygame.time.get_ticks()
        if now - self.cooldowns.get(name, 0) < cooldown:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.play()
        self.cooldowns[name] = now


class Renderer:
    def __init__(self):
        self.window = pygame.display.set_mode((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE)
        self.internal = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        self.fullscreen = False

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE)

    def present(self):
        ww, wh = self.window.get_size()
        scale = min(ww / INTERNAL_WIDTH, wh / INTERNAL_HEIGHT)
        nw, nh = int(INTERNAL_WIDTH * scale), int(INTERNAL_HEIGHT * scale)
        x, y = (ww - nw) // 2, (wh - nh) // 2
        self.window.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(self.internal, (nw, nh))
        self.window.blit(scaled, (x, y))
        pygame.display.flip()

    def map_mouse(self, pos):
        ww, wh = self.window.get_size()
        scale = min(ww / INTERNAL_WIDTH, wh / INTERNAL_HEIGHT)
        nw, nh = int(INTERNAL_WIDTH * scale), int(INTERNAL_HEIGHT * scale)
        x, y = (ww - nw) // 2, (wh - nh) // 2
        px = int((pos[0] - x) / scale)
        py = int((pos[1] - y) / scale)
        px = max(0, min(INTERNAL_WIDTH - 1, px))
        py = max(0, min(INTERNAL_HEIGHT - 1, py))
        return px, py


def draw_panel(surf, rect):
    pygame.draw.rect(surf, COLORS["panel"], rect, border_radius=10)
