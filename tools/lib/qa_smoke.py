import subprocess
import sys
from .common import ROOT, write_text_report


def _run_cmd(args):
    proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or '').strip().splitlines()
    err = (proc.stderr or '').strip().splitlines()
    last = out[-1] if out else (err[-1] if err else '')
    return proc.returncode, last


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'qa' / 'cli_smoke_report.txt'
    checks = [
        [sys.executable, '-m', 'tools.doctor'],
        [sys.executable, '-m', 'tools.qa.check_beta_run_flow'],
    ]
    lines = ['mode=qa_smoke', f'dry_run={dry_run}', '']
    overall = 'PASS'
    for cmd in checks:
        rc, last = _run_cmd(cmd)
        if rc != 0:
            overall = 'WARNING'
        lines.append(f'- cmd={cmd!r} rc={rc} last={last}')
    lines += ['', f'overall={overall}']
    return write_text_report(report, 'chakana_studio qa smoke', lines)
