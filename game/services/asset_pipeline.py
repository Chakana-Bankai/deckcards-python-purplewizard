from __future__ import annotations

import json
import time
import zlib
from pathlib import Path

import pygame

from game.art.gen_art32 import GEN_ART_VERSION, GEN_BIOME_VERSION, chakana_points
from game.art.gen_avatar_chakana import GEN_AVATAR_VERSION, render_avatar
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.content.card_art_generator import export_prompts
from game.core.paths import assets_dir, data_dir, sprite_category_dir
from game.core.safe_io import atomic_write_json, load_json


class AssetPipeline:
    def __init__(self, card_gen, enemy_gen, guide_gen, bg_gen):
        self.card_gen = card_gen
        self.enemy_gen = enemy_gen
        self.guide_gen = guide_gen
        self.bg_gen = bg_gen

    def _safe_manifest(self, path: Path) -> dict:
        payload = {"generator_version": GEN_ART_VERSION, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": {}}
        if not path.exists():
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
        return payload

    def _placeholder_png(self, path: Path, size=(256, 256), label: str = "?"):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((36, 26, 52))
        pts = chakana_points((size[0] // 2, size[1] // 2), min(size) // 4)
        pygame.draw.polygon(surf, (212, 182, 250), pts, 3)
        pygame.draw.circle(surf, (96, 76, 136), (size[0] // 2, size[1] // 2), min(size) // 3, 1)
        pygame.image.save(surf, path)

    def _safe_gen(self, asset_id: str, out_path: Path, fn, manifest_items: dict, placeholder_size=(256, 256), version=GEN_ART_VERSION):
        try:
            fn()
            manifest_items[asset_id] = {"id": asset_id, "path": str(out_path), "generator_version": version, "seed": zlib.crc32(asset_id.encode("utf-8")) & 0xFFFFFFFF, "created_at": int(time.time()), "placeholder": False}
        except Exception as exc:
            print(f"[safe_gen] using placeholder for {asset_id} due to {exc}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._placeholder_png(out_path, size=placeholder_size, label=asset_id)
            manifest_items[asset_id] = {"id": asset_id, "path": str(out_path), "generator_version": version, "seed": zlib.crc32(asset_id.encode("utf-8")) & 0xFFFFFFFF, "created_at": int(time.time()), "placeholder": True, "error": str(exc)}


    def _prompt_lookup(self, prompt_data: dict) -> dict:
        if not isinstance(prompt_data, dict):
            return {}
        cards = prompt_data.get("cards", {}) if isinstance(prompt_data.get("cards", {}), dict) else None
        if isinstance(cards, dict):
            return cards
        return prompt_data

    def ensure_card_art(self, settings: dict, cards: list[dict], prompt_data: dict, manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        a = sprite_category_dir("cards")
        total = max(1, len(cards))
        prompt_lookup = self._prompt_lookup(prompt_data)
        for i, c in enumerate(cards, 1):
            cid = c.get("id", "unknown")
            path = a / f"{cid}.png"
            pentry = prompt_lookup.get(cid, {}) if isinstance(prompt_lookup, dict) else {}
            prompt_text = pentry if isinstance(pentry, str) else (pentry.get("prompt") or pentry.get("prompt_text", ""))
            family = None if isinstance(pentry, str) else (pentry.get("style") or pentry.get("card_type") or pentry.get("family"))
            self._safe_gen(
                cid,
                path,
                lambda cid=cid, c=c, mode=mode, family=family, prompt_text=prompt_text: self.card_gen.ensure_art(cid, c.get("tags", []), c.get("rarity", "common"), mode, family=family, symbol=None, prompt=prompt_text),
                manifest_items,
                placeholder_size=(256, 384),
                version=GEN_CARD_ART_VERSION,
            )
            if progress_cb:
                progress_cb(f"Generando arte de cartas ({i}/{total})", 0.24 + 0.36 * (i / total))

    def ensure_enemy_portraits(self, settings: dict, enemies: list[dict], manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        a = sprite_category_dir("enemies")
        total = max(1, len(enemies))
        for i, e in enumerate(enemies, 1):
            eid = e.get("id", "dummy")
            path = a / f"{eid}.png"
            self._safe_gen(
                f"enemy:{eid}",
                path,
                lambda eid=eid, e=e, mode=mode: self.enemy_gen.ensure_art(eid, mode, tier=e.get("tier", "common"), biome=e.get("biome", "ukhu")),
                manifest_items,
                version=GEN_ART_VERSION,
            )
            if progress_cb:
                progress_cb(f"Generando retratos de enemigos ({i}/{total})", 0.60 + 0.14 * (i / total))

    def ensure_guides(self, settings: dict, guide_types: list[str], manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        total = max(1, len(guide_types))
        for i, gt in enumerate(guide_types, 1):
            path = sprite_category_dir("guides") / f"{gt}.png"
            self._safe_gen(f"guide:{gt}", path, lambda gt=gt, mode=mode: self.guide_gen.generate(gt, mode=mode), manifest_items, version=GEN_ART_VERSION)
            if progress_cb:
                progress_cb(f"Generando guias ({i}/{total})", 0.74 + 0.06 * (i / total))

    def _starter_banner_surface(self, starter_id: str, name: str, size: tuple[int, int]) -> pygame.Surface:
        w, h = size
        sid = str(starter_id or "starter")
        seed = zlib.crc32(sid.encode("utf-8")) & 0xFFFFFFFF
        r = 48 + (seed % 80)
        g = 34 + ((seed >> 3) % 70)
        b = 72 + ((seed >> 7) % 90)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        top = (min(255, r + 36), min(255, g + 24), min(255, b + 42))
        bot = (max(18, r - 12), max(18, g - 10), max(26, b - 16))
        for y in range(h):
            t = y / max(1, h - 1)
            col = (
                int(top[0] * (1.0 - t) + bot[0] * t),
                int(top[1] * (1.0 - t) + bot[1] * t),
                int(top[2] * (1.0 - t) + bot[2] * t),
            )
            pygame.draw.line(surf, col, (0, y), (w, y))
        cx, cy = w // 2, h // 2
        radius = max(20, min(w, h) // 3)
        pts = chakana_points((cx, cy), radius)
        pygame.draw.polygon(surf, (236, 216, 158, 60), pts, 2)
        for i in range(5):
            rr = max(6, radius - i * 8)
            pygame.draw.circle(surf, (255, 232, 176, max(16, 44 - i * 7)), (cx, cy), rr, 1)
        f = pygame.font.SysFont("arial", max(16, h // 5), bold=True)
        label = str(name or sid).strip()[:26]
        txt = f.render(label, True, (248, 238, 206))
        surf.blit(txt, (max(8, (w - txt.get_width()) // 2), h - txt.get_height() - 8))
        pygame.draw.rect(surf, (244, 214, 132), surf.get_rect(), 2, border_radius=10)
        return surf

    def ensure_starter_banners(self, settings: dict, starters: list[dict], manifest_items: dict, progress_cb=None):
        mode = "force_regen" if settings.get("force_regen_art", False) else "missing_only"
        out_dir = sprite_category_dir("starters")
        out_dir.mkdir(parents=True, exist_ok=True)
        total = max(1, len(starters))
        for i, st in enumerate(starters, 1):
            sid = str(st.get("id") or f"starter_{i}")
            name = str(st.get("name") or sid)
            path = out_dir / f"{sid}.png"
            if mode == "missing_only" and path.exists():
                manifest_items[f"starter:{sid}"] = {
                    "id": f"starter:{sid}",
                    "path": str(path),
                    "generator_version": GEN_ART_VERSION,
                    "seed": zlib.crc32(sid.encode("utf-8")) & 0xFFFFFFFF,
                    "created_at": int(time.time()),
                    "placeholder": False,
                }
            else:
                try:
                    banner = self._starter_banner_surface(sid, name, (640, 150))
                    pygame.image.save(banner, path)
                    manifest_items[f"starter:{sid}"] = {
                        "id": f"starter:{sid}",
                        "path": str(path),
                        "generator_version": GEN_ART_VERSION,
                        "seed": zlib.crc32(sid.encode("utf-8")) & 0xFFFFFFFF,
                        "created_at": int(time.time()),
                        "placeholder": False,
                    }
                except Exception as exc:
                    print(f"[safe_gen] using placeholder for starter:{sid} due to {exc}")
                    self._placeholder_png(path, size=(640, 150), label=sid)
                    manifest_items[f"starter:{sid}"] = {
                        "id": f"starter:{sid}",
                        "path": str(path),
                        "generator_version": GEN_ART_VERSION,
                        "seed": zlib.crc32(sid.encode("utf-8")) & 0xFFFFFFFF,
                        "created_at": int(time.time()),
                        "placeholder": True,
                        "error": str(exc),
                    }
            if progress_cb:
                progress_cb(f"Generando banners starter ({i}/{total})", 0.74 + 0.05 * (i / total))
    def ensure_biomes(self, manifest: dict, progress_cb=None, write_manifest: bool = False):
        a = assets_dir()
        biome_manifest = {}
        total = max(1, len(self.bg_gen.BIOMES))
        for i, biome in enumerate(self.bg_gen.BIOMES, 1):
            try:
                self.bg_gen.get_layers(biome, 2026)
            except Exception as exc:
                print(f"[safe_gen] using placeholder for biome:{biome} due to {exc}")
                bdir = sprite_category_dir("biomes") / biome.lower().replace(" ", "_")
                bdir.mkdir(parents=True, exist_ok=True)
                for name in ["bg", "mg", "fg"]:
                    self._placeholder_png(bdir / f"{name}.png", size=(1920, 610), label=biome)
            bdir = sprite_category_dir("biomes") / biome.lower().replace(" ", "_")
            biome_manifest[biome] = {"bg": str(bdir / "bg.png"), "mg": str(bdir / "mg.png"), "fg": str(bdir / "fg.png"), "generator_version": GEN_BIOME_VERSION}
            if progress_cb:
                progress_cb(f"Generando biomas ({biome})", 0.80 + 0.10 * (i / total))
        if write_manifest:
            atomic_write_json(data_dir() / "biome_manifest.json", biome_manifest)


    def ensure_avatar(self, write_manifest: bool = False):
        p_preview = sprite_category_dir("avatar") / "chakana.png"
        p_player = sprite_category_dir("player") / "chakana_avatar.png"
        p_preview.parent.mkdir(parents=True, exist_ok=True)
        p_player.parent.mkdir(parents=True, exist_ok=True)
        try:
            surf = render_avatar(0.0, 256)
            pygame.image.save(surf.convert_alpha(), p_preview)
            pygame.image.save(surf.convert_alpha(), p_player)
            if write_manifest:
                atomic_write_json(data_dir() / "art_manifest_avatar.json", {"generator_version": GEN_AVATAR_VERSION, "path": str(p_preview), "player_path": str(p_player)})
        except Exception as exc:
            print(f"[safe_gen] using placeholder for avatar:chakana due to {exc}")
            self._placeholder_png(p_preview, size=(256, 256), label="chakana")
            self._placeholder_png(p_player, size=(256, 256), label="chakana")

    def _default_prompt_payload(self, cards: list[dict]) -> dict:
        payload = {}
        for i, c in enumerate(cards):
            cid = c.get("id", f"card_{i}")
            tags = c.get("tags", []) or []
            ctype = "attack" if "attack" in tags else "defense" if ("block" in tags or "defense" in tags) else "control" if ("draw" in tags or "scry" in tags or "control" in tags) else "spirit"
            name = c.get("name_key", cid)
            payload[cid] = f"{name} | type={ctype} | seed={abs(hash(cid)) % 1000000}"
        return payload

    def ensure_all_assets(self, settings: dict, content: dict, progress_cb=None):
        write_manifests = bool(settings.get("force_regen_art", False) or settings.get("update_manifests", False))
        self.ensure_avatar(write_manifest=write_manifests)
        a = assets_dir()
        (a / "music").mkdir(parents=True, exist_ok=True)
        sprite_category_dir("cards").mkdir(parents=True, exist_ok=True)
        sprite_category_dir("enemies").mkdir(parents=True, exist_ok=True)
        sprite_category_dir("biomes").mkdir(parents=True, exist_ok=True)
        sprite_category_dir("guides").mkdir(parents=True, exist_ok=True)
        sprite_category_dir("starters").mkdir(parents=True, exist_ok=True)
        (a / "sfx" / "generated").mkdir(parents=True, exist_ok=True)

        cards = content.get("cards", [])
        enemies = content.get("enemies", [])
        prompt_data = load_json(data_dir() / "card_prompts.json", default={}, optional=True)
        if bool(settings.get("force_regen_art", False)):
            export_prompts(cards, enemies)
            prompt_data = load_json(data_dir() / "card_prompts.json", default={}, optional=True)
        if not isinstance(prompt_data, dict):
            prompt_data = {}

        manifest_path = data_dir() / "art_manifest.json"
        art_manifest = self._safe_manifest(manifest_path)
        items = art_manifest.setdefault("items", {})

        self.ensure_card_art(settings, cards, prompt_data, items, progress_cb)
        self.ensure_enemy_portraits(settings, enemies, items, progress_cb)
        self.ensure_guides(settings, content.get("guide_types", []), items, progress_cb)
        self.ensure_starter_banners(settings, content.get("starter_decks", []), items, progress_cb)
        self.ensure_biomes(art_manifest, progress_cb, write_manifest=write_manifests)

        if write_manifests:
            atomic_write_json(manifest_path, art_manifest)
            cards_manifest = {"generator_version": GEN_ART_VERSION, "items": {k: v for k, v in items.items() if not str(k).startswith("enemy:") and not str(k).startswith("guide:")}}
            enemies_manifest = {"generator_version": GEN_ART_VERSION, "items": {k: v for k, v in items.items() if str(k).startswith("enemy:")}}
            guides_manifest = {"generator_version": GEN_ART_VERSION, "items": {k: v for k, v in items.items() if str(k).startswith("guide:")}}
            starters_manifest = {"generator_version": GEN_ART_VERSION, "items": {k: v for k, v in items.items() if str(k).startswith("starter:")}}
            atomic_write_json(data_dir() / "art_manifest_cards.json", cards_manifest)
            atomic_write_json(data_dir() / "art_manifest_enemies.json", enemies_manifest)
            atomic_write_json(data_dir() / "art_manifest_guides.json", guides_manifest)
            atomic_write_json(data_dir() / "art_manifest_starters.json", starters_manifest)
            atomic_write_json(data_dir() / "prompt_manifest.json", {"count": len(cards), "generator_version": GEN_ART_VERSION})
        settings["force_regen_art"] = False
        placeholders = sum(1 for v in items.values() if isinstance(v, dict) and v.get("placeholder"))
        return {"manifest": art_manifest, "placeholders": placeholders}




