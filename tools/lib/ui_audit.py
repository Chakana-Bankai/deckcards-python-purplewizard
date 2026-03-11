from .common import ROOT, write_text_report, rel


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'ui_audit_report.txt'
    screens = sorted((ROOT / 'game' / 'ui' / 'screens').glob('*.py'))
    lines = [
        'mode=ui_audit',
        f'dry_run={dry_run}',
        'checks=text_clipping,overlap,bad_spacing,wrong_hierarchy,inconsistent_sizing,stretched_images,unreadable_labels',
        '',
        'screen_files:',
    ]
    for p in screens:
        lines.append(f'- {rel(p)}')
    lines += ['', 'note=static audit scaffold only; no runtime pixel diff in phase 5']
    return write_text_report(report, 'chakana_studio ui audit', lines)
