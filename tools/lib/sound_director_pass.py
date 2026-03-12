from __future__ import annotations

import json
import shutil
from pathlib import Path

from .common import ROOT, ensure_dir, rel, write_json, write_text_report

REPORT = ROOT / 'reports' / 'audio' / 'sound_director_pass_report.txt'
SPEC_PATH = ROOT / 'data' / 'music_specs' / 'music_direction_mvp.json'
MANIFEST_PATH = ROOT / 'game' / 'data' / 'audio_manifest.json'
CURATED_DIR = ROOT / 'game' / 'assets' / 'curated' / 'audio'
GENERATED_DIR = ROOT / 'game' / 'audio' / 'generated'
STAGING_DIR = ROOT / 'assets' / 'production' / 'audio' / 'staging'
APPROVED_DIR = ROOT / 'assets' / 'production' / 'audio' / 'approved'
ARCHIVE_DIR = ROOT / 'assets' / 'production' / 'audio' / 'archive'
STAGING_MANIFEST = STAGING_DIR / 'sound_director_staging_manifest.json'


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _manifest_items() -> dict:
    data = _load_json(MANIFEST_PATH)
    items = data.get('items', {}) if isinstance(data, dict) else {}
    return items if isinstance(items, dict) else {}


def _score_audio_item(item_id: str, meta: dict, spec: dict) -> dict[str, object]:
    warnings: list[str] = []
    score = 0.78
    version = str(meta.get('version', '') or '')
    if version.endswith('v6'):
        warnings.append('legacy_version')
        score -= 0.14
    source = str(meta.get('source', '') or '')
    if source == 'generated':
        score -= 0.06
    analysis = meta.get('analysis', {}) if isinstance(meta.get('analysis'), dict) else {}
    variation_floor = float(((spec.get('thresholds') or {}).get('variation_warning_floor', 0.28)))
    monotony_threshold = float(((spec.get('thresholds') or {}).get('monotony_warning_threshold', 0.65)))
    variation = float(analysis.get('variation_score', 0.0) or 0.0)
    monotony = float(analysis.get('monotony_score', 0.0) or 0.0)
    if analysis and variation < variation_floor:
        warnings.append('low_variation')
        score -= 0.18
    if analysis and monotony > monotony_threshold:
        warnings.append('high_monotony')
        score -= 0.10
    if not analysis and str(meta.get('type', '')) in {'stinger', 'ambient', 'bgm'}:
        warnings.append('missing_analysis')
        score -= 0.12
    if str(meta.get('type', '')) == 'stinger' and source == 'generated':
        warnings.append('stinger_review_candidate')
        score -= 0.05
    score = round(max(0.0, min(1.0, score)), 4)
    return {
        'item_id': item_id,
        'score': score,
        'warnings': warnings,
        'type': str(meta.get('type', '') or ''),
        'context': str(meta.get('context', '') or ''),
        'source': source,
        'version': version,
        'relative_path': str(meta.get('relative_path', '') or ''),
        'analysis': analysis,
    }


def _stage_candidates(flagged: list[dict[str, object]], max_candidates: int, *, dry_run: bool) -> list[dict[str, object]]:
    staged: list[dict[str, object]] = []
    for row in flagged[:max_candidates]:
        source = ROOT / str(row['relative_path'])
        if not source.exists():
            continue
        target = STAGING_DIR / row['type'] / f"{source.stem}__director_candidate{source.suffix}"
        ensure_dir(target.parent)
        staged.append({
            'item_id': row['item_id'],
            'type': row['type'],
            'context': row['context'],
            'source_path': row['relative_path'],
            'staging_path': rel(target),
            'score': row['score'],
            'warnings': row['warnings'],
            'analysis': row['analysis'],
            'action': 'copy_to_staging',
        })
        if not dry_run:
            shutil.copy2(source, target)
    return staged


def run(*, dry_run: bool = False):
    spec = _load_json(SPEC_PATH)
    items = _manifest_items()
    required = set((spec.get('required_mvp_contexts') or []))
    present_contexts = {str((meta or {}).get('context', '') or '') for meta in items.values() if isinstance(meta, dict)}
    mapped_contexts = {('map' if ctx.startswith('map_') else 'boss' if ctx == 'combat_boss' else ctx) for ctx in present_contexts}
    missing = sorted(ctx for ctx in required if ctx not in mapped_contexts)
    scored = [_score_audio_item(item_id, meta, spec) for item_id, meta in items.items() if isinstance(meta, dict)]
    threshold = float(((spec.get('thresholds') or {}).get('minimum_score_for_staging', 0.58)))
    flagged = sorted([row for row in scored if float(row['score']) < threshold], key=lambda row: (float(row['score']), row['item_id']))

    for folder in (STAGING_DIR, APPROVED_DIR, ARCHIVE_DIR):
        ensure_dir(folder)

    max_candidates = int(spec.get('max_candidates_per_pass', 10) or 10)
    staged = _stage_candidates(flagged, max_candidates, dry_run=dry_run)
    staging_payload = {
        'version': 'sound_director_staging_v1',
        'dry_run': bool(dry_run),
        'runtime_manifest': rel(MANIFEST_PATH),
        'staging_bucket': rel(STAGING_DIR),
        'candidate_count': len(staged),
        'missing_required_contexts': missing,
        'candidates': staged,
    }
    write_json(STAGING_MANIFEST, staging_payload)

    source_counts: dict[str, int] = {}
    version_counts: dict[str, int] = {}
    for meta in items.values():
        if not isinstance(meta, dict):
            continue
        source_counts[meta.get('source', 'unknown')] = source_counts.get(meta.get('source', 'unknown'), 0) + 1
        version_counts[meta.get('version', 'unknown')] = version_counts.get(meta.get('version', 'unknown'), 0) + 1

    lines = [
        'phase=3',
        'status=PASS',
        f'dry_run={dry_run}',
        f'spec_exists={SPEC_PATH.exists()}',
        f'manifest_exists={MANIFEST_PATH.exists()}',
        f'manifest_item_count={len(items)}',
        f'curated_dir={rel(CURATED_DIR)}',
        f'generated_dir={rel(GENERATED_DIR)}',
        f'staging_dir={rel(STAGING_DIR)}',
        f'approved_dir={rel(APPROVED_DIR)}',
        f'archive_dir={rel(ARCHIVE_DIR)}',
        f'staging_manifest={rel(STAGING_MANIFEST)}',
        f'source_counts={source_counts}',
        f'version_counts={version_counts}',
        f'missing_required_contexts={missing}',
        f'flagged_audio_count={len(flagged)}',
        f'staged_candidate_count={len(staged)}',
        f'max_candidates_per_pass={max_candidates}',
        'action=staging_queue_prepared',
        '',
        'staged_candidates:',
    ]
    for row in staged[:20]:
        lines.append(f"- {row['item_id']}: score={row['score']} staging={row['staging_path']} warnings={','.join(row['warnings']) or 'none'}")
    if not staged:
        lines.append('- none')
    lines += [
        '',
        'director_pass_capabilities:',
        '- reads music specs from data/music_specs/music_direction_mvp.json',
        '- audits runtime audio from game/data/audio_manifest.json',
        '- maps top flagged items into assets/production/audio/staging as a controlled review queue',
        '- writes a staging manifest for later regeneration/promotion phases',
        '- keeps promotion/archive non-destructive in this phase',
    ]
    return write_text_report(REPORT, 'chakana_studio sound director pass', lines)
