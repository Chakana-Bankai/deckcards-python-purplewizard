from __future__ import annotations

import json
from pathlib import Path

import pygame

from game.art.gen_guide_art32 import GEN_GUIDE_ART_VERSION, render_guide
from game.core.paths import assets_dir, data_dir

GUIDE_TYPES = ["angel", "shaman", "demon", "arcane_hacker"]


class GuideAvatarGenerator:
    def __init__(self):
        self.out_dir = assets_dir() / "sprites" / "guides"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, guide_type: str, mode: str = "missing_only") -> Path:
        gt = guide_type if guide_type in GUIDE_TYPES else "angel"
        out = self.out_dir / f"{gt}.png"
        if out.exists() and mode == "missing_only":
            return out
        surf = render_guide(gt)
        pygame.image.save(surf.convert_alpha(), out)
        manifest = {"generator_version": GEN_GUIDE_ART_VERSION, "items": {g: str(self.out_dir / f"{g}.png") for g in GUIDE_TYPES}}
        (data_dir() / "art_manifest_guides.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
