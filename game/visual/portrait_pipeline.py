from __future__ import annotations

import json
import time
from pathlib import Path

import pygame

from game.core.paths import assets_dir
from .visual_engine import get_visual_engine


class PortraitPipeline:
    """Multi-tier character pipeline: concept art, portrait, hologram."""

    VERSION = "portrait_v5"

    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.generated_root = self.root / "generated" / "portraits"
        self.generated_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "portrait_manifest.json"
        self.manifest = self._load_manifest()
        self._cache: dict[tuple[str, str, tuple[int, int]], pygame.Surface] = {}
        self._cache_stamp: dict[tuple[str, str, tuple[int, int]], str] = {}
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

    def _resolve_role(self, name: str) -> str:
        key = str(name or "").lower().strip()
        if key in {
            "archon",
            "archon_oracle",
            "archon_panel",
            "corrupt_oracle",
            "archon_holo",
            "archon_hologram",
            "archon_portrait",
            "archon_concept",
        }:
            return "archon"
        return "chakana_mage"

    def _resolve_style(self, name: str) -> str:
        key = str(name or "").lower().strip()
        if "concept" in key or key in {"codex_entry"}:
            return "concept"
        if "portrait" in key or key in {"dialogue", "scene", "lore_panel", "menu"}:
            return "portrait"
        if "holo" in key or "hologram" in key or "oracle" in key or key in {"combat_hud", "player_hud", "hud"}:
            return "hologram"
        return "portrait"

    def _canonical_avatar_roots(self) -> list[Path]:
        aroot = assets_dir()
        return [
            aroot / "curated" / "avatars",
            aroot / "avatars" / "master",
            aroot / "avatars",
            aroot / "sprites" / "portrait_sources",
            aroot / "sprites" / "portrait",
            aroot / "sprites" / "hologram",
            aroot / "sprites" / "avatar",
            aroot / "sprites" / "player",
        ]

    def _source_candidates(self, role: str, style: str) -> list[tuple[Path, str]]:
        role = str(role or "chakana_mage").lower().strip()
        style = str(style or "portrait").lower().strip()
        roots = self._canonical_avatar_roots()

        if role == "chakana_mage":
            explicit_master = {
                "concept": ["chakana_mage_master_concept.png"],
                "portrait": ["chakana_mage_master_portrait.png"],
                "hologram": ["chakana_mage_master_hologram.png"],
            }
            generated = {
                "concept": ["chakana_mage_concept.png"],
                "portrait": ["chakana_mage_portrait.png"],
                "hologram": ["chakana_mage_hologram.png", "chakana_mage_holo.png"],
            }
            placeholders = {
                "concept": ["chakana_mage.png", "chakana.png"],
                "portrait": ["chakana_mage.png", "chakana.png"],
                "hologram": ["combat_hud.png", "chakana_mage_holo.png", "chakana_mage_hologram.png"],
            }
            out: list[tuple[Path, str]] = []
            for filename in explicit_master.get(style, []):
                for root in roots:
                    out.append((root / filename, "official_master"))
            for filename in generated.get(style, []):
                for root in roots:
                    out.append((root / filename, "generated"))
            for filename in placeholders.get(style, []):
                for root in roots:
                    out.append((root / filename, "placeholder"))
            return out

        archon = {
            "concept": [
                ("archon_master_concept.png", "official_master"),
                ("archon_concept.png", "generated"),
                ("archon.png", "placeholder"),
            ],
            "portrait": [
                ("archon_master_portrait.png", "official_master"),
                ("archon_portrait.png", "generated"),
                ("archon.png", "placeholder"),
            ],
            "hologram": [
                ("archon_master_hologram.png", "official_master"),
                ("archon_hologram.png", "generated"),
                ("archon_holo.png", "placeholder"),
                ("archon_oracle.png", "placeholder"),
            ],
        }
        out: list[tuple[Path, str]] = []
        for filename, tag in archon.get(style, []):
            for root in roots:
                out.append((root / filename, tag))
        return out

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

    def _stylize_portrait(self, source: pygame.Surface, role: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(16, int(size[0])), max(16, int(size[1]))
        fitted = self._fit_contain(source, (w, h))
        dw = max(24, w // 2)
        dh = max(24, h // 2)
        pixel = pygame.transform.scale(fitted, (dw, dh))
        pixel = pygame.transform.scale(pixel, (w, h))

        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        if role == "archon":
            shade.fill((90, 28, 40, 70))
            edge = (226, 84, 104)
        else:
            shade.fill((62, 40, 98, 62))
            edge = (206, 176, 116)
        pixel.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.rect(pixel, edge, pixel.get_rect(), 2, border_radius=8)
        return pixel

    def _to_holographic(self, source: pygame.Surface, role: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(16, int(size[0])), max(16, int(size[1]))
        base = self._stylize_portrait(source, role, size)
        tint = pygame.Surface((w, h), pygame.SRCALPHA)
        if role == "archon":
            tint.fill((220, 74, 98, 58))
            line_col = (236, 110, 128)
            edge = (242, 126, 142)
        else:
            tint.fill((90, 160, 255, 52))
            line_col = (126, 212, 246)
            edge = (152, 228, 255)
        base.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if role != "archon":
            violet = pygame.Surface((w, h), pygame.SRCALPHA)
            violet.fill((146, 96, 238, 30))
            base.blit(violet, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        scan = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(1, h, 3):
            pygame.draw.line(scan, (*line_col, 34), (2, y), (w - 3, y), 1)
        base.blit(scan, (0, 0))

        for y in range(6, h - 6, 13):
            wobble = 1 if ((y // 13) % 2 == 0) else -1
            band = base.subsurface(pygame.Rect(0, y, w, 1)).copy()
            base.blit(band, (wobble, y))

        pygame.draw.rect(base, edge, base.get_rect(), 1, border_radius=8)
        return base

    def _source_stamp(self, role: str, style: str) -> str:
        for p, tag in self._source_candidates(role, style):
            if not p.exists():
                continue
            try:
                stat = p.stat()
                return f"{tag}:{p.name}:{int(stat.st_mtime)}:{int(stat.st_size)}"
            except Exception:
                return f"{tag}:{p.name}"
        return "none"

    def _load_source_by_style(self, role: str, style: str, size: tuple[int, int]) -> tuple[pygame.Surface | None, str, str]:
        for p, tag in self._source_candidates(role, style):
            if not p.exists():
                continue
            try:
                src = pygame.image.load(str(p)).convert_alpha()
                return self._fit_contain(src, size), tag, str(p)
            except Exception:
                continue
        return None, "missing", ""

    def _log_source(self, tag: str, detail: str = ""):
        key = f"{tag}:{detail}" if detail else tag
        if key in self._log_once:
            return
        self._log_once.add(key)
        if detail:
            print(f"[portrait] source={tag} file={detail}")
        else:
            print(f"[portrait] source={tag}")

    def _build_style(self, role: str, style: str, size: tuple[int, int]) -> tuple[pygame.Surface | None, str, str]:
        direct, direct_tag, direct_path = self._load_source_by_style(role, style, size)
        if direct is not None:
            if direct_tag == "official_master":
                return direct, direct_tag, direct_path
            if style == "concept":
                return direct, direct_tag, direct_path
            if style == "portrait":
                return self._stylize_portrait(direct, role, size), direct_tag, direct_path
            return self._to_holographic(direct, role, size), direct_tag, direct_path

        concept, concept_tag, concept_path = self._load_source_by_style(role, "concept", size)
        if concept is not None:
            if style == "concept":
                return concept, concept_tag, concept_path
            if style == "portrait":
                return self._stylize_portrait(concept, role, size), concept_tag, concept_path
            return self._to_holographic(concept, role, size), concept_tag, concept_path

        try:
            ve = get_visual_engine()
            avatar_id = "archon_oracle" if role == "archon" else "combat_hud"
            generated = ve.generate("avatar", avatar_id, size, context=avatar_id, force=False)
            return generated, "generated_or_cache", f"visual_engine:{avatar_id}"
        except Exception:
            return None, "fallback:current", ""

    def get_style(self, name: str, size: tuple[int, int], style: str) -> pygame.Surface | None:
        role = self._resolve_role(name)
        style = str(style or "portrait").lower()
        size = (max(16, int(size[0])), max(16, int(size[1])))
        cache_key = (role, style, size)
        current_stamp = self._source_stamp(role, style)

        if cache_key in self._cache and self._cache_stamp.get(cache_key) == current_stamp:
            return self._cache[cache_key]

        self._cache.pop(cache_key, None)
        self._cache_stamp.pop(cache_key, None)

        out_path = self._generated_path(role, style, size)
        if out_path.exists() and current_stamp == "none":
            try:
                surf = pygame.image.load(str(out_path)).convert_alpha()
                self._cache[cache_key] = surf
                self._cache_stamp[cache_key] = current_stamp
                self._log_source("cache_file", out_path.name)
                return surf
            except Exception:
                pass

        surf, source_tag, source_path = self._build_style(role, style, size)
        if surf is None:
            return None

        try:
            pygame.image.save(surf, str(out_path))
        except Exception:
            pass

        items = self.manifest.setdefault("items", {})
        items[f"{role}:{style}:{size[0]}x{size[1]}"] = {
            "role": role,
            "style": style,
            "size": [size[0], size[1]],
            "path": str(out_path),
            "generated_at": int(time.time()),
            "version": self.VERSION,
            "source": source_tag,
            "source_path": source_path,
        }
        self._save_manifest()
        self._cache[cache_key] = surf
        self._cache_stamp[cache_key] = current_stamp
        self._log_source(source_tag, Path(source_path).name if source_path else style)
        return surf

    def get_concept(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.get_style(name, size, "concept")

    def get_portrait(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.get_style(name, size, "portrait")

    def get_hologram(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.get_style(name, size, "hologram")

    def resolve_for_ui(self, name: str, size: tuple[int, int], current_fallback: pygame.Surface | None = None) -> pygame.Surface | None:
        style = self._resolve_style(name)
        surf = self.get_style(name, size, style)
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

