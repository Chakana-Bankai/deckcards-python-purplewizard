from __future__ import annotations

import json
import time
from pathlib import Path

import pygame

from game.core.paths import assets_dir
from .visual_engine import get_visual_engine


class PortraitPipeline:
    """Multi-tier character pipeline: concept art, portrait, hologram."""

    VERSION = "portrait_v6"

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
        if key in {"angel", "shaman", "demon", "arcane_hacker", "guide"}:
            return "guide"
        if key.startswith("enemy_") or key in {"enemy", "boss"}:
            return "enemy"
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
        if "mini" in key or key in {"hud_mini", "fallback_mini"}:
            return "mini"
        if "codex" in key:
            return "codex"
        if "concept" in key or key in {"codex_entry"}:
            return "concept"
        if "portrait" in key or key in {"dialogue", "scene", "lore_panel", "menu"}:
            return "portrait"
        if "holo" in key or "hologram" in key or "oracle" in key or key in {"combat_hud", "player_hud", "hud"}:
            return "hologram"
        return "portrait"

    def _role_profile(self, role: str) -> dict:
        profiles = {
            "chakana_mage": {
                "tint": (90, 160, 255, 52),
                "accent": (152, 228, 255),
                "edge": (206, 176, 116),
                "scanline": (126, 212, 246),
                "noise": (156, 236, 255, 26),
                "rgb_shift": (1, -1),
            },
            "archon": {
                "tint": (220, 74, 98, 58),
                "accent": (242, 126, 142),
                "edge": (226, 84, 104),
                "scanline": (236, 110, 128),
                "noise": (255, 124, 146, 32),
                "rgb_shift": (2, -2),
            },
            "guide": {
                "tint": (122, 210, 176, 46),
                "accent": (206, 248, 214),
                "edge": (152, 214, 182),
                "scanline": (188, 246, 214),
                "noise": (176, 248, 214, 24),
                "rgb_shift": (1, 0),
            },
            "enemy": {
                "tint": (156, 94, 210, 52),
                "accent": (228, 196, 255),
                "edge": (168, 112, 226),
                "scanline": (206, 172, 248),
                "noise": (212, 182, 255, 28),
                "rgb_shift": (1, -1),
            },
        }
        return profiles.get(role, profiles["chakana_mage"])

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

        if role == "guide":
            guide_files = {
                "concept": [("guide_master_concept.png", "official_master"), ("guide_portrait.png", "generated"), ("angel.png", "placeholder")],
                "portrait": [("guide_master_portrait.png", "official_master"), ("guide_portrait.png", "generated"), ("angel.png", "placeholder")],
                "hologram": [("guide_master_hologram.png", "official_master"), ("guide_hologram.png", "generated"), ("arcane_hacker.png", "placeholder")],
            }
            out: list[tuple[Path, str]] = []
            for filename, tag in guide_files.get(style, []):
                for root in roots:
                    out.append((root / filename, tag))
                out.append((assets_dir() / "sprites" / "guides" / filename, tag))
            return out

        if role == "enemy":
            enemy_files = {
                "concept": [("enemy_master_concept.png", "official_master"), ("enemy_portrait.png", "generated"), ("archon.png", "placeholder")],
                "portrait": [("enemy_master_portrait.png", "official_master"), ("enemy_portrait.png", "generated"), ("archon.png", "placeholder")],
                "hologram": [("enemy_master_hologram.png", "official_master"), ("enemy_hologram.png", "generated"), ("archon_holo.png", "placeholder")],
            }
            out: list[tuple[Path, str]] = []
            for filename, tag in enemy_files.get(style, []):
                for root in roots:
                    out.append((root / filename, tag))
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
        profile = self._role_profile(role)

        dw = max(24, w // 2)
        dh = max(24, h // 2)
        pixel = pygame.transform.scale(fitted, (dw, dh))
        pixel = pygame.transform.scale(pixel, (w, h))

        vignette = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 72), vignette.get_rect(), 5, border_radius=12)
        pixel.blit(vignette, (0, 0))

        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        tr, tg, tb, _ = profile["tint"]
        shade.fill((int(tr * 0.45), int(tg * 0.35), int(tb * 0.35), 54))
        pixel.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        left = pygame.Surface((max(8, w // 10), h), pygame.SRCALPHA)
        left.fill((*profile["accent"], 18))
        pixel.blit(left, (0, 0))
        pygame.draw.rect(pixel, profile["edge"], pixel.get_rect(), 2, border_radius=8)
        return pixel

    def _to_holographic(self, source: pygame.Surface, role: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = max(16, int(size[0])), max(16, int(size[1]))
        base = self._stylize_portrait(source, role, size)
        profile = self._role_profile(role)

        tint = pygame.Surface((w, h), pygame.SRCALPHA)
        tint.fill(profile["tint"])
        base.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        scan = pygame.Surface((w, h), pygame.SRCALPHA)
        line_col = profile["scanline"]
        for y in range(1, h, 3):
            pygame.draw.line(scan, (*line_col, 34), (2, y), (w - 3, y), 1)
        base.blit(scan, (0, 0))

        for y in range(6, h - 6, 13):
            wobble = 1 if ((y // 13) % 2 == 0) else -1
            band = base.subsurface(pygame.Rect(0, y, w, 1)).copy()
            base.blit(band, (wobble, y))

        rx, bx = profile["rgb_shift"]
        if rx or bx:
            r = base.copy()
            b = base.copy()
            r.fill((255, 0, 0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            b.fill((0, 0, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
            base.blit(r, (rx, 0), special_flags=pygame.BLEND_RGBA_ADD)
            base.blit(b, (bx, 0), special_flags=pygame.BLEND_RGBA_ADD)

        noise = pygame.Surface((w, h), pygame.SRCALPHA)
        nr, ng, nb, na = profile["noise"]
        for y in range(0, h, 7):
            if (y // 7) % 2 == 0:
                pygame.draw.line(noise, (nr, ng, nb, na), (4, y), (w - 4, y), 1)
        base.blit(noise, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        pygame.draw.rect(base, profile["accent"], base.get_rect(), 1, border_radius=8)
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
        if style == "codex":
            style = "portrait"
            size = (max(64, int(size[0])), max(64, int(size[1])))
        if style == "mini":
            style = "hologram"
            size = (max(28, int(size[0])), max(28, int(size[1])))

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
        current_stamp = self._source_stamp(role, style if style not in {"codex", "mini"} else ("portrait" if style == "codex" else "hologram"))

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

    def get_codex_portrait(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.get_style(name, size, "codex")

    def get_mini_avatar(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.get_style(name, size, "mini")

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
