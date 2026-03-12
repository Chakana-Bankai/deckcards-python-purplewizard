from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import pygame

from game.art.geometric_ritual_engine import render_card_from_dna
from game.cards.card_canon_registry import load_card_canon_catalog
from game.core.paths import project_root


def _archive_runtime_cards(runtime_dir: Path, archive_root: Path) -> tuple[int, Path]:
    moved = 0
    archive_root.mkdir(parents=True, exist_ok=True)
    for png in runtime_dir.glob('*.png'):
        target = archive_root / png.name
        if target.exists():
            target.unlink()
        shutil.move(str(png), str(target))
        moved += 1
    return moved, archive_root


def _build_game_art_manifest(cards: list[dict[str, str]]) -> dict[str, object]:
    items = {}
    for row in cards:
        items[row['id']] = {
            'path': row['relative_path'],
            'mode': 'immersion_rebuild_phase6',
            'generator': 'geometric_ritual_engine_frameless',
            'framed': False,
        }
    return {'items': items}


def _build_aggregate_manifest(cards: list[dict[str, str]], existing: dict[str, object] | None = None) -> dict[str, object]:
    payload = dict(existing or {})
    sections = dict(payload.get('sections', {}) or {})
    items = {}
    for row in cards:
        items[row['id']] = {
            'path': row['relative_path'],
            'exists': True,
            'set': row['faction'],
            'artwork': row['artwork_id'],
            'framed': False,
            'generator': 'geometric_ritual_engine_frameless',
        }
    sections['cards'] = {
        'count': len(cards),
        'manifest_items_count': len(items),
        'items': items,
    }
    payload['version'] = 'chakana_art_manifest_v2'
    payload['generated_at'] = int(datetime.now().timestamp())
    payload['sections'] = sections
    return payload


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    root = Path(project_root())
    runtime_dir = root / 'game' / 'assets' / 'sprites' / 'cards'
    staging_dir = root / 'assets' / 'production' / 'art' / 'staging' / 'immersion_rebuild_phase6'
    archive_dir = root / 'assets' / 'production' / 'art' / 'archive' / 'immersion_rebuild_phase6' / datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = root / 'reports' / 'art' / 'full_art_regeneration_report.txt'
    game_manifest_path = root / 'game' / 'data' / 'art_manifest.json'
    aggregate_manifest_path = root / 'data' / 'manifests' / 'art_manifest.json'
    cards_manifest_count_path = root / 'game' / 'data' / 'art_manifest_cards.json'

    runtime_dir.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    for png in staging_dir.glob('*.png'):
        png.unlink()

    catalog = load_card_canon_catalog()
    rendered = []
    identity_passed = 0
    missing = []
    for card in catalog.cards:
        artwork_id = str(card.art.artwork_id or card.id)
        out_path = staging_dir / f'{artwork_id}.png'
        result = render_card_from_dna(card.id, out_path, prompt_hint=card.name, rarity=card.rarity, apply_frame=False)
        if not out_path.exists():
            missing.append(card.id)
            continue
        if bool(result.get('identity_lock', {}).get('passed', False)):
            identity_passed += 1
        rendered.append({
            'id': card.id,
            'artwork_id': artwork_id,
            'faction': card.faction,
            'relative_path': f"game/assets/sprites/cards/{artwork_id}.png",
            'staging_path': str(out_path),
            'identity_lock_passed': bool(result.get('identity_lock', {}).get('passed', False)),
        })

    if missing or len(rendered) != catalog.count:
        lines = [
            'full_art_regeneration_report',
            'status=FAIL',
            f'catalog_count={catalog.count}',
            f'rendered_count={len(rendered)}',
            f'missing_count={len(missing)}',
        ]
        for card_id in missing[:24]:
            lines.append(f'- missing_render={card_id}')
        report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'[full_art_regeneration] report={report_path}')
        return 1

    archived_count, archived_path = _archive_runtime_cards(runtime_dir, archive_dir)
    for row in rendered:
        shutil.copy2(row['staging_path'], runtime_dir / f"{row['artwork_id']}.png")

    game_manifest = _build_game_art_manifest(rendered)
    game_manifest_path.write_text(json.dumps(game_manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    existing_aggregate = {}
    if aggregate_manifest_path.exists():
        try:
            existing_aggregate = json.loads(aggregate_manifest_path.read_text(encoding='utf-8'))
        except Exception:
            existing_aggregate = {}
    aggregate_manifest = _build_aggregate_manifest(rendered, existing_aggregate)
    aggregate_manifest_path.write_text(json.dumps(aggregate_manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    cards_manifest_count_path.write_text(
        json.dumps({'count': len(rendered), 'generator_version': 'geometric_ritual_engine_frameless_v1'}, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )

    runtime_pngs = sorted(p.name for p in runtime_dir.glob('*.png'))
    stale_refs = [row['id'] for row in rendered if row['artwork_id'] + '.png' not in runtime_pngs]

    lines = [
        'full_art_regeneration_report',
        'status=PASS' if not stale_refs else 'status=WARNING',
        f'catalog_count={catalog.count}',
        f'rendered_count={len(rendered)}',
        f'identity_lock_pass_count={identity_passed}',
        f'identity_lock_fail_count={len(rendered) - identity_passed}',
        f'archived_runtime_png_count={archived_count}',
        f'archive_path={archived_path.as_posix()}',
        f'staging_path={staging_dir.as_posix()}',
        f'runtime_dir={runtime_dir.as_posix()}',
        f'game_manifest_items={len(game_manifest.get("items", {}))}',
        f'aggregate_manifest_cards={len(aggregate_manifest.get("sections", {}).get("cards", {}).get("items", {}))}',
        'frameless_runtime_assets=True',
        'missing_art=0',
        f'stale_runtime_refs={len(stale_refs)}',
        '',
        'sample_outputs:',
    ]
    for row in rendered[:12]:
        lines.append(f"- {row['id']} -> {row['relative_path']} identity_lock_passed={row['identity_lock_passed']}")
    if stale_refs:
        lines.extend(['', 'stale_refs:'])
        for card_id in stale_refs[:24]:
            lines.append(f'- {card_id}')

    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[full_art_regeneration] staging={staging_dir}')
    print(f'[full_art_regeneration] archive={archived_path}')
    print(f'[full_art_regeneration] runtime={runtime_dir}')
    print(f'[full_art_regeneration] report={report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
