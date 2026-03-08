from __future__ import annotations

import json
import time
from pathlib import Path

import pygame

from game.core.paths import assets_dir
from .visual_engine import get_visual_engine


class PortraitPipeline:
    """Portrait source + stylized pipeline with cache and safe fallbacks."""

    VERSION = "portrait_v1"

    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.generated_root = self.root / "generated" / "portraits"
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "portrait_manifest.json"
        self.manifest = self._load_manifest()
        self._cache: dict[tuple[str, str, tuple[int, int]], pygame.Surface] = {}
        self._log_once: set[str] = set()

    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": self.VERSION, "updated_at": int(time.time()), "items": {}}
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("version", self.VERSION)
                payload.setdefault("updated_at", int(time.time()))
                payload.setdefault("items", {})
                return payload
        except Exception:
            pass
        return {"version": self.VERSION, "updated_at": int(time.time()), "items": {}}

    def _save_manifest(self):
        self.manifest["version"] = self.VERSION
        self.manifest["updated_at"] = int(time.time())
        try:
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _source_candidates(self, role: str) -> list[Path]:
        aroot = assets_dir()
        role = str(role or "chakana").lower()
        return [
            aroot / "sprites" / "portrait_sources" / f"{role}_master.png",
            aroot / "sprites" / "portrait_sources" / f"{role}.png",
            aroot / "sprites" / "avatar" / f"{role}.png",
        ]

    def _resolve_role(self, name: str) -> str:
        key = str(name or "").lower()
        if key in {"archon", "archon_oracle", "archon_panel", "corrupt_oracle"}:
            return "archon"
        return "chakana"

    def _generated_path(self, role: str, style: str, size: tuple[int, int]) -> Path:
        return self.generated_root / f"{role}_{style}_{size[0]}x{size[1]}.png"

    def _fit_contain(self, source: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(16, int(size[0])), max(16, int(size[1]))
        sw, sh = source.get_size()
        if sw <= 0 or sh <= 0:
            return pygame.Surface((w, h), pygame.SRCALPHA)
        scale = min(w / sw, h / sh)
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        img = pygame.transform.scale(source, (tw, th))
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(img, (w // 2 - tw // 2, h // 2 - th // 2))
        return out

    def _stylize(self, source: pygame.Surface, role: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(16, int(size[0])), max(16, int(size[1]))
        fitted = self._fit_contain(source, (w, h))

        # Keep crisp pseudo-pixel profile: downscale then upscale with nearest.
        dw = max(16, w // 3)
        dh = max(16, h // 3)
        pixel = pygame.transform.scale(fitted, (dw, dh))
        pixel = pygame.transform.scale(pixel, (w, h))

        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        if role == "archon":
            shade.fill((96, 20, 32, 90))
            edge = (226, 84, 104)
            glow = (236, 102, 122, 42)
        else:
            shade.fill((70, 30, 114, 84))
            edge = (206, 176, 116)
            glow = (126, 212, 246, 42)
        pixel.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(pixel, (0, 0))
        glow_s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(glow_s, glow, glow_s.get_rect(), 2, border_radius=8)
        out.blit(glow_s, (0, 0))
        pygame.draw.rect(out, edge, out.get_rect(), 2, border_radius=8)
        return out

    def _log_source(self, tag: str):
        if tag in self._log_once:
            return
        self._log_once.add(tag)
        print(f"[portrait] source={tag}")

    def get_master(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        role = self._resolve_role(name)
        cache_key = (role, "master", (int(size[0]), int(size[1])))
        if cache_key in self._cache:
            return self._cache[cache_key]
        for p in self._source_candidates(role):
            if not p.exists():
                continue
            try:
                src = pygame.image.load(str(p)).convert_alpha()
                surf = self._fit_contain(src, size)
                self._cache[cache_key] = surf
                self._log_source("master")
                return surf
            except Exception:
                continue
        return None

    def get_stylized(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        role = self._resolve_role(name)
        size = (max(16, int(size[0])), max(16, int(size[1])))
        cache_key = (role, "stylized", size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        out_path = self._generated_path(role, "stylized", size)
        if out_path.exists():
            try:
                surf = pygame.image.load(str(out_path)).convert_alpha()
                self._cache[cache_key] = surf
                self._log_source("stylized")
                return surf
            except Exception:
                pass

        src = self.get_master(role, size)
        if src is not None:
            surf = self._stylize(src, role, size)
        else:
            # Safe stylized fallback from visual engine when no master source is present.
            try:
                ve = get_visual_engine()
                avatar_id = "archon_oracle" if role == "archon" else "combat_hud"
                surf = ve.generate("avatar", avatar_id, size, context=avatar_id, force=False)
            except Exception:
                surf = None
            if surf is None:
                return None

        try:
            pygame.image.save(surf, str(out_path))
        except Exception:
            pass
        items = self.manifest.setdefault("items", {})
        items[f"{role}:{size[0]}x{size[1]}"] = {
            "role": role,
            "style": "stylized",
            "size": [size[0], size[1]],
            "path": str(out_path),
            "generated_at": int(time.time()),
            "version": self.VERSION,
        }
        self._save_manifest()
        self._cache[cache_key] = surf
        self._log_source("stylized")
        return surf

    def resolve_for_ui(self, name: str, size: tuple[int, int], current_fallback: pygame.Surface | None = None) -> pygame.Surface | None:
        surf = self.get_stylized(name, size)
        if surf is not None:
            return surf
        if current_fallback is not None:
            self._log_source("fallback:current")
        return current_fallback


_PIPELINE: PortraitPipeline | None = None


def get_portrait_pipeline() -> PortraitPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = PortraitPipeline()
    return _PIPELINE
