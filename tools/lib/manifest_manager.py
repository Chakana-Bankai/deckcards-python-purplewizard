import json
from pathlib import Path
from .common import ROOT, write_text_report, rel


def _status(path: Path) -> str:
    if not path.exists():
        return 'MISSING'
    try:
        json.loads(path.read_text(encoding='utf-8'))
        return 'OK'
    except Exception:
        return 'BROKEN'


def _all_manifests() -> list[Path]:
    preferred = [
        ROOT / 'game/data/art_manifest.json',
        ROOT / 'game/data/audio_manifest.json',
        ROOT / 'game/data/art_manifest_avatar.json',
        ROOT / 'game/data/art_manifest_enemies.json',
        ROOT / 'game/data/art_manifest_guides.json',
        ROOT / 'game/data/biome_manifest.json',
        ROOT / 'data/manifests/art_manifest.json',
        ROOT / 'data/manifests/audio_manifest.json',
        ROOT / 'data/manifests/card_manifest.json',
        ROOT / 'data/manifests/codex_manifest.json',
        ROOT / 'data/manifests/art_reference_manifest.json',
    ]
    return preferred


def audit_manifest_status() -> dict[str, object]:
    manifests = _all_manifests()
    statuses = {rel(p): _status(p) for p in manifests}
    duplicate_names: dict[str, list[Path]] = {}
    for p in ROOT.rglob('*manifest*.json'):
        if '.git' in p.parts:
            continue
        duplicate_names.setdefault(p.name, []).append(p)
    dupes = {k: sorted(v) for k, v in duplicate_names.items() if len(v) > 1}
    broken = [k for k, v in statuses.items() if v != 'OK']
    return {
        'statuses': statuses,
        'duplicates': dupes,
        'broken': broken,
    }


def run_audit(*, dry_run: bool = False):
    report = ROOT / 'reports' / 'tools' / 'manifest_audit_report.txt'
    audit = audit_manifest_status()
    statuses = audit['statuses']
    dupes = audit['duplicates']
    lines = ['mode=manifest_audit', f'dry_run={dry_run}', '']
    for key, status in statuses.items():
        lines.append(f'- {key} => {status}')
    lines += ['', f'duplicate_manifest_name_count={len(dupes)}', 'duplicate_manifest_names:']
    for name, paths in sorted(dupes.items()):
        lines.append(f'- {name}: {len(paths)}')
        for p in paths:
            lines.append(f'  - {rel(p)}')
    return write_text_report(report, 'chakana_studio manifest audit', lines)
