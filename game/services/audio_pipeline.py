from __future__ import annotations

import time

from game.core.bootstrap_assets import ensure_bgm_assets
from game.core.paths import data_dir
from game.core.safe_io import atomic_write_json, load_json


class AudioPipeline:
    def ensure_music_assets(self, settings: dict, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Cargando mÃºsica", 0.92)

        regen_requested = bool(settings.get("force_regen_music", False) or settings.get("update_manifests", False))
        if not regen_requested:
            existing = load_json(data_dir() / "bgm_manifest.json", default={})
            return existing if isinstance(existing, dict) else {}

        try:
            manifest = ensure_bgm_assets(force_regen=bool(settings.get("force_regen_music", False)))
        except Exception as exc:
            print(f"[audio_safe] fallback music generation failed: {exc}")
            manifest = {}

        items = manifest if isinstance(manifest, dict) else {}
        profile_counts = {
            "menu_map_lore": 0,
            "shop_reward": 0,
            "combat": 0,
            "boss": 0,
        }
        for meta in items.values():
            if not isinstance(meta, dict):
                continue
            profile = str(meta.get("mood_profile", "")).strip().lower()
            if profile in profile_counts:
                profile_counts[profile] += 1

        payload = {
            "generator_version": "bgm_v3",
            "created_at": int(time.time()),
            "items": items,
            "profiles": profile_counts,
        }
        atomic_write_json(data_dir() / "audio_manifest.json", payload)
        return items
