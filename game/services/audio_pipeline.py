from __future__ import annotations

import time

from game.core.bootstrap_assets import ensure_bgm_assets
from game.core.paths import data_dir
from game.core.safe_io import atomic_write_json


class AudioPipeline:
    def ensure_music_assets(self, settings: dict, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Cargando música", 0.92)
        try:
            manifest = ensure_bgm_assets(force_regen=bool(settings.get("force_regen_music", False)))
        except Exception as exc:
            print(f"[audio_safe] fallback music generation failed: {exc}")
            manifest = {}
        payload = {"generator_version": "bgm_v2", "created_at": int(time.time()), "items": manifest if isinstance(manifest, dict) else {}}
        if bool(settings.get("force_regen_music", False) or settings.get("update_manifests", False)):
            atomic_write_json(data_dir() / "audio_manifest.json", payload)
        return manifest
