from __future__ import annotations

import json
import time
from pathlib import Path

import pygame

from .generators import (
    AvatarGenerator,
    BiomeGenerator,
    EmblemGenerator,
    IconGenerator,
    RelicGenerator,
    SacredOverlayGenerator,
)
from .generators.lore_motifs import MOTIF_LIBRARY


class VisualEngine:
    """Centralized procedural visual identity engine with manifest cache."""

    VERSION = "visual_v2"
    PALETTE = {
        "deep_purple": (28, 18, 44),
        "violet": (126, 82, 196),
        "gold": (226, 194, 126),
        "cyan": (112, 214, 235),
        "void": (10, 8, 20),
    }

    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.generated_root = self.root / "generated"
        self.manifest_path = self.root / "visual_manifest.json"
        self._ensure_dirs()
        self.manifest = self._load_manifest()
        self.avatar = AvatarGenerator()
        self.icon = IconGenerator()
        self.relic = RelicGenerator()
        self.biome = BiomeGenerator()
        self.emblem = EmblemGenerator()
        self.overlay = SacredOverlayGenerator()
        self._surface_cache: dict[tuple[str, str, tuple[int, int], str], pygame.Surface] = {}

    def _ensure_dirs(self):
        for d in [
            self.generated_root,
            self.generated_root / "avatar",
            self.generated_root / "icons",
            self.generated_root / "relics",
            self.generated_root / "biomes",
            self.generated_root / "emblems",
            self.generated_root / "overlays",
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": self.VERSION, "generated_at": int(time.time()), "items": {}}
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("version", self.VERSION)
                data.setdefault("generated_at", int(time.time()))
                data.setdefault("items", {})
                return data
        except Exception:
            pass
        return {"version": self.VERSION, "generated_at": int(time.time()), "items": {}}

    def _save_manifest(self):
        self.manifest["version"] = self.VERSION
        self.manifest["generated_at"] = int(time.time())
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def _seed(self, asset_id: str) -> int:
        return abs(hash(f"{self.VERSION}:{asset_id}")) % (2**31 - 1)

    def _item_key(self, category: str, asset_id: str, size: tuple[int, int], context: str = "") -> str:
        return f"{category}:{asset_id}:{int(size[0])}x{int(size[1])}:{context}"

    def _path_for(self, category: str, asset_id: str, size: tuple[int, int], context: str = "") -> Path:
        suffix = f"_{context}" if context else ""
        name = f"{asset_id}_{int(size[0])}x{int(size[1])}{suffix}.png"
        return self.generated_root / category / name

    def _load_surface(self, path: Path) -> pygame.Surface | None:
        try:
            if path.exists():
                return pygame.image.load(str(path)).convert_alpha()
        except Exception:
            return None
        return None

    def _lore_tags(self, asset_id: str, context: str) -> list[str]:
        key = f"{asset_id}:{context}".lower()
        tags = []
        for motif in MOTIF_LIBRARY.keys():
            if motif in key:
                tags.append(motif)
        if "archon" in key and "archons" not in tags:
            tags.append("archons")
        if "chakana" in key and "chakana" not in tags:
            tags.append("chakana")
        return tags

    def _register(self, key: str, category: str, asset_id: str, context: str, size: tuple[int, int], path: Path):
        items = self.manifest.setdefault("items", {})
        items[key] = {
            "asset_id": asset_id,
            "category": category,
            "seed": self._seed(asset_id),
            "palette": self.PALETTE,
            "output_paths": [str(path)],
            "context": context,
            "version": self.VERSION,
            "generated_at": int(time.time()),
            "size": [int(size[0]), int(size[1])],
            "state": "valid" if path.exists() else "missing",
            "lore_tags": self._lore_tags(asset_id, context),
        }
        self._save_manifest()

    def generate(self, category: str, asset_id: str, size: tuple[int, int], context: str = "", force: bool = False) -> pygame.Surface:
        cat = str(category or "icons").lower()
        aid = str(asset_id or "default").lower()
        size = (max(12, int(size[0])), max(12, int(size[1])))
        cctx = str(context or "")
        cache_key = (cat, aid, size, cctx)
        key = self._item_key(cat, aid, size, cctx)

        if not force and cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        path = self._path_for(cat, aid, size, cctx)
        if not force and path.exists():
            surf = self._load_surface(path)
            if surf is not None:
                self._surface_cache[cache_key] = surf
                return surf

        if cat == "avatar":
            surf = self.avatar.render(aid if not cctx else cctx, size, seed=self._seed(key))
        elif cat == "icons":
            surf = self.icon.render(aid, size)
        elif cat == "relics":
            rarity = cctx or "common"
            surf = self.relic.render(aid, rarity, size)
        elif cat == "biomes":
            motif = cctx or "bg"
            surf = self.biome.render_panel(aid, size, motif=motif)
        elif cat == "emblems":
            mini = cctx == "mini"
            surf = self.emblem.render(aid, size, mini=mini)
        elif cat == "overlays":
            alpha = 74 if cctx == "boss" else 54
            surf = self.overlay.render(aid, size, alpha=alpha)
        else:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            surf.fill((58, 46, 88, 255))
            pygame.draw.rect(surf, (122, 102, 184), surf.get_rect(), 2)

        try:
            pygame.image.save(surf, str(path))
        except Exception:
            pass
        self._register(key, cat, aid, cctx, size, path)
        self._surface_cache[cache_key] = surf
        print(f"[visual] {cat}/{aid} source=generated ctx={cctx or '-'}")
        return surf

    def ensure_core(self, force: bool = False):
        # Non-destructive baseline generation only.
        self.generate("avatar", "combat_hud", (192, 192), context="combat_hud", force=force)
        self.generate("avatar", "menu", (256, 256), context="menu", force=force)
        self.generate("avatar", "archon_oracle", (192, 192), context="archon_oracle", force=force)
        self.generate("relics", "violet_seal", (128, 128), context="rare", force=force)
        self.generate("biomes", "ukhu_pacha", (512, 256), context="sigil", force=force)
        self.generate("biomes", "fractura_chakana", (512, 256), context="sigil", force=force)
        self.generate("emblems", "cosmic_warrior", (96, 96), context="mini", force=force)


_ENGINE: VisualEngine | None = None


def get_visual_engine() -> VisualEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = VisualEngine()
    return _ENGINE
