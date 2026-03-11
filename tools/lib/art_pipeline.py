import json
import subprocess
import sys
from pathlib import Path

from .common import ROOT, write_text_report

CARD_MANIFEST = ROOT / 'data' / 'manifests' / 'card_manifest.json'
ART_MANIFEST = ROOT / 'data' / 'manifests' / 'art_manifest.json'
CARD_DIR = ROOT / 'game' / 'assets' / 'sprites' / 'cards'
REPORT_DIR = ROOT / 'reports' / 'art'
STAGING_DIR = ROOT / 'assets' / 'staging' / 'cards'
PRODUCTION_DIR = ROOT / 'assets' / 'production' / 'cards'


def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _card_entries():
    data = _load_json(CARD_MANIFEST)
    return list(data.get('cards') or [])


def _card_ids():
    return [str(row.get('id')) for row in _card_entries() if row.get('id')]


def _card_png_path(card_id: str) -> Path:
    return CARD_DIR / f'{card_id}.png'


def _missing_card_ids():
    return [cid for cid in _card_ids() if not _card_png_path(cid).exists()]


def _duplicate_card_assets():
    groups = {}
    for png in CARD_DIR.glob('*.png'):
        stem = png.stem
        canonical = stem.split('__pass', 1)[0]
        groups.setdefault(canonical, []).append(png.name)
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


def _broken_manifest_entries():
    broken = []
    if not ART_MANIFEST.exists():
        return ['missing:data/manifests/art_manifest.json']
    data = _load_json(ART_MANIFEST)
    items = (((data.get('sections') or {}).get('cards') or {}).get('items') or {})
    for cid in _card_ids():
        row = items.get(cid)
        if not row:
            broken.append(f'missing_manifest_entry:{cid}')
            continue
        rel = row.get('path')
        if not rel:
            broken.append(f'missing_path:{cid}')
            continue
        full = ROOT / rel
        if not full.exists():
            broken.append(f'broken_path:{cid}:{rel}')
    return broken


def _run_module(module: str, *args: str):
    cmd = [sys.executable, '-m', module, *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        'cmd': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout.strip(),
        'stderr': proc.stderr.strip(),
    }


def run(*, dry_run: bool = False):
    report = REPORT_DIR / 'art_pipeline_cli_audit_report.txt'
    entries = _card_entries()
    missing = _missing_card_ids()
    broken = _broken_manifest_entries()
    duplicates = _duplicate_card_assets()
    lines = [
        'mode=art_audit',
        f'dry_run={dry_run}',
        f'card_manifest_exists={CARD_MANIFEST.exists()}',
        f'art_manifest_exists={ART_MANIFEST.exists()}',
        f'card_count={len(entries)}',
        f'card_pngs={len(list(CARD_DIR.glob("*.png")))}',
        f'missing_count={len(missing)}',
        f'broken_manifest_entries={len(broken)}',
        f'duplicate_groups={len(duplicates)}',
    ]
    if missing:
        lines += ['', 'missing_cards:'] + [f'- {cid}' for cid in missing[:40]]
    if broken:
        lines += ['', 'broken_manifest:'] + [f'- {row}' for row in broken[:40]]
    if duplicates:
        lines += ['', 'duplicate_assets:']
        for key, files in sorted(duplicates.items())[:40]:
            lines.append(f'- {key}: {", ".join(files)}')
    return write_text_report(report, 'chakana_studio art audit', lines)


def generate_all(*, dry_run: bool = False):
    report = REPORT_DIR / 'art_generate_report.txt'
    if dry_run:
        return write_text_report(report, 'chakana_studio art generate', [
            'mode=art_generate',
            'dry_run=True',
            f'card_count={len(_card_ids())}',
            'action=python -m tools.assets.regenerate_premium_card_batch --all',
        ])
    res = _run_module('tools.assets.regenerate_premium_card_batch', '--all')
    lines = [
        'mode=art_generate',
        'dry_run=False',
        f'card_count={len(_card_ids())}',
        f'returncode={res["returncode"]}',
        '',
        'stdout:',
        res['stdout'] or '<empty>',
        '',
        'stderr:',
        res['stderr'] or '<empty>',
    ]
    return write_text_report(report, 'chakana_studio art generate', lines)


def regenerate_missing(*, dry_run: bool = False, force: bool = False):
    report = REPORT_DIR / 'art_regenerate_missing_report.txt'
    missing = _missing_card_ids()
    lines = [
        'mode=art_regenerate_missing',
        f'dry_run={dry_run}',
        f'force={force}',
        f'missing_count={len(missing)}',
    ]
    if not missing and not force:
        lines.append('action=noop')
        return write_text_report(report, 'chakana_studio art regenerate missing', lines)
    if dry_run:
        ids = missing if missing else _card_ids()
        lines += ['', 'target_ids:'] + [f'- {cid}' for cid in ids[:60]]
        return write_text_report(report, 'chakana_studio art regenerate missing', lines)
    ids = missing if missing else _card_ids()
    res = _run_module('tools.assets.regenerate_premium_card_batch', '--ids', *ids)
    lines += [
        f'target_count={len(ids)}',
        '',
        'stdout:',
        res['stdout'] or '<empty>',
        '',
        'stderr:',
        res['stderr'] or '<empty>',
        f'returncode={res["returncode"]}',
    ]
    return write_text_report(report, 'chakana_studio art regenerate missing', lines)


def validate(*, dry_run: bool = False):
    report = REPORT_DIR / 'art_validate_report.txt'
    entries = _card_entries()
    missing = _missing_card_ids()
    broken = _broken_manifest_entries()
    dims_ok = 0
    dims_bad = []
    if not dry_run:
        import pygame
        pygame.init()
        for cid in _card_ids():
            p = _card_png_path(cid)
            if not p.exists():
                continue
            try:
                surf = pygame.image.load(str(p))
                size = surf.get_size()
                if size == (320, 220):
                    dims_ok += 1
                else:
                    dims_bad.append(f'{cid}:{size[0]}x{size[1]}')
            except Exception as exc:
                dims_bad.append(f'{cid}:load_error:{exc}')
    lines = [
        'mode=art_validate',
        f'dry_run={dry_run}',
        f'card_count={len(entries)}',
        f'missing_count={len(missing)}',
        f'broken_manifest_entries={len(broken)}',
        f'dims_ok={dims_ok}',
        f'dims_bad={len(dims_bad)}',
    ]
    if dry_run:
        lines.append('quality_validation=skipped_dry_run')
        return write_text_report(report, 'chakana_studio art validate', lines)
    res = _run_module('tools.assets.run_art_quality_validation')
    lines += [
        '',
        'quality_validation_stdout:',
        res['stdout'] or '<empty>',
        '',
        'quality_validation_stderr:',
        res['stderr'] or '<empty>',
        f'quality_validation_returncode={res["returncode"]}',
    ]
    if dims_bad:
        lines += ['', 'dimension_or_load_issues:'] + [f'- {row}' for row in dims_bad[:80]]
    return write_text_report(report, 'chakana_studio art validate', lines)


def promote(*, dry_run: bool = False):
    report = REPORT_DIR / 'art_promote_report.txt'
    staged = sorted(STAGING_DIR.glob('*.png')) if STAGING_DIR.exists() else []
    production = sorted(PRODUCTION_DIR.glob('*.png')) if PRODUCTION_DIR.exists() else []
    lines = [
        'mode=art_promote',
        f'dry_run={dry_run}',
        f'staging_exists={STAGING_DIR.exists()}',
        f'production_exists={PRODUCTION_DIR.exists()}',
        f'staging_count={len(staged)}',
        f'production_count={len(production)}',
    ]
    if not staged:
        lines.append('action=noop_no_staged_assets')
        return write_text_report(report, 'chakana_studio art promote', lines)
    lines.append('action=report_only_until_runtime_switches_to_assets/production')
    lines += ['', 'staged_assets:'] + [f'- {p.name}' for p in staged[:80]]
    return write_text_report(report, 'chakana_studio art promote', lines)
