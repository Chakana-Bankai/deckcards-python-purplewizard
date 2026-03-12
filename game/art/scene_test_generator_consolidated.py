from __future__ import annotations

import json
import os
from pathlib import Path

import pygame

from game.art.geometric_ritual_engine import render_card_from_dna
from game.art.shape_dna import export_identity_dataset_summary
from game.art.system_registry import CANONICAL_MODULES, LEGACY_MODULES, canonical_pipeline_order
from game.core.paths import project_root

TEST_IDS = {
    "solar_warrior": "HYP-SOLAR-ATTACK-GUERRERO_ASTRAL_DE_HIPERBOREA_I",
    "archon": "ARC-ARCHON-ATTACK-ARCANO_DEL_VACIO_01",
    "guide_mage": "BASE-GUIDE-GUARD-CAMPO_PROTECTOR",
}


def main() -> int:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = Path(project_root())
    out_dir = root / "assets" / "test_identity_v2"
    report_path = root / "reports" / "art" / "art_engine_consolidation_report.txt"
    dataset_path = root / "data" / "card_dna" / "identity_dataset_v2.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    dataset_summary = export_identity_dataset_summary(dataset_path)
    lines = [
        "art_engine_consolidation_report",
        f"canonical_modules={json.dumps(CANONICAL_MODULES, ensure_ascii=True)}",
        f"legacy_modules={json.dumps(LEGACY_MODULES, ensure_ascii=True)}",
        f"canonical_pipeline={' -> '.join(canonical_pipeline_order())}",
        f"identity_dataset_count={dataset_summary.get('count', 0)}",
        "",
    ]

    for label, card_id in TEST_IDS.items():
        out_path = out_dir / f"{label}_identity_v2.png"
        result = render_card_from_dna(card_id, out_path)
        identity = result["identity_lock"]
        lines.extend([
            f"[{label.upper()}]",
            f"card_id={card_id}",
            f"path={out_path.as_posix()}",
            f"archetype={result['dna']['archetype']}",
            f"weapon_type={result['dna']['weapon_type']}",
            f"energy_type={result['dna']['energy_type']}",
            f"pose_type={result['dna']['pose_type']}",
            f"occ_subject={identity['occ_subject']}",
            f"occ_object={identity['occ_object']}",
            f"silhouette_integrity={identity['silhouette_integrity']}",
            f"identity_lock_passed={identity['passed']}",
            "",
        ])

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"[art_consolidation] out={out_dir}")
    print(f"[art_consolidation] report={report_path}")
    print(f"[art_consolidation] dataset={dataset_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
