from __future__ import annotations

from pathlib import Path

from rich.console import Console

from game.audio.loop_tail_refiner import refine_runtime_loop
from game.core.paths import project_root

console = Console(stderr=True, highlight=False)

TRACKS = ['menu', 'combat', 'boss']


def main() -> int:
    root = project_root()
    source_dir = root / 'assets' / 'audio' / 'test_identity'
    out_dir = source_dir / 'runtime_loops'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = root / 'reports' / 'audio_identity_runtime_loops.txt'

    lines = ['audio_identity_runtime_loops']
    for name in TRACKS:
        source = source_dir / f'{name}_identity.wav'
        target = out_dir / f'{name}_identity_runtime_loop.wav'
        refined = refine_runtime_loop(source, target)
        lines.extend([
            f'[{name}]',
            f'source_path={refined.source_path}',
            f'target_path={refined.target_path}',
            f'duration_seconds={refined.duration_seconds}',
            f'refined_duration_seconds={refined.refined_duration_seconds}',
            f'trim_seconds={refined.trim_seconds}',
            f'tempo_bpm={refined.tempo_bpm}',
            f'variation_score={refined.variation_score}',
            f'fade_seconds={refined.fade_seconds}',
            f'loop_smoothness_before={refined.loop_smoothness_before}',
            f'loop_smoothness_after={refined.loop_smoothness_after}',
            '',
        ])
        console.print(f'[cyan][Loop Refiner][/cyan] {name} -> {target.name} trim={refined.trim_seconds}s refined={refined.refined_duration_seconds}s')

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding='utf-8')
    console.print(f'[cyan][Loop Refiner][/cyan] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
