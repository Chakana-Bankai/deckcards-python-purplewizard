from __future__ import annotations

import os

import pygame
from rich.console import Console
from rich.table import Table

from game.art.assembly_pipeline import assemble_scene_art
from game.core.paths import project_root

console = Console(highlight=False)

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
    out_dir = root / 'assets' / 'art' / 'cards' / 'test_shape_grammar_v1'
    report_path = root / 'reports' / 'art' / 'test_shape_grammar_v1_metrics.txt'
    summary_path = root / 'reports' / 'art' / 'test_shape_grammar_v1_summary.txt'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['test_shape_grammar_v1_metrics']
    results = []
    table = Table(title='shape_grammar_v1')
    table.add_column('card')
    table.add_column('occ_subject')
    table.add_column('occ_object')
    table.add_column('contrast')
    table.add_column('readability')
    for index, (label, prompt) in enumerate(SCENE_PROMPTS.items(), start=1):
        out_path = out_dir / f'{label.lower()}_shape_grammar_v1.png'
        result = assemble_scene_art(label.lower(), prompt, 16100 + index * 211, out_path)
        metrics = result.metrics
        results.append((label, result))
        table.add_row(label, str(metrics.occ_subject), str(metrics.occ_object), str(metrics.contrast_score), str(metrics.readability_ok))
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
            f'grammar_match_score={metrics.grammar_match_score}',
            '',
        ])

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    summary_lines = ['test_shape_grammar_v1_summary']
    for label, result in results:
        metrics = result.metrics
        grammar = 'HUMANOID/' + ('ARCHON' if label == 'ARCHON' else 'SOLAR_WARRIOR' if label == 'SOLAR_WARRIOR' else 'GUIDE_MAGE')
        ready = 'yes' if metrics.readability_ok and metrics.grammar_match_score >= 0.80 else 'not yet'
        summary_lines.extend([
            f'[{label}]',
            f'1. grammar applied: {grammar}',
            f'2. scale control: composed at 480x270 with subject and object stabilized through grammar ratios and upscaled to 1920x1080 only at export.',
            f'3. proportion correction: head/torso/pelvis/legs/shoulders were constrained through humanoid grammar ratios and pose anchors.',
            f'4. silhouette readability improved: {metrics.silhouette_integrity >= 0.75 and metrics.grammar_match_score >= 0.80}',
            f'5. ready for template extraction: {ready}',
            '',
        ])
    summary_path.write_text("\n".join(summary_lines).rstrip() + "\n", encoding='utf-8')
    console.print(table)
    console.print(f'[green][test_shape_grammar_v1][/green] out={out_dir}')
    console.print(f'[green][test_shape_grammar_v1][/green] report={report_path}')
    console.print(f'[green][test_shape_grammar_v1][/green] summary={summary_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
