from .common import ROOT, write_text_report


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'master' / 'chakana_reports_build.txt'
    buckets = ['audit', 'art', 'qa', 'tools', 'engine', 'validation']
    lines = ['mode=reports_build', f'dry_run={dry_run}', '']
    for bucket in buckets:
        folder = ROOT / 'reports' / bucket
        count = sum(1 for item in folder.rglob('*') if item.is_file()) if folder.exists() else 0
        lines.append(f'- {bucket}: {count}')
    return write_text_report(report, 'chakana_studio reports build', lines)
