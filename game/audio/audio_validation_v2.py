from __future__ import annotations

from game.audio.audio_stack_tools import analyze_audio_file
from game.core.paths import project_root


def main() -> int:
    root = project_root()
    base = root / 'assets' / 'audio' / 'mvp_v2'
    report = root / 'reports' / 'audio' / 'audio_validation_v2_report.txt'
    lines = ['audio_validation_v2_report']
    for path in sorted(base.glob('*.wav')):
        analysis = analyze_audio_file(path)
        distinctiveness = round(max(0.0, min(1.0, analysis.variation_score * (1.0 - min(1.0, analysis.monotony_score * 0.5)))), 4)
        lines.extend([
            f'[{path.stem}]',
            f'note_variation={analysis.variation_score}',
            f'dynamic_range_proxy_db={round(analysis.peak_db - analysis.rms_db, 4)}',
            f'loop_smoothness={round(1.0 - min(1.0, analysis.monotony_score * 0.35), 4)}',
            f'tempo_consistency_bpm={analysis.tempo_bpm}',
            f'stinger_distinctiveness={distinctiveness}',
            '',
        ])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
