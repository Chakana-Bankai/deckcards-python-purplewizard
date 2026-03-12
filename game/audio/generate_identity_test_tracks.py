from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from game.audio.audio_engine import get_audio_engine
from game.audio.audio_stack_tools import analyze_audio_file
from game.core.paths import project_root

console = Console(stderr=True, highlight=False)

TRACK_CONTEXTS = {
    'menu': ('menu', 'a'),
    'combat': ('combat', 'a'),
    'boss': ('combat_boss', 'a'),
}


def main() -> int:
    root = project_root()
    out_dir = root / 'assets' / 'audio' / 'test_identity'
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = get_audio_engine()
    report_lines = ['audio_identity_test_tracks_phase5']

    for label, (ctx, variant) in TRACK_CONTEXTS.items():
        generated = engine._ensure_bgm_variant(ctx, variant, force=True)
        target = out_dir / f'{label}_identity.wav'
        shutil.copy2(generated, target)
        analysis = analyze_audio_file(target)
        report_lines.extend([
            f'[{label}]',
            f'source={generated.as_posix()}',
            f'path={target.as_posix()}',
            f'duration_seconds={analysis.duration_seconds}',
            f'tempo_bpm={analysis.tempo_bpm}',
            f'onset_count={analysis.onset_count}',
            f'variation_score={analysis.variation_score}',
            f'monotony_score={analysis.monotony_score}',
            f'loop_end_seconds={analysis.loop_end_seconds}',
            '',
        ])
        console.print(f'[cyan][Audio Identity][/cyan] exported {label} -> {target.name} tempo={analysis.tempo_bpm} variation={analysis.variation_score}')

    phase5_report = root / 'reports' / 'audio_identity_phase5_tracks.txt'
    phase5_report.parent.mkdir(parents=True, exist_ok=True)
    phase5_report.write_text("\n".join(report_lines).rstrip() + "\n", encoding='utf-8')
    console.print(f'[cyan][Audio Identity][/cyan] report={phase5_report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
