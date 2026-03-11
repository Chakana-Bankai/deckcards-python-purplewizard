from __future__ import annotations

import json
import os
from pathlib import Path

import pygame

from game.art.frame_engine import generate_frame_asset
from game.content.card_art_generator import PromptBuilder
from game.art.scene_engine import generate_scene_art
from game.core.paths import data_dir, project_root

SAMPLES = ['cw_lore_10', 'hip_cosmic_warrior_20', 'arc_060']


def _load_cards() -> dict[str, dict]:
    cards = {}
    for name in ('cards.json', 'cards_hiperboria.json', 'cards_arconte.json'):
        path = data_dir() / name
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
        rows = raw if isinstance(raw, list) else raw.get('cards', [])
        for row in rows:
            if isinstance(row, dict) and row.get('id'):
                cards[str(row['id'])] = row
    return cards


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    cards = _load_cards()
    pb = PromptBuilder()
    out_dir = project_root() / 'reports' / 'validation' / 'scene_pipeline_samples'
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = ['status=ok', 'samples=3', 'pipeline=frame_engine+scene_engine+reference_sampler+silhouette_builder+fx_layer']
    for cid in SAMPLES:
        card = cards[cid]
        entry = pb.build_entry(card)
        art_path = out_dir / f'{cid}_art.png'
        frame_path = out_dir / f'{cid}_frame.png'
        result = generate_scene_art(cid, entry['prompt_text'], sum(ord(ch) for ch in cid), art_path)
        pygame.image.save(generate_frame_asset(), str(frame_path))
        lines.append(
            f"{cid}|art={art_path.name}|frame={frame_path.name}|scene={result.get('scene_type','')}|env={result.get('environment_preset','')}|palette={','.join(map(str, result.get('palette_seeded', [])))}|refs={','.join(result.get('references_used', []))}|occ_subject={result.get('occ_subject','')}|occ_object={result.get('occ_object','')}|occ_fx={result.get('occ_fx','')}|readability_ok={result.get('readability_ok','')}"
        )
    report = project_root() / 'reports' / 'validation' / 'scene_pipeline_test_report.txt'
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[scene_pipeline] report={report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
