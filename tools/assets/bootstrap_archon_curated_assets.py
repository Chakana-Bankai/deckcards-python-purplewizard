from __future__ import annotations

from pathlib import Path
import shutil

from game.core.paths import assets_dir


def run() -> dict:
    root = assets_dir()
    curated = root / "curated" / "avatars"
    curated.mkdir(parents=True, exist_ok=True)

    targets = {
        "archon_master_concept.png": None,
        "archon_master_portrait.png": None,
        "archon_master_hologram.png": None,
    }

    candidates = [
        root / "sprites" / "avatar" / "archon_oracle.png",
        root / "sprites" / "avatar" / "archon_hologram.png",
        root / "sprites" / "avatar" / "archon_portrait.png",
        root / "sprites" / "player" / "archon_oracle.png",
    ]

    # Fallback to generated visual cache if sprite candidates do not exist.
    vroot = Path(__file__).resolve().parents[1] / "game" / "visual" / "generated" / "avatar"
    if vroot.exists():
        candidates.extend(sorted(vroot.glob("archon_oracle_*.png")))

    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        return {"status": "WARNING", "message": "archon source missing", "created": []}

    created = []
    for filename in targets:
        dst = curated / filename
        if not dst.exists():
            shutil.copy2(source, dst)
            created.append(str(dst))

    return {
        "status": "PASS",
        "source": str(source),
        "created": created,
    }


if __name__ == "__main__":
    out = run()
    print(out)
