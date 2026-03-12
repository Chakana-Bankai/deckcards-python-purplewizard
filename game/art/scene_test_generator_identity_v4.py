from __future__ import annotations

import json
import os
from pathlib import Path

import pygame

from game.art.geometric_ritual_engine import render_card_from_dna
from game.core.paths import project_root

TEST_IDS = {
    'solar_warrior': 'HYP-SOLAR-ATTACK-GUERRERO_ASTRAL_DE_HIPERBOREA_I',
    'archon': 'ARC-ARCHON-ATTACK-ARCANO_DEL_VACIO_01',
    'guide_mage': 'BASE-GUIDE-GUARD-CAMPO_PROTECTOR',
}


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = Path(project_root())
    out_dir = root / 'assets' / 'test_identity_v4'
    report_path = root / 'reports' / 'art' / 'test_identity_v4_report.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['test_identity_v4_report', '']
    for label, card_id in TEST_IDS.items():
        out_path = out_dir / f'{label}_identity_v4.png'
        result = render_card_from_dna(card_id, out_path)
        identity = result['identity_lock']
        lines.extend([
            f'[{label.upper()}]',
            f'card_id={card_id}',
            f'path={out_path.as_posix()}',
            f'archetype={result["dna"]["archetype"]}',
            f'weapon_type={result["dna"]["weapon_type"]}',
            f'energy_type={result["dna"]["energy_type"]}',
            f'pose_type={result["dna"]["pose_type"]}',
            f'occ_subject={identity["occ_subject"]}',
            f'occ_object={identity["occ_object"]}',
            f'silhouette_integrity={identity["silhouette_integrity"]}',
            f'identity_lock_passed={identity["passed"]}',
            '',
        ])
    report_path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    print(json.dumps({'out_dir': out_dir.as_posix(), 'report': report_path.as_posix()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
