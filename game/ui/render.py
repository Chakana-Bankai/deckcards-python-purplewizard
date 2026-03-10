from __future__ import annotations

from pathlib import Path

import pygame

from game.core.paths import sprite_category_dir
from game.settings import ASSETS_DIR, INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.ui.system.typography import ChakanaTypography, SMALL_FONT
from game.visual import get_portrait_pipeline, get_visual_engine


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
            "chime": (0.22, 90),
            "deny": (0.24, 90),
            "stinger_victory": (0.38, 180),
            "stinger_defeat": (0.36, 180),
            "stinger_reward": (0.34, 160),
            "stinger_seal_ready": (0.30, 150),
            "stinger_boss_phase": (0.40, 220),
        }
        fallback = {
            "deny": "exhaust",
            "stinger_victory": "chime",
            "stinger_defeat": "hit",
            "stinger_reward": "chime",
            "stinger_seal_ready": "whisper",
            "stinger_boss_phase": "hit",
        }
        for name in self.sound_cfg:
            path = Path(ASSETS_DIR) / "sfx" / f"{name}.wav"
            if path.exists():
                self.sounds[name] = pygame.mixer.Sound(str(path))
                continue
            alias = fallback.get(name)
            alias_path = Path(ASSETS_DIR) / "sfx" / f"{alias}.wav" if alias else None
            self.sounds[name] = pygame.mixer.Sound(str(alias_path)) if alias_path and alias_path.exists() else None

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
        self._visual = None
        self._portrait = None
        self._load_logged = set()

    def _load_image(self, path: Path, fallback_size: tuple[int, int], fill=(60, 55, 90), fallback_label: str = ""):
        if path.exists():
            try:
                return pygame.image.load(str(path)).convert_alpha()
            except Exception:
                pass
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(fill)
        pygame.draw.rect(surf, (120, 110, 170), surf.get_rect(), 3)
        if fallback_label:
            f = ChakanaTypography().get(SMALL_FONT, max(12, fallback_size[1] // 11))
            txt = f.render(fallback_label[:20], True, (230, 226, 246))
            surf.blit(txt, (6, max(4, fallback_size[1] - txt.get_height() - 4)))
        return surf

    def _try_portrait_pipeline(self, category: str, name: str, size: tuple[int, int], current: pygame.Surface | None):
        cat = str(category or "").lower()
        key = str(name or "").lower()
        use_portrait = (
            cat in {"avatar", "player", "enemies", "guides"} or (cat == "overlays" and key in {"archon", "archon_oracle", "archon_panel"})
        )
        if not use_portrait:
            return None
        try:
            if self._portrait is None:
                self._portrait = get_portrait_pipeline()
            portrait_key = key
            if cat == "enemies":
                portrait_key = f"enemy__{key}__hologram"
            elif cat == "guides":
                portrait_key = f"guide__{key}__portrait"
            return self._portrait.resolve_for_ui(portrait_key, size, current_fallback=current)
        except Exception:
            return None

    def sprite(self, category: str, name: str, size: tuple[int, int], fallback=(60, 55, 90)):
        key = (category, name, size)
        if key in self._cache:
            return self._cache[key]
        path = sprite_category_dir(category) / f"{name}.png"
        lbl = name if category == "cards" else ""
        src = "fallback"
        if path.exists():
            img = self._load_image(path, size, fallback, fallback_label=lbl)
            src = f"sprite:{path.name}"
            portrait_img = self._try_portrait_pipeline(category, name, size, img)
            if portrait_img is not None:
                img = portrait_img
                src = "portrait_pipeline"
        else:
            img = self._try_portrait_pipeline(category, name, size, None)
            if img is not None:
                src = "portrait_pipeline"
            if img is None and category in {"avatar", "player", "relics", "biomes", "starters", "emblems", "overlays"}:
                try:
                    if self._visual is None:
                        self._visual = get_visual_engine()
                    vcat = {"player": "avatar", "starters": "emblems"}.get(category, category)
                    ctx = "mini" if category == "starters" else ""
                    if vcat == "biomes":
                        ctx = "bg"
                    if vcat == "avatar":
                        ctx = str(name or "combat_hud")
                    if vcat == "relics":
                        ctx = "rare"
                    img = self._visual.generate(vcat, str(name or "default"), size, context=ctx, force=False)
                    src = "visual_generated"
                except Exception:
                    img = None
            if img is None:
                img = self._load_image(path, size, fallback, fallback_label=lbl)
                src = "fallback"
        if img.get_size() != size:
            img = pygame.transform.scale(img, size)
        if str(category).lower() in {"avatar", "player", "enemies", "biomes"}:
            lk = f"{str(category).lower()}:{str(name).lower()}:{src}"
            if lk not in self._load_logged:
                self._load_logged.add(lk)
                print(f"[asset] category={category} name={name} source={src}")
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






