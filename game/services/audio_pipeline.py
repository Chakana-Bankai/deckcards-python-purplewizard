from __future__ import annotations

from game.core.bootstrap_assets import ensure_bgm_assets


class AudioPipeline:
    def ensure_music_assets(self, settings: dict, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Cargando música", 0.92)
        try:
            return ensure_bgm_assets(force_regen=bool(settings.get("force_regen_music", False)))
        except Exception as exc:
            print(f"[audio_safe] fallback music generation failed: {exc}")
            return {}
