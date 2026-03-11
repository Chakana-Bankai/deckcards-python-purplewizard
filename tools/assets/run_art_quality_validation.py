from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from game.art.art_quality_validation import evaluate_generated_art
from game.art.scene_engine import generate_scene_art, semantic_from_prompt
from game.content.card_art_generator import CardArtGenerator, PromptBuilder
from game.core.paths import data_dir, project_root

DEFAULT_IDS = ['cw_lore_10', 'hip_cosmic_warrior_20', 'arc_060']


def _load_cards() -> dict[str, dict]:
    cards: dict[str, dict] = {}
    for name in ('cards.json', 'cards_hiperboria.json', 'cards_arconte.json'):
        path = data_dir() / name
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
        rows = raw if isinstance(raw, list) else raw.get('cards', [])
        for row in rows:
            if isinstance(row, dict) and row.get('id'):
                cards[str(row['id'])] = row
    return cards


def _evaluate_card(card: dict, pb: PromptBuilder, gen: CardArtGenerator, retries: int = 1) -> dict:
    cid = str(card.get('id'))
    entry = pb.build_entry(card)
    prompt = str(entry.get('prompt_text', '') or '')
    semantic = semantic_from_prompt(prompt)
    path = project_root() / 'game' / 'assets' / 'sprites' / 'cards' / f'{cid}.png'

    last_result = generate_scene_art(cid, prompt, sum(ord(ch) for ch in cid), path)
    quality = evaluate_generated_art(
        card=card,
        path=path,
        semantic=semantic,
        scene_type=str(last_result.get('scene_type', '') or ''),
        environment_preset=str(last_result.get('environment_preset', '') or ''),
        palette_id=str((last_result.get('palette_seeded') or [''])[0] or ''),
        references_used=list(last_result.get('references_used', []) or []),
        occ_subject=float(last_result.get('occ_subject', 0.0) or 0.0),
        occ_object=float(last_result.get('occ_object', 0.0) or 0.0),
        occ_fx=float(last_result.get('occ_fx', 0.0) or 0.0),
    )
    attempt = 0
    while attempt < retries and not quality.accepted:
        attempt += 1
        gen.ensure_art(
            cid,
            list(card.get('tags', []) or []),
            str(card.get('rarity', 'common')),
            mode='force_regen',
            family=str(entry.get('family', card.get('role', '') or '')),
            symbol=str(card.get('symbol', '') or ''),
            prompt=prompt,
        )
        last_result = generate_scene_art(cid, prompt, sum(ord(ch) for ch in cid) + attempt * 101, path)
        quality = evaluate_generated_art(
            card=card,
            path=path,
            semantic=semantic,
            scene_type=str(last_result.get('scene_type', '') or ''),
            environment_preset=str(last_result.get('environment_preset', '') or ''),
            palette_id=str((last_result.get('palette_seeded') or [''])[0] or ''),
            references_used=list(last_result.get('references_used', []) or []),
            occ_subject=float(last_result.get('occ_subject', 0.0) or 0.0),
            occ_object=float(last_result.get('occ_object', 0.0) or 0.0),
            occ_fx=float(last_result.get('occ_fx', 0.0) or 0.0),
        )
        quality.retries = attempt
    return {
        'id': cid,
        'overall': quality.overall,
        'accepted': quality.accepted,
        'retries': quality.retries,
        'scene': str(last_result.get('scene_type', '') or ''),
        'env': str(last_result.get('environment_preset', '') or ''),
        'palette': str((last_result.get('palette_seeded') or [''])[0] or ''),
        'refs': list(last_result.get('references_used', []) or []),
        'occ_subject': round(float(last_result.get('occ_subject', 0.0) or 0.0), 4),
        'occ_object': round(float(last_result.get('occ_object', 0.0) or 0.0), 4),
        'occ_fx': round(float(last_result.get('occ_fx', 0.0) or 0.0), 4),
        'metrics': quality.metrics.to_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Valida calidad de arte generado y reintenta una vez si falla.')
    parser.add_argument('--ids', nargs='*', default=DEFAULT_IDS)
    parser.add_argument('--retries', type=int, default=1)
    args = parser.parse_args()

    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    cards = _load_cards()
    pb = PromptBuilder()
    gen = CardArtGenerator()
    rows = []
    accepted = 0
    for cid in args.ids:
        card = cards.get(str(cid))
        if not card:
            rows.append(f'{cid}|missing_card=True')
            continue
        result = _evaluate_card(card, pb, gen, max(0, int(args.retries)))
        accepted += 1 if result['accepted'] else 0
        m = result['metrics']
        rows.append(
            f"{result['id']}|overall={result['overall']}|accepted={result['accepted']}|retries={result['retries']}|scene={result['scene']}|env={result['env']}|palette={result['palette']}|refs={','.join(result['refs'])}|occ_subject={result['occ_subject']}|occ_object={result['occ_object']}|occ_fx={result['occ_fx']}|silhouette={m['silhouette_readability']}|subject={m['subject_recognizability']}|environment={m['environment_clarity']}|palette_coherence={m['palette_coherence']}|noise={m['excessive_noise']}|lore={m['lore_alignment']}"
        )

    overall_status = 'PASS' if accepted == len(args.ids) else 'WARNING'
    out = project_root() / 'reports' / 'validation' / 'art_quality_validation_report.txt'
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'status={overall_status}',
        f'cards={len(args.ids)}',
        f'accepted={accepted}',
        'criteria=silhouette+subject+environment+palette+noise+lore',
        *rows,
    ]
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[art_quality] report={out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
