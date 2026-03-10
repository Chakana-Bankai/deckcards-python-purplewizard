from __future__ import annotations

from game.audio.audio_engine import get_audio_engine


class AudioPipeline:
    def ensure_music_assets(self, settings: dict, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Cargando musica", 0.92)

        force = bool(settings.get("force_regen_music", False) or settings.get("update_manifests", False))
        engine = get_audio_engine()

        if force:
            manifest = engine.ensure_core_assets(force=True)
            return manifest if isinstance(manifest, dict) else {}

        # Normal boot must stay lazy: keep existing manifests and generate on demand
        # when a specific context is actually played. This avoids startup freezes.
        try:
            engine._prune_manifest()
            engine._save_manifest()
        except Exception:
            pass
        return dict(getattr(engine, "_manifest", {}) or {})
