from __future__ import annotations

from rich.console import Console

from game.audio.audio_depth_specs import load_audio_depth_specs
from game.audio.audio_stack_tools import analyze_audio_file, write_wav_soundfile
from game.audio.layered_theme_builder import SAMPLE_RATE, build_layered_theme
from game.audio.stinger_composer_v2 import compose_stinger
from game.core.paths import project_root

console = Console(stderr=True, highlight=False)

THEME_CONTEXTS = ['studio_intro', 'main_menu', 'combat_normal', 'combat_boss', 'victory', 'pack_open', 'rare_reveal', 'legendary_reveal']
STINGER_EVENTS = ['ui_confirm', 'ui_cancel', 'draw_card', 'play_card']


def main() -> int:
    root = project_root()
    out_dir = root / 'assets' / 'audio' / 'mvp_v2'
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = load_audio_depth_specs()
    lines = ['audio_mvp_v2_report']

    for context in THEME_CONTEXTS:
        result = build_layered_theme(context, seconds=float(specs[context]['loop_length_seconds']))
        path = out_dir / f'{context}.wav'
        write_wav_soundfile(path, result.samples, SAMPLE_RATE, channels=1, subtype='PCM_16')
        analysis = analyze_audio_file(path)
        lines.extend([
            f'[{context}]',
            'kind=theme',
            f'path={path.as_posix()}',
            f'tempo_bpm={analysis.tempo_bpm}',
            f'variation_score={analysis.variation_score}',
            f'monotony_score={analysis.monotony_score}',
            f'loop_end_seconds={analysis.loop_end_seconds}',
            f'layer_presence={result.layer_presence}',
            '',
        ])
        console.print(f'[cyan][Audio MVP v2][/cyan] theme {context} -> {path.name} tempo={analysis.tempo_bpm} variation={analysis.variation_score}')

    for name in STINGER_EVENTS:
        result = compose_stinger(name)
        path = out_dir / f'{name}.wav'
        write_wav_soundfile(path, result.samples, SAMPLE_RATE, channels=1, subtype='PCM_16')
        analysis = analyze_audio_file(path)
        lines.extend([
            f'[{name}]',
            'kind=stinger',
            f'path={path.as_posix()}',
            f'tempo_bpm={analysis.tempo_bpm}',
            f'variation_score={analysis.variation_score}',
            f'monotony_score={analysis.monotony_score}',
            '',
        ])
        console.print(f'[cyan][Audio MVP v2][/cyan] stinger {name} -> {path.name} variation={analysis.variation_score}')

    report = root / 'reports' / 'audio' / 'audio_mvp_v2_report.txt'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    console.print(f'[cyan][Audio MVP v2][/cyan] report={report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
