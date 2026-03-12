from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image
import cv2
import numpy as np

from .common import ROOT, ensure_dir, rel, write_json, write_text_report

REPORT = ROOT / 'reports' / 'art' / 'art_director_pass_report.txt'
SPEC_PATH = ROOT / 'data' / 'art_specs' / 'card_art_direction.json'
MANIFEST_PATH = ROOT / 'game' / 'data' / 'art_manifest.json'
RUNTIME_DIR = ROOT / 'game' / 'assets' / 'sprites' / 'cards'
STAGING_DIR = ROOT / 'assets' / 'production' / 'art' / 'staging'
APPROVED_DIR = ROOT / 'assets' / 'production' / 'art' / 'approved'
ARCHIVE_DIR = ROOT / 'assets' / 'production' / 'art' / 'archive'
STAGING_MANIFEST = STAGING_DIR / 'art_director_staging_manifest.json'


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _runtime_assets() -> list[Path]:
    if not RUNTIME_DIR.exists():
        return []
    return sorted([p for p in RUNTIME_DIR.glob('*.png') if p.is_file()])


def _archive_assets() -> list[Path]:
    archive_root = RUNTIME_DIR / '_archive_passes'
    if not archive_root.exists():
        return []
    return sorted(archive_root.rglob('*.png'))


def _asset_metrics(path: Path) -> dict[str, object]:
    width = 0
    height = 0
    palette_diversity = 0
    border_ratio = 0.0
    try:
        with Image.open(path) as img:
            img = img.convert('RGBA')
            width, height = img.size
            rgb = img.convert('RGB')
            quant = rgb.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
            palette_diversity = len({idx for idx in quant.getdata()})
            arr = np.asarray(rgb, dtype=np.uint8)
            edge_band = max(2, min(width, height) // 18)
            top = arr[:edge_band, :, :]
            bottom = arr[-edge_band:, :, :]
            left = arr[:, :edge_band, :]
            right = arr[:, -edge_band:, :]
            border = np.concatenate([
                top.reshape(-1, 3),
                bottom.reshape(-1, 3),
                left.reshape(-1, 3),
                right.reshape(-1, 3),
            ], axis=0)
            inner = arr[edge_band: max(edge_band + 1, height - edge_band), edge_band: max(edge_band + 1, width - edge_band), :]
            inner_mean = inner.reshape(-1, 3).mean(axis=0) if inner.size else np.array([127.0, 127.0, 127.0])
            border_delta = np.abs(border.mean(axis=0) - inner_mean).mean() / 255.0 if border.size else 0.0
            border_ratio = float(max(0.0, min(1.0, 1.0 - border_delta)))
    except Exception:
        pass
    frame = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    blur_score = float(cv2.Laplacian(frame, cv2.CV_64F).var()) if frame is not None else 0.0
    file_size = int(path.stat().st_size)
    return {
        'width': width,
        'height': height,
        'file_size': file_size,
        'blur_score': round(blur_score, 4),
        'palette_diversity': int(palette_diversity),
        'border_ratio': round(border_ratio, 4),
    }


def _score_asset(path: Path, spec: dict) -> dict[str, object]:
    metrics = _asset_metrics(path)
    warnings: list[str] = []
    score = 1.0
    if metrics['file_size'] < 120000:
        warnings.append('low_filesize')
        score -= 0.22
    if metrics['width'] < 300 or metrics['height'] < 200:
        warnings.append('low_resolution')
        score -= 0.18
    thresholds = spec.get('thresholds') or {}
    blur_threshold = float(thresholds.get('blur_warning_threshold', 40.0))
    if float(metrics['blur_score']) < blur_threshold:
        warnings.append('blurry')
        score -= 0.18
    palette_floor = int(thresholds.get('palette_diversity_warning_floor', 18) or 18)
    if int(metrics['palette_diversity']) < palette_floor:
        warnings.append('low_palette_diversity')
        score -= 0.16
    border_threshold = float(thresholds.get('border_warning_threshold', 0.62))
    if float(metrics['border_ratio']) > border_threshold:
        warnings.append('frame_like_border')
        score -= 0.14
    stem = path.stem.lower()
    if '__pass' in stem or '_tmp' in stem or 'test' in stem:
        warnings.append('legacy_or_test_name')
        score -= 0.10
    score = round(max(0.0, min(1.0, score)), 4)
    return {
        'asset_name': path.name,
        'source_path': rel(path),
        'score': score,
        'warnings': warnings,
        'metrics': metrics,
    }


def _stage_candidates(candidates: list[dict[str, object]], max_candidates: int, *, dry_run: bool) -> list[dict[str, object]]:
    staged: list[dict[str, object]] = []
    for row in candidates[:max_candidates]:
        source = ROOT / str(row['source_path'])
        target = STAGING_DIR / f"{source.stem}__director_candidate{source.suffix}"
        staged.append({
            'asset_name': row['asset_name'],
            'source_path': row['source_path'],
            'staging_path': rel(target),
            'score': row['score'],
            'warnings': row['warnings'],
            'metrics': row['metrics'],
            'action': 'copy_to_staging',
        })
        if not dry_run and source.exists():
            shutil.copy2(source, target)
    return staged


def run(*, dry_run: bool = False):
    spec = _load_json(SPEC_PATH)
    manifest = _load_json(MANIFEST_PATH)
    runtime_assets = _runtime_assets()
    archive_assets = _archive_assets()
    thresholds = spec.get('thresholds') or {}
    staging_threshold = float(thresholds.get('minimum_score_for_staging', 0.55))
    review_threshold = float(thresholds.get('minimum_score_for_review_queue', 0.9))
    scored = [_score_asset(path, spec) for path in runtime_assets]
    flagged = sorted([row for row in scored if float(row['score']) < staging_threshold], key=lambda row: (float(row['score']), row['asset_name']))
    review_queue = sorted([row for row in scored if float(row['score']) < review_threshold], key=lambda row: (float(row['score']), row['asset_name']))

    for folder in (STAGING_DIR, APPROVED_DIR, ARCHIVE_DIR):
        ensure_dir(folder)

    max_candidates = int(spec.get('max_candidates_per_pass', 12) or 12)
    selected = flagged if flagged else review_queue
    staged = _stage_candidates(selected, max_candidates, dry_run=dry_run)
    staging_payload = {
        'version': 'art_director_staging_v2',
        'dry_run': bool(dry_run),
        'runtime_bucket': rel(RUNTIME_DIR),
        'staging_bucket': rel(STAGING_DIR),
        'flagged_candidate_count': len(flagged),
        'review_queue_count': len(review_queue),
        'candidate_count': len(staged),
        'selection_mode': 'flagged' if flagged else 'review_queue',
        'candidates': staged,
    }
    write_json(STAGING_MANIFEST, staging_payload)

    lines = [
        'phase=4',
        'status=PASS',
        f'dry_run={dry_run}',
        f'spec_exists={SPEC_PATH.exists()}',
        f'manifest_exists={MANIFEST_PATH.exists()}',
        f'runtime_asset_count={len(runtime_assets)}',
        f'archived_pass_asset_count={len(archive_assets)}',
        f'staging_dir={rel(STAGING_DIR)}',
        f'approved_dir={rel(APPROVED_DIR)}',
        f'archive_dir={rel(ARCHIVE_DIR)}',
        f'staging_manifest={rel(STAGING_MANIFEST)}',
        f'manifest_item_count={len((manifest.get("items") or {})) if isinstance(manifest, dict) else 0}',
        f'flagged_asset_count={len(flagged)}',
        f'review_queue_count={len(review_queue)}',
        f'staged_candidate_count={len(staged)}',
        f'max_candidates_per_pass={max_candidates}',
        f'selection_mode={"flagged" if flagged else "review_queue"}',
        'action=staging_queue_refined',
        '',
        'staged_candidates:',
    ]
    for row in staged[:20]:
        lines.append(f"- {row['asset_name']}: score={row['score']} staging={row['staging_path']} warnings={','.join(row['warnings']) or 'none'} palette={row['metrics']['palette_diversity']} border={row['metrics']['border_ratio']}")
    if not staged:
        lines.append('- none')
    lines += [
        '',
        'director_pass_capabilities:',
        '- reads art specs from data/art_specs/card_art_direction.json',
        '- audits runtime production art in game/assets/sprites/cards',
        '- scores assets using blur, file size, palette diversity and frame-like border heuristics',
        '- falls back to a review queue when no asset crosses the hard staging threshold',
        '- copies selected candidates into assets/production/art/staging with a staging manifest',
        '- keeps promotion/archive non-destructive in this phase',
    ]
    return write_text_report(REPORT, 'chakana_studio art director pass', lines)
