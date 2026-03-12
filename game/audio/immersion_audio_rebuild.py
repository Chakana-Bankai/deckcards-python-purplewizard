from __future__ import annotations

import json
import shutil
from pathlib import Path

from rich.console import Console

from game.audio.audio_stack_tools import analyze_audio_file, write_wav_soundfile
from game.audio.event_sfx_builder import SAMPLE_RATE, compose_event_sfx
from game.audio.layered_theme_builder import build_layered_theme
from game.audio.stinger_composer_v2 import compose_stinger
from game.core.paths import project_root

console = Console(stderr=True, highlight=False)

THEME_EXPORTS = {
    'studio_intro': ('studio', 'studio_intro.wav'),
    'main_menu': ('bgm', 'menu_a.wav'),
    'map_exploration': ('bgm', 'map_kay_a.wav'),
    'combat_normal': ('bgm', 'combat_a.wav'),
    'combat_elite': ('bgm', 'combat_elite_a.wav'),
    'combat_boss': ('bgm', 'combat_boss_a.wav'),
    'shop': ('bgm', 'shop_a.wav'),
    'reward': ('bgm', 'reward_a.wav'),
    'victory': ('bgm', 'victory_a.wav'),
    'defeat': ('bgm', 'defeat_a.wav'),
    'codex': ('bgm', 'codex_a.wav'),
    'credits': ('bgm', 'credits_a.wav'),
}

MAP_VARIANTS = ('map_kay_a.wav', 'map_ukhu_a.wav', 'map_hanan_a.wav')
STINGER_EXPORTS = ('pack_open', 'rare_reveal', 'legendary_reveal', 'reward', 'victory', 'defeat', 'ritual_trigger', 'boss_warning', 'studio_intro')
SFX_EXPORTS = (
    'hover', 'select', 'confirm', 'cancel', 'invalid', 'draw_card', 'play_card',
    'attack_light', 'attack_heavy', 'block', 'heal', 'ritual', 'combo_trigger', 'harmony_gain', 'boss_phase',
)


def _archive_existing(path: Path, archive_root: Path) -> str:
    if not path.exists():
        return 'missing'
    rel = path.relative_to(project_root())
    target = archive_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return str(target)


def _manifest_entry(item_id: str, item_type: str, context: str, file_path: Path, analysis: dict) -> dict:
    root = project_root().resolve()
    rel = file_path.resolve().relative_to(root)
    return {
        'track_id': item_id,
        'type': item_type,
        'context': context,
        'variant': 'a',
        'seed': abs(hash((item_id, 'immersion_audio_phase3'))) % (2**31 - 1),
        'file_path': str(file_path.resolve()),
        'relative_path': str(rel).replace('\\', '/'),
        'generation_date': 1773350000,
        'version': 'chakana_audio_depth_v2',
        'state': 'valid',
        'source': 'generated',
        'active_runtime': True,
        'analysis': analysis,
    }


def main() -> int:
    root = project_root()
    generated_root = root / 'game' / 'audio' / 'generated'
    mvp_root = root / 'assets' / 'audio' / 'mvp_v2'
    archive_root = root / 'assets' / 'production' / 'audio' / 'archive' / 'immersion_rebuild_phase3'
    manifest_path = root / 'game' / 'data' / 'audio_manifest.json'
    legacy_manifest_path = root / 'game' / 'audio' / 'audio_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    items = manifest.setdefault('items', {})
    report_lines = ['immersion_audio_rebuild_report', '']

    for context, (folder, filename) in THEME_EXPORTS.items():
        result = build_layered_theme(context)
        out_path = generated_root / folder / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        archived = _archive_existing(out_path, archive_root)
        write_wav_soundfile(out_path, result.samples, SAMPLE_RATE, channels=1, subtype='PCM_16')
        shutil.copy2(out_path, mvp_root / f'{context}.wav')
        analysis = analyze_audio_file(out_path).model_dump()
        item_id = out_path.stem
        runtime_context = {
            'main_menu': 'menu',
            'map_exploration': 'map_kay',
            'combat_normal': 'combat',
        }.get(context, context)
        items[item_id] = _manifest_entry(item_id, 'bgm', runtime_context, out_path, analysis)
        report_lines.extend([
            f'[theme:{context}]',
            f'runtime_path={out_path.as_posix()}',
            f'archived_previous={archived}',
            f'variation_score={analysis["variation_score"]}',
            f'tempo_bpm={analysis["tempo_bpm"]}',
            '',
        ])

    map_source = generated_root / 'bgm' / 'map_kay_a.wav'
    for filename in MAP_VARIANTS[1:]:
        out_path = generated_root / 'bgm' / filename
        archived = _archive_existing(out_path, archive_root)
        shutil.copy2(map_source, out_path)
        analysis = analyze_audio_file(out_path).model_dump()
        context = filename.replace('_a.wav', '')
        items[out_path.stem] = _manifest_entry(out_path.stem, 'bgm', context, out_path, analysis)
        report_lines.extend([
            f'[theme:{context}]',
            f'runtime_path={out_path.as_posix()}',
            f'archived_previous={archived}',
            'source=map_exploration_clone',
            '',
        ])

    for name in STINGER_EXPORTS:
        result = compose_stinger(name)
        folder = 'studio' if name == 'studio_intro' else 'stingers'
        out_path = generated_root / folder / f'{name}.wav'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        archived = _archive_existing(out_path, archive_root)
        write_wav_soundfile(out_path, result.samples, SAMPLE_RATE, channels=1, subtype='PCM_16')
        shutil.copy2(out_path, mvp_root / f'{name}.wav')
        analysis = analyze_audio_file(out_path).model_dump()
        items[f'stinger_{name}'] = _manifest_entry(f'stinger_{name}', 'stinger', name, out_path, analysis)
        report_lines.extend([
            f'[stinger:{name}]',
            f'runtime_path={out_path.as_posix()}',
            f'archived_previous={archived}',
            f'variation_score={analysis["variation_score"]}',
            '',
        ])

    for name in SFX_EXPORTS:
        out_path = generated_root / 'sfx' / f'{name}.wav'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        archived = _archive_existing(out_path, archive_root)
        samples = compose_event_sfx(name)
        write_wav_soundfile(out_path, samples, SAMPLE_RATE, channels=1, subtype='PCM_16')
        shutil.copy2(out_path, mvp_root / f'{name}.wav')
        analysis = analyze_audio_file(out_path).model_dump()
        items[f'sfx_{name}'] = _manifest_entry(f'sfx_{name}', 'sfx', name, out_path, analysis)
        report_lines.extend([
            f'[sfx:{name}]',
            f'runtime_path={out_path.as_posix()}',
            f'archived_previous={archived}',
            f'variation_score={analysis["variation_score"]}',
            '',
        ])

    manifest['version'] = 'chakana_audio_depth_v2'
    manifest['generated_at'] = 1773350000

    for item_id, meta in list(items.items()):
        if not isinstance(meta, dict):
            continue
        if meta.get('type') == 'bgm' and item_id.endswith(('_b', '_c')):
            meta['active_runtime'] = False
            meta['state'] = 'archived_legacy'
        if meta.get('type') == 'stinger' and item_id in {'stinger_relic_gain', 'stinger_level_up', 'stinger_seal_ready', 'stinger_harmony_ready'}:
            meta['active_runtime'] = False
            meta['state'] = 'legacy_optional'

    payload = json.dumps(manifest, indent=2, ensure_ascii=False)
    manifest_path.write_text(payload, encoding='utf-8')
    legacy_manifest_path.write_text(payload, encoding='utf-8')

    report_lines.extend([
        '[summary]',
        f'themes_promoted={len(THEME_EXPORTS) + 2}',
        f'stingers_promoted={len(STINGER_EXPORTS)}',
        f'sfx_promoted={len(SFX_EXPORTS)}',
        f'archive_root={archive_root.as_posix()}',
        'runtime_manifest_updated=game/data/audio_manifest.json',
        'stale_assets_no_longer_preferred=True',
    ])
    report = root / 'reports' / 'audio' / 'immersion_audio_rebuild_report.txt'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(report_lines).rstrip() + '\n', encoding='utf-8')
    console.print(f'[cyan][Immersion Audio][/cyan] report={report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
