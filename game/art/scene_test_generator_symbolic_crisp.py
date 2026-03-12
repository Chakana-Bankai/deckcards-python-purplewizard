from __future__ import annotations

import os

import pygame

from game.art.assembly_pipeline import assemble_scene_art
from game.core.paths import project_root

SCENE_PROMPTS = {
    'ARCHON': (
        'palette black crimson toxic green, motif archon corruption ritual staff, sacred geometry ritual seal, '
        'subject archon hierophant, object void ritual staff, environment void cathedral temple, scene type archon_void_scene, '
        'subject pose archon_ritual, secondary object staff, camera ominous low angle, mood oppressive malign, '
        'subject kind archon_foreground, object kind ritual_staff, environment kind archon_cathedral, '
        'effects dark aura void smoke, effect signature corruption aura, energy pattern void sparks, lore tokens archon corruption ritual staff'
    ),
    'SOLAR_WARRIOR': (
        'palette gold amber ivory, motif solar warrior attack spear mountain, sacred geometry solar disc, '
        'subject solar warrior champion, object radiant spear, environment warm mountain citadel, scene type hyperborea_temple_scene, '
        'subject pose solar_warrior_attack, secondary object spear, camera heroic medium close, mood heroic radiant, '
        'subject kind warrior_foreground, object kind spear, environment kind citadel, effects warm light solar aura, '
        'effect signature spear flare, energy pattern sun arc, lore tokens solar warrior attack spear mountain solar'
    ),
    'GUIDE_MAGE': (
        'palette teal gold pearl, motif guide mage wisdom support chakana temple, sacred geometry chakana, '
        'subject guide mage sage, object orb staff, environment sacred temple plateau, scene type mountain_guardian_scene, '
        'subject pose guide_mage_calm, secondary object orb, camera calm medium close, mood serene wise, '
        'subject kind oracle_totem, object kind orb, environment kind sanctuary, effects mystic aura soft glow, '
        'effect signature wisdom glyphs, energy pattern sacred geometry, lore tokens guide mage wisdom support chakana temple'
    ),
}


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'test_identity_crisp'
    report_path = root / 'reports' / 'art' / 'symbolic_crisp_examples.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['symbolic_crisp_examples', 'style_target=playable_placeholder_with_identity', '']
    for index, (label, prompt) in enumerate(SCENE_PROMPTS.items(), start=1):
        out_path = out_dir / f'{label.lower()}_crisp.png'
        result = assemble_scene_art(label.lower(), prompt, 19100 + index * 101, out_path)
        m = result.metrics
        lines.extend([
            f'[{label}]',
            f'path={out_path.as_posix()}',
            f'silhouette_clarity={m.silhouette_integrity}',
            f'weapon_visibility={m.occ_object}',
            f'contrast={m.contrast_score}',
            f'focus_balance={m.focus_balance}',
            f'readability_ok={m.readability_ok}',
            '',
        ])
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    print(f'[symbolic_crisp] out={out_dir}')
    print(f'[symbolic_crisp] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
