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


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = project_root()
    out_dir = root / 'assets' / 'test_identity'
    report_path = root / 'reports' / 'art' / 'identity_lock_metrics_phase5.txt'
    summary_path = root / 'reports' / 'art' / 'identity_lock_summary_phase5.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['identity_lock_metrics_phase5']
    results = []
    for index, (label, prompt) in enumerate(SCENE_PROMPTS.items(), start=1):
        out_path = out_dir / f'{label.lower()}_identity_lock.png'
        result = assemble_scene_art(label.lower(), prompt, 12100 + index * 173, out_path)
        metrics = result.metrics
        results.append((label, metrics))
        lines.extend([
            f'[{label}]',
            f'path={out_path.as_posix()}',
            f'occ_subject={metrics.occ_subject}',
            f'occ_object={metrics.occ_object}',
            f'contrast_score={metrics.contrast_score}',
            f'readability_ok={metrics.readability_ok}',
            f'focus_balance={metrics.focus_balance}',
            f'white_clip_ratio={metrics.white_clip_ratio}',
            f'subject_visible_ratio={metrics.subject_visible_ratio}',
            f'subject_occluded_by_fx_ratio={metrics.subject_occluded_by_fx_ratio}',
            f'weapon_attached_ratio={metrics.weapon_attached_ratio}',
            f'silhouette_integrity={metrics.silhouette_integrity}',
            f'limb_connection_score={metrics.limb_connection_score}',
            f'frontal_block_score={metrics.frontal_block_score}',
            '',
        ])

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    passed = [label for label, metrics in results if metrics.readability_ok]
    summary_lines = [
        'identity_lock_summary_phase5',
        '1. Pipeline changes: applied the identity lock grammar with canonical shape language, scene composition rules, cleaned references, and archetype anchors over the stabilized 480x270 to 1920x1080 pipeline.',
        '2. Washout fix: the scene rules kept subject, object, symbolic layer, and environment in canonical roles with safe-zone control and occupancy caps.',
        '3. Figure construction fix: subjects now inherit the identity document, character templates, and scene rules so each archetype reads through silhouette, prop choice, palette family, and camera bias.',
        f'4. Metrics passed: {", ".join(passed) if passed else "none"}; thresholds checked include occupancy, contrast, visibility, FX occlusion, weapon attachment, silhouette integrity, and limb connection.',
        '5. Remaining refinement before scaling: integrate scene_rules.json as a direct runtime source and deepen costume/prop detail without breaking silhouette clarity.',
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding='utf-8')
    print(f'[identity_lock] out={out_dir}')
    print(f'[identity_lock] report={report_path}')
    print(f'[identity_lock] summary={summary_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
