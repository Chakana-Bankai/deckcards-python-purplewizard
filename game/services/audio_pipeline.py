from __future__ import annotations

import time

from game.core.bootstrap_assets import ensure_bgm_assets
from game.core.paths import data_dir
<<<<<<< ours
from game.core.safe_io import atomic_write_json
=======
from game.core.safe_io import atomic_write_json, load_json
>>>>>>> theirs


class AudioPipeline:
    def ensure_music_assets(self, settings: dict, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Cargando música", 0.92)
<<<<<<< ours
=======

        regen_requested = bool(settings.get("force_regen_music", False) or settings.get("update_manifests", False))
        if not regen_requested:
            existing = load_json(data_dir() / "bgm_manifest.json", default={})
            return existing if isinstance(existing, dict) else {}

>>>>>>> theirs
        try:
            manifest = ensure_bgm_assets(force_regen=bool(settings.get("force_regen_music", False)))
        except Exception as exc:
            print(f"[audio_safe] fallback music generation failed: {exc}")
            manifest = {}
<<<<<<< ours
        payload = {"generator_version": "bgm_v2", "created_at": int(time.time()), "items": manifest if isinstance(manifest, dict) else {}}
        if bool(settings.get("force_regen_music", False) or settings.get("update_manifests", False)):
            atomic_write_json(data_dir() / "audio_manifest.json", payload)
=======

        payload = {
            "generator_version": "bgm_v2",
            "created_at": int(time.time()),
            "items": manifest if isinstance(manifest, dict) else {},
        }
        atomic_write_json(data_dir() / "audio_manifest.json", payload)
>>>>>>> theirs
        return manifest
