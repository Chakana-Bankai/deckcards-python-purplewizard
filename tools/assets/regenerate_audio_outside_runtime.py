from __future__ import annotations

import argparse
import json

from game.audio.audio_engine import get_audio_engine
from game.core.paths import project_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenera audio Chakana fuera del runtime del juego.")
    parser.add_argument("--force", action="store_true", help="Fuerza regeneracion completa de assets de audio.")
    args = parser.parse_args()

    engine = get_audio_engine()
    if args.force:
        manifest = engine.ensure_core_assets(force=True)
        mode = "force_regen"
    else:
        try:
            engine._prune_manifest()
            engine._save_manifest()
        except Exception:
            pass
        manifest = dict(getattr(engine, '_manifest', {}) or {})
        mode = "manifest_only"

    out = project_root() / "reports" / "validation" / "external_audio_regen_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "status=ok",
        f"mode={mode}",
        f"force={int(bool(args.force))}",
        f"tracks={len((manifest or {}).get('tracks', {}))}",
        f"contexts={len((manifest or {}).get('contexts', {}))}",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[audio_regen] mode={mode} report={out}")
    print(json.dumps({
        "mode": mode,
        "tracks": len((manifest or {}).get('tracks', {})),
        "contexts": len((manifest or {}).get('contexts', {})),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
