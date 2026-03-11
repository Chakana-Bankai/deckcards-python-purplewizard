from collections import defaultdict
from pathlib import Path
from .common import ROOT, write_text_report, rel


def _group_files(base: Path, patterns: tuple[str, ...]) -> dict[str, list[Path]]:
    buckets: dict[str, list[Path]] = defaultdict(list)
    if not base.exists():
        return {}
    for pattern in patterns:
        for path in base.rglob(pattern):
            if '__pycache__' in path.parts:
                continue
            buckets[path.name].append(path)
    return {k: sorted(v) for k, v in buckets.items() if len(v) > 1}


def collect_duplicates() -> dict[str, dict[str, list[Path]]]:
    return {
        'tools': _group_files(ROOT / 'tools', ('*.py',)),
        'docs': _group_files(ROOT / 'docs', ('*.md', '*.txt')),
        'reports': _group_files(ROOT / 'reports', ('*.md', '*.txt', '*.json')),
        'assets': _group_files(ROOT / 'assets', ('*.png', '*.jpg', '*.jpeg', '*.webp', '*.wav')),
    }


def run(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'duplicate_detector_report.txt'
    dupes = collect_duplicates()
    total = sum(len(v) for v in dupes.values())
    lines = ['mode=duplication_check', f'dry_run={dry_run}', f'duplicate_group_count={total}', '']
    for domain, mapping in dupes.items():
        lines.append(f'[{domain}] count={len(mapping)}')
        for name, paths in sorted(mapping.items()):
            lines.append(f'- {name}: {len(paths)}')
            for p in paths:
                lines.append(f'  - {rel(p)}')
        lines.append('')
    return write_text_report(report, 'chakana_studio duplicate detector', lines)
