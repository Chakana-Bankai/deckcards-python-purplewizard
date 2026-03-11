from .common import ROOT, write_text_report, rel


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'engine' / 'cli_engine_audit_report.txt'
    engine_candidate = [
        ROOT / 'game/art',
        ROOT / 'game/audio',
        ROOT / 'game/visual',
        ROOT / 'game/core',
    ]
    game_specific = [
        ROOT / 'game/data',
        ROOT / 'docs/canon',
        ROOT / 'assets/art_reference',
    ]
    lines = ['mode=engine_audit', f'dry_run={dry_run}', '', 'engine_candidate:']
    for p in engine_candidate:
        lines.append(f'- {rel(p)}')
    lines += ['', 'game_specific:']
    for p in game_specific:
        lines.append(f'- {rel(p)}')
    return write_text_report(report, 'chakana_studio engine audit', lines)
