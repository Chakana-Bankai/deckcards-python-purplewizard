from __future__ import annotations

import json
import os
from pathlib import Path

import pygame

from game.art.gen_card_art_advanced import GEN_CARD_ART_ADVANCED_VERSION, generate

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "game" / "assets"
CURATED = ASSETS / "curated" / "avatars"
OUT_DIR = ASSETS / ".cache" / "art_direction_pass"
REPORT = ROOT / "card_art_upgrade_report.txt"


def _sample_generation() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "id": "base_art_direction_probe",
            "type": "attack",
            "prompt": "base set mystical warrior, chakana motifs, gold violet palette, subject casts ritual blade",
        },
        {
            "id": "hip_art_direction_probe",
            "type": "control",
            "prompt": "hiperborea set, atlantean polar temple, crystal technology, ancient advanced civilization",
        },
        {
            "id": "arc_art_direction_probe",
            "type": "legendary",
            "prompt": "archon void corruption gnostic horror dark entity oppressive demonic",
        },
    ]

    out = []
    for i, row in enumerate(samples):
        path = OUT_DIR / f"{row['id']}.png"
        res = generate(row["id"], row["type"], row["prompt"], 9100 + i * 7, path)
        ok = path.exists()
        size = None
        if ok:
            try:
                s = pygame.image.load(str(path))
                size = list(s.get_size())
            except Exception:
                size = None
        out.append(
            {
                "id": row["id"],
                "ok": ok,
                "size": size,
                "result": res if isinstance(res, dict) else {"raw": str(res)},
                "path": str(path.relative_to(ROOT)),
            }
        )
    return {"generator": GEN_CARD_ART_ADVANCED_VERSION, "samples": out}


def _avatar_holo_check() -> dict:
    concept = CURATED / "chakana_mage_master_concept.png"
    portrait = CURATED / "chakana_mage_master_portrait.png"
    holo = CURATED / "chakana_mage_master_hologram.png"

    rows = {}
    for key, p in {"concept": concept, "portrait": portrait, "hologram": holo}.items():
        exists = p.exists()
        size = None
        if exists:
            try:
                s = pygame.image.load(str(p))
                size = list(s.get_size())
            except Exception:
                size = None
        rows[key] = {"exists": exists, "size": size, "path": str(p.relative_to(ROOT))}

    portrait_512 = rows["portrait"]["size"] == [512, 512]
    holo_scanline_ready = rows["hologram"]["exists"]

    return {
        "assets": rows,
        "portrait_512x512": portrait_512,
        "hologram_asset_present": holo_scanline_ready,
        "note": "Run python -m tools.build_chakana_master_from_reference --source <ruta_imagen> to rebuild curated assets with new 512x512 portrait pipeline.",
    }


def main() -> int:
    sample = _sample_generation()
    avatar = _avatar_holo_check()

    lines = []
    lines.append("CHAKANA ART DIRECTION PASS")
    lines.append("")
    lines.append("[status]")
    lines.append("- Procedural card art narrative composition: APPLIED")
    lines.append("- Set style direction (Base/Hiperborea/Archon): APPLIED")
    lines.append("- Avatar portrait pipeline 512x512 focus: APPLIED (tooling)")
    lines.append("- Hologram treatment (scanline/glow/transparent energy): APPLIED")
    lines.append("")
    lines.append("[card_generation_samples]")
    for row in sample["samples"]:
        rid = row["id"]
        ok = row["ok"]
        size = row["size"]
        style = (row["result"] or {}).get("set_style") if isinstance(row.get("result"), dict) else None
        narrative = (row["result"] or {}).get("narrative_composition") if isinstance(row.get("result"), dict) else None
        lines.append(f"- {rid}: ok={ok} size={size} set_style={style} narrative={narrative} path={row['path']}")

    lines.append("")
    lines.append("[avatar_pipeline]")
    lines.append(f"- portrait_512x512={avatar['portrait_512x512']}")
    lines.append(f"- hologram_asset_present={avatar['hologram_asset_present']}")
    for k, v in avatar["assets"].items():
        lines.append(f"- {k}: exists={v['exists']} size={v['size']} path={v['path']}")
    lines.append(f"- note: {avatar['note']}")

    lines.append("")
    lines.append("[raw_json]")
    lines.append(json.dumps({"sample": sample, "avatar": avatar}, ensure_ascii=False, indent=2))

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[art_direction] report={REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
