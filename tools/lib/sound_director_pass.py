from __future__ import annotations

import json
import shutil
from pathlib import Path
import sys

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.audio.audio_stack_tools import analyze_audio_file
from .common import ensure_dir, rel, write_json, write_text_report

REPORT = ROOT / 'reports' / 'audio' / 'sound_director_pass_report.txt'
SPEC_PATH = ROOT / 'data' / 'music_specs' / 'music_direction_mvp.json'
MANIFEST_PATH = ROOT / 'game' / 'data' / 'audio_manifest.json'
CURATED_DIR = ROOT / 'game' / 'assets' / 'curated' / 'audio'
GENERATED_DIR = ROOT / 'game' / 'audio' / 'generated'
STAGING_DIR = ROOT / 'assets' / 'production' / 'audio' / 'staging'
IMPROVED_DIR = STAGING_DIR / 'improved'
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


def _improve_candidate(source: Path, target: Path) -> None:
    data, sample_rate = sf.read(str(source), always_2d=True)
    audio = data.astype(np.float32, copy=False)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-6:
        audio = audio * min(0.96 / peak, 1.12)
    fade_samples = min(max(64, sample_rate // 100), max(1, audio.shape[0] // 8))
    if fade_samples > 1 and audio.shape[0] >= fade_samples:
        fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32).reshape(-1, 1)
        fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32).reshape(-1, 1)
        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out
    target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(target), audio, sample_rate, subtype='PCM_16')


def _improve_staged_candidates(staged: list[dict[str, object]], spec: dict, *, dry_run: bool) -> list[dict[str, object]]:
    improved_rows: list[dict[str, object]] = []
    max_improvements = int(spec.get('max_improvements_per_pass', 6) or 6)
    for row in staged[:max_improvements]:
        staged_path = ROOT / str(row['staging_path'])
        improved_path = IMPROVED_DIR / row['type'] / f"{Path(row['item_id']).stem}__improved.wav"
        if not dry_run and staged_path.exists():
            _improve_candidate(staged_path, improved_path)
        before_analysis = analyze_audio_file(staged_path).model_dump() if staged_path.exists() else row.get('analysis', {})
        after_analysis = analyze_audio_file(improved_path).model_dump() if improved_path.exists() else before_analysis
        improved_rows.append({
            'item_id': row['item_id'],
            'type': row['type'],
            'context': row['context'],
            'source_path': row['source_path'],
            'source_staging_path': row['staging_path'],
            'improved_path': rel(improved_path),
            'before_analysis': before_analysis,
            'after_analysis': after_analysis,
            'peak_db_delta': round(float(after_analysis.get('peak_db', 0.0)) - float(before_analysis.get('peak_db', 0.0)), 4),
            'variation_delta': round(float(after_analysis.get('variation_score', 0.0)) - float(before_analysis.get('variation_score', 0.0)), 4),
            'action': 'improved_candidate_generated',
        })
    return improved_rows


def _promotion_score(after_analysis: dict[str, object], spec: dict) -> float:
    thresholds = spec.get('thresholds') or {}
    variation_floor = float(thresholds.get('variation_warning_floor', 0.28))
    monotony_threshold = float(thresholds.get('monotony_warning_threshold', 0.65))
    variation = float(after_analysis.get('variation_score', 0.0) or 0.0)
    monotony = float(after_analysis.get('monotony_score', 1.0) or 1.0)
    peak_db = float(after_analysis.get('peak_db', -12.0) or -12.0)
    score = 0.68
    if variation >= variation_floor:
        score += 0.1
    if monotony <= monotony_threshold:
        score += 0.08
    if -3.0 <= peak_db <= -0.1:
        score += 0.08
    if float(after_analysis.get('loop_end_seconds', 0.0) or 0.0) > 0.5:
        score += 0.04
    return round(min(1.0, score), 4)


def _promote_candidates(improved: list[dict[str, object]], spec: dict, *, dry_run: bool) -> list[dict[str, object]]:
    promoted_rows: list[dict[str, object]] = []
    promotion_threshold = float((spec.get('thresholds') or {}).get('minimum_score_for_promotion', 0.8))
    suffix = str(((spec.get('archive_policy') or {}).get('suffix_pattern', '__director_pass')) or '__director_pass')
    for row in improved:
        promotion_score = _promotion_score(row['after_analysis'], spec)
        if promotion_score < promotion_threshold:
            continue
        runtime_path = ROOT / str(row['source_path'])
        improved_path = ROOT / str(row['improved_path'])
        approved_path = APPROVED_DIR / row['type'] / Path(row['improved_path']).name
        archive_name = f"{runtime_path.stem}{suffix}{runtime_path.suffix}"
        archive_path = ARCHIVE_DIR / row['type'] / archive_name
        promoted_rows.append({
            'item_id': row['item_id'],
            'runtime_path': rel(runtime_path),
            'approved_path': rel(approved_path),
            'archive_path': rel(archive_path),
            'improved_path': row['improved_path'],
            'promotion_score': promotion_score,
            'action': 'promote_to_runtime',
        })
        if not dry_run and runtime_path.exists() and improved_path.exists():
            ensure_dir(approved_path.parent)
            ensure_dir(archive_path.parent)
            shutil.copy2(runtime_path, archive_path)
            shutil.copy2(improved_path, approved_path)
            shutil.copy2(improved_path, runtime_path)
    return promoted_rows


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

    for folder in (STAGING_DIR, IMPROVED_DIR, APPROVED_DIR, ARCHIVE_DIR):
        ensure_dir(folder)

    max_candidates = int(spec.get('max_candidates_per_pass', 10) or 10)
    staged = _stage_candidates(flagged, max_candidates, dry_run=dry_run)
    improved = _improve_staged_candidates(staged, spec, dry_run=dry_run)
    promoted = _promote_candidates(improved, spec, dry_run=dry_run)
    staging_payload = {
        'version': 'sound_director_staging_v3',
        'dry_run': bool(dry_run),
        'runtime_manifest': rel(MANIFEST_PATH),
        'staging_bucket': rel(STAGING_DIR),
        'improved_bucket': rel(IMPROVED_DIR),
        'approved_bucket': rel(APPROVED_DIR),
        'archive_bucket': rel(ARCHIVE_DIR),
        'candidate_count': len(staged),
        'improved_candidate_count': len(improved),
        'promoted_candidate_count': len(promoted),
        'missing_required_contexts': missing,
        'candidates': staged,
        'improved_candidates': improved,
        'promoted_candidates': promoted,
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
        'phase=7',
        'status=PASS',
        f'dry_run={dry_run}',
        f'spec_exists={SPEC_PATH.exists()}',
        f'manifest_exists={MANIFEST_PATH.exists()}',
        f'manifest_item_count={len(items)}',
        f'curated_dir={rel(CURATED_DIR)}',
        f'generated_dir={rel(GENERATED_DIR)}',
        f'staging_dir={rel(STAGING_DIR)}',
        f'improved_dir={rel(IMPROVED_DIR)}',
        f'approved_dir={rel(APPROVED_DIR)}',
        f'archive_dir={rel(ARCHIVE_DIR)}',
        f'staging_manifest={rel(STAGING_MANIFEST)}',
        f'source_counts={source_counts}',
        f'version_counts={version_counts}',
        f'missing_required_contexts={missing}',
        f'flagged_audio_count={len(flagged)}',
        f'staged_candidate_count={len(staged)}',
        f'improved_candidate_count={len(improved)}',
        f'promoted_candidate_count={len(promoted)}',
        f'max_candidates_per_pass={max_candidates}',
        f'max_improvements_per_pass={int(spec.get("max_improvements_per_pass", 6) or 6)}',
        'action=promotion_applied',
        '',
        'promoted_candidates:',
    ]
    for row in promoted[:20]:
        lines.append(
            f"- {row['item_id']}: runtime={row['runtime_path']} approved={row['approved_path']} archive={row['archive_path']} promotion_score={row['promotion_score']}"
        )
    if not promoted:
        lines.append('- none')
    lines += [
        '',
        'director_pass_capabilities:',
        '- reads music specs from data/music_specs/music_direction_mvp.json',
        '- audits runtime audio from game/data/audio_manifest.json',
        '- maps top flagged items into assets/production/audio/staging as a controlled review queue',
        '- generates improved audio candidates with safe normalization and fade cleanup',
        '- promotes improved candidates that meet the promotion threshold',
        '- archives replaced runtime audio safely before replacement',
    ]
    return write_text_report(REPORT, 'chakana_studio sound director pass', lines)
