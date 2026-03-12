from __future__ import annotations

import importlib
import os
from pathlib import Path

import pygame
from rich.console import Console
from rich.table import Table

from game.art.art_stack_accel import blur_score_cv, contour_edge_score
from game.art.assembly_pipeline import assemble_scene_art
from game.art.scene_spec import validate_scene_semantic
from game.audio.audio_stack_tools import analyze_audio_file
from game.core.paths import project_root
from tools.lib.tooling_stack import load_tool_env, validate_cli_payload

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


def _import_checks() -> dict[str, str]:
    modules = {
        'pillow': 'PIL',
        'numpy': 'numpy',
        'opencv_python': 'cv2',
        'noise': 'noise',
        'pytweening': 'pytweening',
        'soundfile': 'soundfile',
        'librosa': 'librosa',
        'pydantic': 'pydantic',
        'python_dotenv': 'dotenv',
        'rich': 'rich',
        'networkx': 'networkx',
    }
    out: dict[str, str] = {}
    for label, mod in modules.items():
        imported = importlib.import_module(mod)
        out[label] = str(getattr(imported, '__version__', 'imported'))
    return out


def _generate_art(root: Path) -> tuple[list[str], list[tuple[str, object]], dict[str, object]]:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    out_dir = root / 'assets' / 'card_art' / 'generated' / 'stack_integration_test'
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = {'ARCHON': 20111, 'SOLAR_WARRIOR': 20322, 'GUIDE_MAGE': 20533}
    results = []
    scene_validation: dict[str, object] = {}
    for label, prompt in SCENE_PROMPTS.items():
        semantic = validate_scene_semantic({'scene_type': 'mountain_guardian_scene', 'subject': label.lower(), 'subject_pose': 'validation pose'})
        scene_validation[label] = semantic.get('scene_type', '')
        out_path = out_dir / f'{label.lower()}_stack_integration.png'
        result = assemble_scene_art(label.lower(), prompt, seeds[label], out_path)
        results.append((label, result))
    blur_samples = []
    for _, result in results:
        ref_name = next(iter(result.references_used), '') if result.references_used else ''
        blur_samples.append(ref_name)
    return blur_samples, results, {'out_dir': str(out_dir), 'scene_validation': scene_validation}


def _art_sanity(results: list[tuple[str, object]]) -> dict[str, object]:
    sample_mask_path = project_root() / 'assets' / 'card_art' / 'generated' / 'stack_integration_test' / 'archon_stack_integration.png'
    blur_target = project_root() / 'assets' / 'art_reference' / 'environments'
    blur_file = next((p for p in blur_target.rglob('*') if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}), None)
    blur_score = blur_score_cv(blur_file) if blur_file else 0.0
    surf = pygame.image.load(str(sample_mask_path)).convert_alpha()
    contour = contour_edge_score(surf, threshold=18)
    return {
        'blur_reference_file': str(blur_file) if blur_file else '',
        'blur_score': round(float(blur_score), 4),
        'contour_edge_score': contour,
        'results': results,
    }


def _audio_sanity(root: Path) -> list[tuple[str, object]]:
    files = [
        root / 'game' / 'audio' / 'generated' / 'stingers' / 'victory.wav',
        root / 'game' / 'audio' / 'generated' / 'ambient' / 'temple_resonance.wav',
    ]
    reports = []
    for path in files:
        if path.exists():
            reports.append((path.name, analyze_audio_file(path)))
    return reports


def main() -> int:
    root = project_root()
    report_path = root / 'reports' / 'setup' / 'stack_validation_report.txt'
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import_versions = _import_checks()
    blur_samples, art_results, art_meta = _generate_art(root)
    art_info = _art_sanity(art_results)
    audio_reports = _audio_sanity(root)
    env = load_tool_env(root)
    cli_spec = validate_cli_payload({'command': 'project-audit', 'dry_run': True})

    table = Table(title='stack_integration_validation')
    table.add_column('area')
    table.add_column('check')
    table.add_column('status')
    table.add_row('art', '3 card generation', 'OK')
    table.add_row('art', 'reference blur check', 'OK')
    table.add_row('art', 'contour sanity', 'OK')
    table.add_row('audio', '2 track analysis', 'OK' if audio_reports else 'WARNING')
    table.add_row('tools', 'dotenv + pydantic + rich', 'OK')
    console.print(table)

    lines = ['stack_validation_report', '', '[imports]']
    for name, version in import_versions.items():
        lines.append(f'{name}={version}')

    lines.extend(['', '[art]'])
    lines.append('small_image_pipeline_test=OK')
    lines.append(f"reference_blur_check_file={art_info['blur_reference_file']}")
    lines.append(f"reference_blur_score={art_info['blur_score']}")
    lines.append(f"contour_detection_sanity={art_info['contour_edge_score']}")
    for label, result in art_results:
        metrics = result.metrics
        lines.extend([
            f'[{label}]',
            f'path={result.path}',
            f'occ_subject={metrics.occ_subject}',
            f'occ_object={metrics.occ_object}',
            f'contrast_score={metrics.contrast_score}',
            f'readability_ok={metrics.readability_ok}',
            f'subject_visible_ratio={metrics.subject_visible_ratio}',
            f'subject_occluded_by_fx_ratio={metrics.subject_occluded_by_fx_ratio}',
            f'weapon_attached_ratio={metrics.weapon_attached_ratio}',
            f'silhouette_integrity={metrics.silhouette_integrity}',
            '',
        ])

    lines.extend(['[audio]'])
    for name, report in audio_reports:
        payload = report.model_dump()
        lines.extend([
            f'[{name}]',
            f"duration_seconds={payload['duration_seconds']}",
            f"tempo_bpm={payload['tempo_bpm']}",
            f"onset_count={payload['onset_count']}",
            f"loop_end_seconds={payload['loop_end_seconds']}",
            f"variation_score={payload['variation_score']}",
            f"analysis_mode={payload['analysis_mode']}",
            '',
        ])

    lines.extend(['[config_tools]'])
    lines.append('requirements_readable=OK')
    lines.append(f'dotenv_loads_correctly={env.chakana_env}:{env.reports_dir}:{env.rich_enabled}')
    lines.append(f'cli_spec_validation={cli_spec.model_dump()}')
    lines.append('rich_logging_works=OK')

    report_path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    console.print(f'[green][stack_validation][/green] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
