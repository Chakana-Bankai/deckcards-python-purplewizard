from pathlib import Path
from .common import ROOT, write_text_report, rel
from .duplicate_detector import collect_duplicates
from .manifest_manager import audit_manifest_status


def _root_clutter_candidates() -> list[Path]:
    keep = {
        'AGENTS.md', 'README.md', 'run.ps1', 'requirements.txt', 'pyproject.toml',
        'pytest.ini', '.gitignore', '.gitattributes', '.gitkeep', '.regen_flag',
        'savegame.json', 'temp_run_capture.log', 'reset_generated.ps1'
    }
    out: list[Path] = []
    for p in ROOT.iterdir():
        if p.is_file() and p.name not in keep and p.suffix.lower() in {'.txt', '.md', '.log'}:
            out.append(p)
    return sorted(out)


def _report_folders() -> dict[str, int]:
    buckets = {}
    for name in ['audit', 'audits', 'art', 'cleanup', 'engine', 'master', 'qa', 'tools', 'validation']:
        folder = ROOT / 'reports' / name
        buckets[name] = sum(1 for item in folder.rglob('*') if item.is_file()) if folder.exists() else 0
    return buckets


def _wrong_location_candidates() -> list[str]:
    candidates: list[str] = []
    if (ROOT / 'game' / 'assets' / 'tmp').exists():
        candidates.append('game/assets/tmp')
    if (ROOT / 'assets' / 'archive').exists():
        candidates.append('assets/archive (legacy, prefer assets/_archive)')
    if (ROOT / 'reports' / 'audits').exists():
        candidates.append('reports/audits (legacy overlap, prefer reports/audit)')
    if not (ROOT / 'assets' / 'art_reference').exists():
        candidates.append('assets/art_reference missing')
    if (ROOT / 'assets' / 'art_references').exists():
        candidates.append('assets/art_references (unexpected duplicate of assets/art_reference)')
    return candidates


def _stale_report_candidates() -> list[str]:
    candidates: list[str] = []
    for folder_name in ['audit', 'audits', 'tools', 'validation']:
        folder = ROOT / 'reports' / folder_name
        if not folder.exists():
            continue
        for path in folder.glob('*.txt'):
            if '__pass' in path.name or path.name.startswith('temp_'):
                candidates.append(rel(path))
    return sorted(candidates)


def _wrong_manifest_locations() -> list[str]:
    out: list[str] = []
    allowed_prefixes = (
        ROOT / 'game' / 'data',
        ROOT / 'game' / 'visual',
        ROOT / 'game' / 'audio',
        ROOT / 'data' / 'manifests',
    )
    for path in ROOT.rglob('*manifest*.json'):
        if '.git' in path.parts:
            continue
        if not any(str(path).startswith(str(prefix)) for prefix in allowed_prefixes):
            out.append(rel(path))
    return sorted(out)


def run(*, dry_run: bool = True):
    report = ROOT / 'reports' / 'cleanup' / 'project_sanitization_report.txt'
    root_clutter = _root_clutter_candidates()
    dupes = collect_duplicates()
    manifest_audit = audit_manifest_status()
    report_counts = _report_folders()
    wrong = _wrong_location_candidates()
    stale_reports = _stale_report_candidates()
    wrong_manifest_locations = _wrong_manifest_locations()
    total_dupe_groups = sum(len(v) for v in dupes.values())
    lines: list[str] = [
        'mode=project_sanitizer',
        f'dry_run={dry_run}',
        '',
        f'root_clutter_count={len(root_clutter)}',
        'root_clutter_candidates:',
    ]
    for p in root_clutter:
        lines.append(f'- {rel(p)}')
    lines += ['', f'duplicate_group_count={total_dupe_groups}', 'duplicate_groups:']
    for domain, mapping in dupes.items():
        lines.append(f'- [{domain}] {len(mapping)}')
        for name, paths in sorted(mapping.items()):
            lines.append(f'  - {name}: {len(paths)}')
            for p in paths:
                lines.append(f'    - {rel(p)}')
    lines += ['', 'report_bucket_counts:']
    for name, count in sorted(report_counts.items()):
        lines.append(f'- {name}: {count}')
    lines += ['', f'manifest_problem_count={len(manifest_audit["broken"])}', 'manifest_problems:']
    for item in manifest_audit['broken']:
        lines.append(f'- {item}')
    lines += ['', f'wrong_manifest_location_count={len(wrong_manifest_locations)}', 'wrong_manifest_locations:']
    for item in wrong_manifest_locations:
        lines.append(f'- {item}')
    lines += ['', f'stale_report_candidate_count={len(stale_reports)}', 'stale_report_candidates:']
    for item in stale_reports:
        lines.append(f'- {item}')
    lines += ['', f'wrong_location_candidate_count={len(wrong)}', 'wrong_location_candidates:']
    for item in wrong:
        lines.append(f'- {item}')
    lines += [
        '',
        'sanitization_policy:',
        '- report-first; no destructive move/delete in phase 7',
        '- prefer archive or wrapper over removal',
        '- prefer chakana_studio.py over direct root wrappers',
        '- prefer reports/audit over reports/audits for new audits',
        '- prefer data/manifests as canonical mirror layer while runtime still consumes game/data and game/visual',
    ]
    return write_text_report(report, 'chakana_studio project sanitization', lines)
