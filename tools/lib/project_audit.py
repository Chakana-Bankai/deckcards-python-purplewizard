from .common import ROOT, write_text_report, rel


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'project_audit_cli_report.txt'
    checkpoints = [
        ROOT / 'reports' / 'audit' / 'repository_reality_audit.txt',
        ROOT / 'reports' / 'audit' / 'canonical_structure_plan.txt',
        ROOT / 'reports' / 'audit' / 'manifest_recovery_report.txt',
        ROOT / 'reports' / 'art' / 'art_references_integration_report.txt',
    ]
    lines = ['mode=project_audit', f'dry_run={dry_run}', '', 'checkpoints:']
    for p in checkpoints:
        status = 'OK' if p.exists() else 'MISSING'
        lines.append(f'- {rel(p)} => {status}')
    lines += [
        '',
        'canonical_runtime_roots:',
        f'- {rel(ROOT / "game/data")}',
        f'- {rel(ROOT / "game/assets/sprites/cards")}',
        f'- {rel(ROOT / "assets/art_reference")}',
    ]
    return write_text_report(report, 'chakana_studio project audit', lines)
