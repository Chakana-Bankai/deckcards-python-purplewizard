from __future__ import annotations

import os

import pygame

from game.art.assembly_pipeline import assemble_scene_art
from game.core.paths import project_root

PROMPT = (
    'palette gold amber ivory, motif solar warrior attack spear mountain, sacred geometry solar disc, '
    'subject solar warrior champion, object radiant spear, environment warm mountain citadel, scene type hyperborea_temple_scene, '
    'subject pose solar_warrior_attack, secondary object spear, camera heroic medium close, mood heroic radiant, '
    'subject kind warrior_foreground, object kind spear, environment kind citadel, effects warm light solar aura, '
    'effect signature spear flare, energy pattern sun arc, lore tokens solar warrior attack spear mountain solar'
)

SEEDS = [20301, 20377]


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'test_identity_crisp'
    report_path = root / 'reports' / 'art' / 'solar_warrior_heroic_report.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['solar_warrior_heroic_examples', 'style_target=playable_placeholder_with_identity', '']
    for index, seed in enumerate(SEEDS, start=1):
        out_path = out_dir / f'solar_warrior_heroic_{index}.png'
        result = assemble_scene_art(f'solar_warrior_heroic_{index}', PROMPT, seed, out_path)
        m = result.metrics
        lines.extend([
            f'[VARIANT_{index}]',
            f'path={out_path.as_posix()}',
            f'seed={seed}',
            f'silhouette_clarity={m.silhouette_integrity}',
            f'weapon_visibility={m.occ_object}',
            f'contrast={m.contrast_score}',
            f'focus_balance={m.focus_balance}',
            f'readability_ok={m.readability_ok}',
            '',
        ])
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    print(f'[solar_heroic] out={out_dir}')
    print(f'[solar_heroic] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
