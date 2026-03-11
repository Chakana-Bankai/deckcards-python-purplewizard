from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from game.content.card_art_generator import PromptBuilder
from game.art.reference_sampler import ReferenceSampler
from game.art.scene_engine import (
    semantic_from_prompt,
    _categories_for_prompt,
    _keywords_from_semantic,
    _prioritize_refs,
    _resolve_explicit_refs,
    _palette_from_refs,
    _strong_foreground_palette,
    _draw_background,
    _apply_contrast,
)
from game.art.silhouette_builder import draw_subject, draw_focus_object
from game.art.fx_layer import draw_fx
from game.core.paths import data_dir, project_root

DEFAULT_IDS = ['cw_lore_10', 'hip_cosmic_warrior_20', 'arc_060']


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


def _occupancy_ratio(surface: pygame.Surface) -> float:
    mask = pygame.mask.from_surface(surface)
    total = surface.get_width() * surface.get_height()
    return round(mask.count() / max(1, total), 4)


def _compose_preview(prompt: str, seed: int) -> tuple[dict, dict[str, pygame.Surface]]:
    semantic = semantic_from_prompt(prompt)
    sampler = ReferenceSampler()
    explicit_refs = _resolve_explicit_refs(sampler, semantic)
    sampled_refs = sampler.pick(_categories_for_prompt(prompt), _keywords_from_semantic(semantic), seed)
    refs = []
    seen = set()
    source_refs = explicit_refs if explicit_refs else _prioritize_refs(sampled_refs, semantic)
    max_refs = 3 if explicit_refs else 6
    for ref in source_refs:
        key = str(ref.path).lower()
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)
        if len(refs) >= max_refs:
            break

    palette = _palette_from_refs(refs)
    work = pygame.Surface((768, 768), pygame.SRCALPHA, 32)
    background = pygame.Surface(work.get_size(), pygame.SRCALPHA, 32)
    _draw_background(background, semantic, palette, __import__('random').Random(seed))

    shadow = pygame.Surface(work.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 132), (int(work.get_width() * 0.10), int(work.get_height() * 0.62), int(work.get_width() * 0.80), int(work.get_height() * 0.20)))

    fg_palette = _strong_foreground_palette(palette, semantic.get('subject_kind', ''), semantic.get('object_kind', ''))
    subject = pygame.Surface(work.get_size(), pygame.SRCALPHA, 32)
    draw_subject(subject, semantic, refs, fg_palette, __import__('random').Random(seed + 1))

    obj = pygame.Surface(work.get_size(), pygame.SRCALPHA, 32)
    draw_focus_object(obj, semantic, fg_palette, __import__('random').Random(seed + 2))

    fx = pygame.Surface(work.get_size(), pygame.SRCALPHA, 32)
    draw_fx(fx, semantic, palette, __import__('random').Random(seed + 3))

    final = pygame.Surface(work.get_size(), pygame.SRCALPHA, 32)
    final.blit(background, (0, 0))
    final.blit(shadow, (0, 0))
    final.blit(subject, (0, 0))
    final.blit(obj, (0, 0))
    final.blit(fx, (0, 0))
    _apply_contrast(final)

    layers = {
        'background': pygame.transform.smoothscale(background, (320, 220)).convert_alpha(),
        'subject': pygame.transform.smoothscale(subject, (320, 220)).convert_alpha(),
        'object': pygame.transform.smoothscale(obj, (320, 220)).convert_alpha(),
        'fx': pygame.transform.smoothscale(fx, (320, 220)).convert_alpha(),
        'final': pygame.transform.smoothscale(final, (320, 220)).convert_alpha(),
    }
    meta = {
        'subject_kind': str(semantic.get('subject_kind', '') or ''),
        'object_kind': str(semantic.get('object_kind', '') or ''),
        'environment_kind': str(semantic.get('environment_kind', '') or ''),
        'references': [r.path.name for r in refs[:4]],
        'occupancy_subject': _occupancy_ratio(layers['subject']),
        'occupancy_object': _occupancy_ratio(layers['object']),
        'occupancy_fx': _occupancy_ratio(layers['fx']),
    }
    return meta, layers


def _contact_sheet(card_id: str, layers: dict[str, pygame.Surface]) -> pygame.Surface:
    w, h = 320, 220
    pad = 12
    titles = ['background', 'subject', 'object', 'fx', 'final']
    sheet = pygame.Surface((w * 2 + pad * 3, h * 3 + pad * 4), pygame.SRCALPHA, 32)
    sheet.fill((18, 14, 24, 255))
    font = pygame.font.SysFont('consolas', 18)
    positions = {
        'background': (pad, pad + 18),
        'subject': (pad * 2 + w, pad + 18),
        'object': (pad, pad * 2 + h + 18),
        'fx': (pad * 2 + w, pad * 2 + h + 18),
        'final': (pad + (w // 2), pad * 3 + h * 2 + 18),
    }
    for name in titles:
        x, y = positions[name]
        label = font.render(name, True, (232, 220, 172))
        sheet.blit(label, (x, y - 18))
        sheet.blit(layers[name], (x, y))
        pygame.draw.rect(sheet, (96, 80, 128), (x, y, w, h), 2, border_radius=6)
    title = font.render(card_id, True, (255, 255, 255))
    sheet.blit(title, (pad, 2))
    return sheet


def main() -> int:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    parser = argparse.ArgumentParser(description='Genera preview de capas para cartas ancla.')
    parser.add_argument('--ids', nargs='*', default=DEFAULT_IDS)
    args = parser.parse_args()

    cards = _load_cards()
    pb = PromptBuilder()
    out_dir = project_root() / 'reports' / 'validation' / 'layer_previews'
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = ['status=ok', 'mode=layer_preview', 'ids=' + ','.join(args.ids)]

    for cid in args.ids:
        card = cards[cid]
        entry = pb.build_entry(card)
        meta, layers = _compose_preview(entry['prompt_text'], sum(ord(ch) for ch in cid))
        card_dir = out_dir / cid
        card_dir.mkdir(parents=True, exist_ok=True)
        for name, surf in layers.items():
            pygame.image.save(surf, str(card_dir / f'{name}.png'))
        pygame.image.save(_contact_sheet(cid, layers), str(card_dir / 'contact_sheet.png'))
        lines.append(
            f"{cid}|subject_kind={meta['subject_kind']}|object_kind={meta['object_kind']}|environment_kind={meta['environment_kind']}|refs={','.join(meta['references'])}|occ_subject={meta['occupancy_subject']}|occ_object={meta['occupancy_object']}|occ_fx={meta['occupancy_fx']}"
        )

    report = project_root() / 'reports' / 'validation' / 'layer_preview_report.txt'
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[layer_preview] report={report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
