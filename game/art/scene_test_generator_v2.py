from __future__ import annotations

import os
from pathlib import Path

import pygame

from game.art.scene_engine import generate_scene_art
from game.core.paths import project_root

SCENE_PROMPTS = {
    'ARCHON': (
        'palette black crimson toxic green, '
        'motif archon corruption ritual, '
        'sacred geometry ritual seal, '
        'subject archon hierophant, '
        'object void ritual staff, '
        'environment void temple, '
        'scene type archon_void_scene, '
        'subject pose ritual pose, '
        'secondary object staff, '
        'camera ominous low angle, '
        'mood oppressive malign, '
        'subject kind archon_foreground, '
        'object kind ritual_staff, '
        'environment kind archon_cathedral, '
        'effects dark aura void smoke, '
        'effect signature corruption aura, '
        'energy pattern void sparks, '
        'lore tokens archon corruption ritual'
    ),
    'SOLAR_WARRIOR': (
        'palette gold amber ivory, '
        'motif solar warrior attack spear, '
        'sacred geometry solar disc, '
        'subject solar warrior champion, '
        'object radiant spear, '
        'environment warm temple citadel, '
        'scene type hyperborea_temple_scene, '
        'subject pose attack pose, '
        'secondary object spear, '
        'camera heroic medium close, '
        'mood heroic radiant, '
        'subject kind warrior_foreground, '
        'object kind spear, '
        'environment kind citadel, '
        'effects warm light solar aura, '
        'effect signature spear flare, '
        'energy pattern sun arc, '
        'lore tokens solar warrior attack spear'
    ),
    'GUIDE_MAGE': (
        'palette teal gold pearl, '
        'motif guide mage wisdom chakana, '
        'sacred geometry chakana, '
        'subject guide mage sage, '
        'object orb staff, '
        'environment sacred temple sanctuary, '
        'scene type mountain_guardian_scene, '
        'subject pose ritual pose, '
        'secondary object orb, '
        'camera calm medium close, '
        'mood serene wise, '
        'subject kind oracle_totem, '
        'object kind orb, '
        'environment kind sanctuary, '
        'effects mystic aura soft glow, '
        'effect signature wisdom glyphs, '
        'energy pattern sacred geometry, '
        'lore tokens guide mage wisdom chakana'
    ),
}


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'art' / 'cards' / 'test_scene_composition_v2'
    report_path = root / 'reports' / 'art' / 'scene_test_v2_metrics.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['scene_test_v2_metrics']
    for index, (label, prompt) in enumerate(SCENE_PROMPTS.items(), start=1):
        out_path = out_dir / f'{label.lower()}_scene_comp_v2.png'
        result = generate_scene_art(label.lower(), prompt, 5100 + index * 137, out_path)
        lines.extend(
            [
                f'[{label}]',
                f'path={out_path.as_posix()}',
                f'occ_subject={result["occ_subject"]}',
                f'occ_object={result["occ_object"]}',
                f'contrast_score={result["contrast_score"]}',
                f'readability_ok={result["readability_ok"]}',
                f'focus_balance={result["focus_balance"]}',
                '',
            ]
        )

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    print(f'[scene_test_v2] out={out_dir}')
    print(f'[scene_test_v2] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
