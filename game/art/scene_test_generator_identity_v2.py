from __future__ import annotations

import os

import pygame

from game.art.assembly_pipeline import assemble_scene_art
from game.core.paths import project_root

SCENE_PROMPTS = {
    'ARCHON': (
        'palette black crimson toxic green, '
        'motif archon corruption ritual staff, '
        'sacred geometry ritual seal, '
        'subject archon hierophant, '
        'object void ritual staff, '
        'environment void cathedral temple, '
        'scene type archon_void_scene, '
        'subject pose archon_ritual, '
        'secondary object staff, '
        'camera ominous low angle, '
        'mood oppressive malign, '
        'subject kind archon_foreground, '
        'object kind ritual_staff, '
        'environment kind archon_cathedral, '
        'effects dark aura void smoke, '
        'effect signature corruption aura, '
        'energy pattern void sparks, '
        'lore tokens archon corruption ritual staff'
    ),
    'SOLAR_WARRIOR': (
        'palette gold amber ivory, '
        'motif solar warrior attack spear mountain, '
        'sacred geometry solar disc, '
        'subject solar warrior champion, '
        'object radiant spear, '
        'environment warm mountain citadel, '
        'scene type hyperborea_temple_scene, '
        'subject pose solar_warrior_attack, '
        'secondary object spear, '
        'camera heroic medium close, '
        'mood heroic radiant, '
        'subject kind warrior_foreground, '
        'object kind spear, '
        'environment kind citadel, '
        'effects warm light solar aura, '
        'effect signature spear flare, '
        'energy pattern sun arc, '
        'lore tokens solar warrior attack spear mountain solar'
    ),
    'GUIDE_MAGE': (
        'palette teal gold pearl, '
        'motif guide mage wisdom support chakana temple, '
        'sacred geometry chakana, '
        'subject guide mage sage, '
        'object orb staff, '
        'environment sacred temple plateau, '
        'scene type mountain_guardian_scene, '
        'subject pose guide_mage_calm, '
        'secondary object orb, '
        'camera calm medium close, '
        'mood serene wise, '
        'subject kind oracle_totem, '
        'object kind orb, '
        'environment kind sanctuary, '
        'effects mystic aura soft glow, '
        'effect signature wisdom glyphs, '
        'energy pattern sacred geometry, '
        'lore tokens guide mage wisdom support chakana temple'
    ),
}


def _bool_text(value: bool) -> str:
    return 'PASS' if value else 'WARNING'


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'test_identity_v2'
    report_path = root / 'reports' / 'art_pipeline_validation.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        'art_pipeline_validation',
        'canvas=1920x1080',
        'safe_art_zone=0.70',
        'subject_limits=width<=0.35;height<=0.45',
        'weapon_limit=length<=0.60_subject_height',
        'zones=sky:0.30,subject:0.40,ground:0.30',
        '',
    ]

    for index, (label, prompt) in enumerate(SCENE_PROMPTS.items(), start=1):
        out_path = out_dir / f'{label.lower()}_identity_v2.png'
        result = assemble_scene_art(label.lower(), prompt, 16600 + index * 211, out_path)
        metrics = result.metrics
        silhouette_ok = metrics.silhouette_integrity >= 0.75
        weapon_scale_ok = metrics.occ_object <= 0.25 and metrics.weapon_attached_ratio >= 0.85
        subject_readability_ok = metrics.contrast_score >= 0.62 and metrics.subject_visible_ratio >= 0.80 and metrics.white_clip_ratio <= 0.05
        scene_balance_ok = metrics.focus_balance >= 0.75
        overall_ok = silhouette_ok and weapon_scale_ok and subject_readability_ok and scene_balance_ok
        lines.extend([
            f'[{label}]',
            f'path={out_path.as_posix()}',
            f'silhouette_clarity={metrics.silhouette_integrity}',
            f'weapon_scale={metrics.occ_object}',
            f'subject_readability={metrics.contrast_score}',
            f'scene_balance={metrics.focus_balance}',
            f'subject_visibility={metrics.subject_visible_ratio}',
            f'fx_occlusion={metrics.subject_occluded_by_fx_ratio}',
            f'white_clip_ratio={metrics.white_clip_ratio}',
            f'weapon_attached_ratio={metrics.weapon_attached_ratio}',
            f'legacy_readability_ok={metrics.readability_ok}',
            f'silhouette_clarity_status={_bool_text(silhouette_ok)}',
            f'weapon_scale_status={_bool_text(weapon_scale_ok)}',
            f'subject_readability_status={_bool_text(subject_readability_ok)}',
            f'scene_balance_status={_bool_text(scene_balance_ok)}',
            f'overall_status={_bool_text(overall_ok)}',
            '',
        ])

    report_path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    print(f'[identity_v2] out={out_dir}')
    print(f'[identity_v2] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
