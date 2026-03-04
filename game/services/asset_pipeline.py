from __future__ import annotations

import json
import time
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, GEN_BIOME_VERSION, chakana_points
from game.content.card_art_generator import export_prompts
from game.core.paths import assets_dir, data_dir
from game.core.safe_io import load_json


class AssetPipeline:
    def __init__(self, card_gen, enemy_gen, guide_gen, bg_gen):
        self.card_gen = card_gen
        self.enemy_gen = enemy_gen
        self.guide_gen = guide_gen
        self.bg_gen = bg_gen

    def _safe_manifest(self, path: Path) -> dict:
        payload = {"generator_version": GEN_ART_VERSION, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": {}}
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw.setdefault("generator_version", GEN_ART_VERSION)
                raw.setdefault("created_at", payload["created_at"])
                raw.setdefault("items", {})
                return raw
        except Exception:
            pass
        bak = path.with_suffix(".bak")
        try:
            path.replace(bak)
        except Exception:
            pass
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def _placeholder_png(self, path: Path, size=(256, 256), label: str = "?"):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((36, 26, 52))
        pts = chakana_points((size[0] // 2, size[1] // 2), min(size) // 4)
        pygame.draw.polygon(surf, (212, 182, 250), pts, 3)
        pygame.draw.circle(surf, (96, 76, 136), (size[0] // 2, size[1] // 2), min(size) // 3, 1)
        pygame.image.save(surf, path)

    def _safe_gen(self, asset_id: str, out_path: Path, fn, manifest_items: dict, placeholder_size=(256, 256)):
        try:
            fn()
            manifest_items[asset_id] = {"path": str(out_path), "generator_version": GEN_ART_VERSION, "placeholder": False}
        except Exception as exc:
            print(f"[safe_gen] using placeholder for {asset_id} due to {exc}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._placeholder_png(out_path, size=placeholder_size, label=asset_id)
            manifest_items[asset_id] = {"path": str(out_path), "generator_version": GEN_ART_VERSION, "placeholder": True, "error": str(exc)}

    def ensure_card_art(self, settings: dict, cards: list[dict], prompt_data: dict, manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        a = assets_dir() / "sprites" / "cards"
        total = max(1, len(cards))
        for i, c in enumerate(cards, 1):
            cid = c.get("id", "unknown")
            path = a / f"{cid}.png"
            pentry = prompt_data.get(cid, {}) if isinstance(prompt_data, dict) else {}
            self._safe_gen(
                cid,
                path,
                lambda cid=cid, c=c, mode=mode, pentry=pentry: self.card_gen.ensure_art(cid, c.get("tags", []), c.get("rarity", "common"), mode, family=pentry.get("family"), symbol=pentry.get("symbol")),
                manifest_items,
                placeholder_size=(256, 384),
            )
            if progress_cb:
                progress_cb(f"Generando arte de cartas ({i}/{total})", 0.24 + 0.36 * (i / total))

    def ensure_enemy_portraits(self, settings: dict, enemies: list[dict], manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        a = assets_dir() / "sprites" / "enemies"
        total = max(1, len(enemies))
        for i, e in enumerate(enemies, 1):
            eid = e.get("id", "dummy")
            path = a / f"{eid}.png"
            self._safe_gen(
                f"enemy:{eid}",
                path,
                lambda eid=eid, e=e, mode=mode: self.enemy_gen.ensure_art(eid, mode, tier=e.get("tier", "common"), biome=e.get("biome", "ukhu")),
                manifest_items,
            )
            if progress_cb:
                progress_cb(f"Generando retratos de enemigos ({i}/{total})", 0.60 + 0.14 * (i / total))

    def ensure_guides(self, settings: dict, guide_types: list[str], manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        total = max(1, len(guide_types))
        for i, gt in enumerate(guide_types, 1):
            path = assets_dir() / "sprites" / "guides" / f"{gt}.png"
            self._safe_gen(f"guide:{gt}", path, lambda gt=gt, mode=mode: self.guide_gen.generate(gt, mode=mode), manifest_items)
            if progress_cb:
                progress_cb(f"Generando guías ({i}/{total})", 0.74 + 0.06 * (i / total))

    def ensure_biomes(self, manifest: dict, progress_cb=None):
        a = assets_dir()
        biome_manifest = {}
        total = max(1, len(self.bg_gen.BIOMES))
        for i, biome in enumerate(self.bg_gen.BIOMES, 1):
            try:
                self.bg_gen.get_layers(biome, 2026)
            except Exception as exc:
                print(f"[safe_gen] using placeholder for biome:{biome} due to {exc}")
                bdir = a / "sprites" / "biomes" / biome.lower().replace(" ", "_")
                bdir.mkdir(parents=True, exist_ok=True)
                for name in ["bg", "mg", "fg"]:
                    self._placeholder_png(bdir / f"{name}.png", size=(1920, 610), label=biome)
            bdir = a / "sprites" / "biomes" / biome.lower().replace(" ", "_")
            biome_manifest[biome] = {"bg": str(bdir / "bg.png"), "mg": str(bdir / "mg.png"), "fg": str(bdir / "fg.png"), "generator_version": GEN_BIOME_VERSION}
            if progress_cb:
                progress_cb(f"Generando biomas ({biome})", 0.80 + 0.10 * (i / total))
        (data_dir() / "biome_manifest.json").write_text(json.dumps(biome_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_all_assets(self, settings: dict, content: dict, progress_cb=None):
        a = assets_dir()
        (a / "music").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "cards").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "enemies").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "biomes").mkdir(parents=True, exist_ok=True)
        (a / "sprites" / "guides").mkdir(parents=True, exist_ok=True)
        (a / "sfx" / "generated").mkdir(parents=True, exist_ok=True)

        prompt_data = load_json(data_dir() / "card_prompts.json", default={})
        cards = content.get("cards", [])
        enemies = content.get("enemies", [])
        if not isinstance(prompt_data, dict) or len(prompt_data) != len(cards):
            export_prompts(cards, enemies)
            prompt_data = load_json(data_dir() / "card_prompts.json", default={})
            if not isinstance(prompt_data, dict):
                prompt_data = {}

        manifest_path = data_dir() / "art_manifest.json"
        art_manifest = self._safe_manifest(manifest_path)
        items = art_manifest.setdefault("items", {})

        self.ensure_card_art(settings, cards, prompt_data, items, progress_cb)
        self.ensure_enemy_portraits(settings, enemies, items, progress_cb)
        self.ensure_guides(settings, content.get("guide_types", []), items, progress_cb)
        self.ensure_biomes(art_manifest, progress_cb)

        manifest_path.write_text(json.dumps(art_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir() / "prompt_manifest.json").write_text(json.dumps({"count": len(cards), "generator_version": GEN_ART_VERSION}, ensure_ascii=False, indent=2), encoding="utf-8")
        settings["force_regen_art"] = False
        return art_manifest
