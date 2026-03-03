from __future__ import annotations

from pathlib import Path

import pygame

from game.settings import ASSETS_DIR, INTERNAL_HEIGHT, INTERNAL_WIDTH


class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.cooldowns = {}
        self.master_volume = 0.7
        self.sound_cfg = {
            "ui_click": (0.22, 80),
            "card_pick": (0.3, 80),
            "card_play": (0.35, 90),
            "hit": (0.5, 100),
            "shield": (0.4, 90),
            "exhaust": (0.45, 100),
            "whisper": (0.24, 90),
        }
        for name in self.sound_cfg:
            path = Path(ASSETS_DIR) / "sfx" / f"{name}.wav"
            self.sounds[name] = pygame.mixer.Sound(str(path)) if path.exists() else None

    def set_volume(self, value: float):
        self.master_volume = max(0.0, min(1.0, value))

    def play(self, name: str):
        if name not in self.sound_cfg:
            return
        vol, cooldown = self.sound_cfg[name]
        now = pygame.time.get_ticks()
        if now - self.cooldowns.get(name, 0) < cooldown:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(vol * self.master_volume)
            snd.play()
        self.cooldowns[name] = now


class AssetManager:
    def __init__(self):
        self._cache = {}

    def _load_image(self, path: Path, fallback_size: tuple[int, int], fill=(60, 55, 90)):
        if path.exists():
            try:
                return pygame.image.load(str(path)).convert_alpha()
            except Exception:
                pass
        surf = pygame.Surface(fallback_size)
        surf.fill(fill)
        pygame.draw.rect(surf, (120, 110, 170), surf.get_rect(), 3)
        return surf

    def sprite(self, category: str, name: str, size: tuple[int, int], fallback=(60, 55, 90)):
        key = (category, name, size)
        if key in self._cache:
            return self._cache[key]
        path = Path(ASSETS_DIR) / "sprites" / category / f"{name}.png"
        img = self._load_image(path, size, fallback)
        if img.get_size() != size:
            img = pygame.transform.scale(img, size)
        self._cache[key] = img
        return img


class Renderer:
    def __init__(self):
        self.window = pygame.display.set_mode((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE)
        self.internal = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT)).convert()
        self.fullscreen = False
        self.use_smooth = False

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE)

    def _viewport(self):
        ww, wh = self.window.get_size()
        scale = min(ww / INTERNAL_WIDTH, wh / INTERNAL_HEIGHT)
        nw, nh = int(INTERNAL_WIDTH * scale), int(INTERNAL_HEIGHT * scale)
        x, y = (ww - nw) // 2, (wh - nh) // 2
        return x, y, nw, nh, scale

    def present(self):
        x, y, nw, nh, _scale = self._viewport()
        self.window.fill((0, 0, 0))
        if self.use_smooth:
            scaled = pygame.transform.smoothscale(self.internal, (nw, nh))
        else:
            scaled = pygame.transform.scale(self.internal, (nw, nh))
        self.window.blit(scaled, (x, y))
        pygame.display.flip()

    def map_mouse(self, pos):
        x, y, _nw, _nh, scale = self._viewport()
        px = int((pos[0] - x) / max(scale, 1e-6))
        py = int((pos[1] - y) / max(scale, 1e-6))
        px = max(0, min(INTERNAL_WIDTH - 1, px))
        py = max(0, min(INTERNAL_HEIGHT - 1, py))
        return px, py
