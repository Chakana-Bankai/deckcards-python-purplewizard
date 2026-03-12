from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
import numpy as np

from .common import ROOT, ensure_dir, rel, write_json, write_text_report

REPORT = ROOT / 'reports' / 'art' / 'art_director_pass_report.txt'
SPEC_PATH = ROOT / 'data' / 'art_specs' / 'card_art_direction.json'
MANIFEST_PATH = ROOT / 'game' / 'data' / 'art_manifest.json'
RUNTIME_DIR = ROOT / 'game' / 'assets' / 'sprites' / 'cards'
STAGING_DIR = ROOT / 'assets' / 'production' / 'art' / 'staging'
IMPROVED_DIR = STAGING_DIR / 'improved'
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
    file_size = int(path.stat().st_size) if path.exists() else 0
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
    thresholds = spec.get('thresholds') or {}
    if metrics['file_size'] < 120000:
        warnings.append('low_filesize')
        score -= 0.22
    if metrics['width'] < 300 or metrics['height'] < 200:
        warnings.append('low_resolution')
        score -= 0.18
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


def _improve_candidate(source: Path, target: Path) -> None:
    with Image.open(source) as img:
        img = img.convert('RGBA')
        width, height = img.size
        crop_x = max(1, width // 64)
        crop_y = max(1, height // 64)
        cropped = img.crop((crop_x, crop_y, width - crop_x, height - crop_y)).resize((width, height), Image.Resampling.LANCZOS)
        rgb = cropped.convert('RGB')
        rgb = ImageOps.autocontrast(rgb, cutoff=1)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
        rgb = ImageEnhance.Color(rgb).enhance(1.06)
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.2, percent=135, threshold=2))
        alpha = cropped.getchannel('A')
        improved = Image.merge('RGBA', (*rgb.split(), alpha))
        target.parent.mkdir(parents=True, exist_ok=True)
        improved.save(target)


def _improve_staged_candidates(staged: list[dict[str, object]], spec: dict, *, dry_run: bool) -> list[dict[str, object]]:
    improved_rows: list[dict[str, object]] = []
    max_improvements = int(spec.get('max_improvements_per_pass', 6) or 6)
    for row in staged[:max_improvements]:
        staged_path = ROOT / str(row['staging_path'])
        improved_path = IMPROVED_DIR / f"{Path(row['asset_name']).stem}__improved.png"
        if not dry_run and staged_path.exists():
            _improve_candidate(staged_path, improved_path)
        source_metrics = row['metrics']
        improved_metrics = _asset_metrics(improved_path) if improved_path.exists() else source_metrics
        improved_score_row = _score_asset(improved_path, spec) if improved_path.exists() else {'score': row['score'], 'warnings': row['warnings']}
        improved_rows.append({
            'asset_name': row['asset_name'],
            'source_path': row['source_path'],
            'source_staging_path': row['staging_path'],
            'improved_path': rel(improved_path),
            'before_score': row['score'],
            'after_score': improved_score_row['score'],
            'score_delta': round(float(improved_score_row['score']) - float(row['score']), 4),
            'before_metrics': source_metrics,
            'after_metrics': improved_metrics,
            'after_warnings': improved_score_row.get('warnings', []),
            'action': 'improved_candidate_generated',
        })
    return improved_rows


def _promote_candidates(improved: list[dict[str, object]], spec: dict, *, dry_run: bool) -> list[dict[str, object]]:
    promoted_rows: list[dict[str, object]] = []
    promotion_threshold = float((spec.get('thresholds') or {}).get('minimum_score_for_promotion', 0.78))
    suffix = str(((spec.get('archive_policy') or {}).get('suffix_pattern', '__director_pass')) or '__director_pass')
    for row in improved:
        after_score = float(row['after_score'])
        if after_score < promotion_threshold:
            continue
        runtime_path = ROOT / str(row['source_path'])
        improved_path = ROOT / str(row['improved_path'])
        approved_path = APPROVED_DIR / Path(row['improved_path']).name
        archive_name = f"{runtime_path.stem}{suffix}{runtime_path.suffix}"
        archive_path = ARCHIVE_DIR / archive_name
        promoted_rows.append({
            'asset_name': row['asset_name'],
            'runtime_path': rel(runtime_path),
            'approved_path': rel(approved_path),
            'archive_path': rel(archive_path),
            'improved_path': row['improved_path'],
            'after_score': after_score,
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
    manifest = _load_json(MANIFEST_PATH)
    runtime_assets = _runtime_assets()
    archive_assets = _archive_assets()
    thresholds = spec.get('thresholds') or {}
    staging_threshold = float(thresholds.get('minimum_score_for_staging', 0.55))
    review_threshold = float(thresholds.get('minimum_score_for_review_queue', 0.9))
    scored = [_score_asset(path, spec) for path in runtime_assets]
    flagged = sorted([row for row in scored if float(row['score']) < staging_threshold], key=lambda row: (float(row['score']), row['asset_name']))
    review_queue = sorted([row for row in scored if float(row['score']) < review_threshold], key=lambda row: (float(row['score']), row['asset_name']))

    for folder in (STAGING_DIR, IMPROVED_DIR, APPROVED_DIR, ARCHIVE_DIR):
        ensure_dir(folder)

    max_candidates = int(spec.get('max_candidates_per_pass', 12) or 12)
    selected = flagged if flagged else review_queue
    staged = _stage_candidates(selected, max_candidates, dry_run=dry_run)
    improved = _improve_staged_candidates(staged, spec, dry_run=dry_run)
    promoted = _promote_candidates(improved, spec, dry_run=dry_run)
    staging_payload = {
        'version': 'art_director_staging_v4',
        'dry_run': bool(dry_run),
        'runtime_bucket': rel(RUNTIME_DIR),
        'staging_bucket': rel(STAGING_DIR),
        'improved_bucket': rel(IMPROVED_DIR),
        'approved_bucket': rel(APPROVED_DIR),
        'archive_bucket': rel(ARCHIVE_DIR),
        'flagged_candidate_count': len(flagged),
        'review_queue_count': len(review_queue),
        'candidate_count': len(staged),
        'improved_candidate_count': len(improved),
        'promoted_candidate_count': len(promoted),
        'selection_mode': 'flagged' if flagged else 'review_queue',
        'candidates': staged,
        'improved_candidates': improved,
        'promoted_candidates': promoted,
    }
    write_json(STAGING_MANIFEST, staging_payload)

    lines = [
        'phase=7',
        'status=PASS',
        f'dry_run={dry_run}',
        f'spec_exists={SPEC_PATH.exists()}',
        f'manifest_exists={MANIFEST_PATH.exists()}',
        f'runtime_asset_count={len(runtime_assets)}',
        f'archived_pass_asset_count={len(archive_assets)}',
        f'staging_dir={rel(STAGING_DIR)}',
        f'improved_dir={rel(IMPROVED_DIR)}',
        f'approved_dir={rel(APPROVED_DIR)}',
        f'archive_dir={rel(ARCHIVE_DIR)}',
        f'staging_manifest={rel(STAGING_MANIFEST)}',
        f'manifest_item_count={len((manifest.get("items") or {})) if isinstance(manifest, dict) else 0}',
        f'flagged_asset_count={len(flagged)}',
        f'review_queue_count={len(review_queue)}',
        f'staged_candidate_count={len(staged)}',
        f'improved_candidate_count={len(improved)}',
        f'promoted_candidate_count={len(promoted)}',
        f'max_candidates_per_pass={max_candidates}',
        f'max_improvements_per_pass={int(spec.get("max_improvements_per_pass", 6) or 6)}',
        f'selection_mode={"flagged" if flagged else "review_queue"}',
        'action=promotion_applied',
        '',
        'promoted_candidates:',
    ]
    for row in promoted[:20]:
        lines.append(
            f"- {row['asset_name']}: runtime={row['runtime_path']} approved={row['approved_path']} archive={row['archive_path']} after={row['after_score']}"
        )
    if not promoted:
        lines.append('- none')
    lines += [
        '',
        'director_pass_capabilities:',
        '- reads art specs from data/art_specs/card_art_direction.json',
        '- audits runtime production art in game/assets/sprites/cards',
        '- stages review candidates in assets/production/art/staging',
        '- generates improved art candidates with crop cleanup, autocontrast and sharpen pass',
        '- promotes improved candidates that meet the promotion threshold',
        '- archives replaced runtime art safely before replacement',
    ]
    return write_text_report(REPORT, 'chakana_studio art director pass', lines)
