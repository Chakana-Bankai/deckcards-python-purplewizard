from .common import ROOT, write_text_report
from .core_validation import run_suite


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'qa' / 'cli_smoke_report.txt'
    lines = ['mode=qa_smoke', f'dry_run={dry_run}', '']
    if dry_run:
        lines.extend(
            [
                '- suite=canonical_core_validation',
                '- checks=doctor,card-coherence,combat-content-lock,deck-system,beta-run-flow',
                '',
                'overall=DRY_RUN',
            ]
        )
        return write_text_report(report, 'chakana_studio qa smoke', lines)

    overall = 'PASS'
    for result in run_suite():
        if int(result['returncode']) != 0:
            overall = 'WARNING'
        lines.append(
            f"- check={result['label']} cmd={result['command']!r} "
            f"rc={result['returncode']} status={result['status']} last={result['last']}"
        )
    lines += ['', f'overall={overall}']
    return write_text_report(report, 'chakana_studio qa smoke', lines)
