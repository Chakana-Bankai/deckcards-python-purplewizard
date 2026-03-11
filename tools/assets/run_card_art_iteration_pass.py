from __future__ import annotations

import argparse
import json
from pathlib import Path

import pygame

from game.content.card_art_generator import CardArtGenerator, PromptBuilder
from game.core.paths import project_root
from game.art.scene_engine import semantic_from_prompt, _categories_for_prompt, _keywords_from_semantic, _prioritize_refs, _resolve_explicit_refs
from game.art.reference_sampler import ReferenceSampler
from tools.qa.check_beta_run_flow import run as beta_run_main

ANCHOR_IDS = ["cw_lore_10", "hip_cosmic_warrior_20", "arc_060"]


def _load_all_cards() -> list[dict]:
    root = project_root() / "game" / "data"
    cards = []
    for name in ("cards.json", "cards_hiperboria.json", "cards_arconte.json"):
        path = root / name
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        cards.extend(raw if isinstance(raw, list) else raw.get("cards", []))
    return [c for c in cards if isinstance(c, dict) and c.get("id")]


def run_iteration(ids: list[str]) -> Path:
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    all_cards = _load_all_cards()
    by_id = {str(c.get("id")): c for c in all_cards}
    pb = PromptBuilder()
    gen = CardArtGenerator()
    sampler = ReferenceSampler()

    lines = [
        "status=ok",
        "phase=all",
        "ids=" + ",".join(ids),
    ]

    for cid in ids:
        card = by_id.get(cid)
        if not card:
            lines.append(f"{cid}|missing_card")
            continue
        entry = pb.build_entry(card)
        prompt = str(entry.get("prompt_text", "") or "")
        sem = semantic_from_prompt(prompt)
        explicit_refs = _resolve_explicit_refs(sampler, sem)
        sampled_refs = sampler.pick(_categories_for_prompt(prompt), _keywords_from_semantic(sem), 123)
        refs = []
        seen = set()
        for ref in explicit_refs + _prioritize_refs(sampled_refs, sem):
            key = str(ref.path).lower()
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)
            if len(refs) >= 6:
                break
        res = gen.ensure_art(
            cid,
            list(card.get("tags", []) or []),
            str(card.get("rarity", "common")),
            mode="force_regen",
            family=str(entry.get("family", card.get("role", "") or "")),
            symbol=str(card.get("symbol", "") or ""),
            prompt=prompt,
        )
        out_name = Path(str(res.get("path"))).name
        lines.append(
            f"{cid}|subject_kind={sem.get('subject_kind','')}|object_kind={sem.get('object_kind','')}|environment_kind={sem.get('environment_kind','')}|refs={','.join(r.path.name for r in refs[:4])}|asset={out_name}"
        )

    try:
        payload = beta_run_main()
        lines.append(f"beta_run={str((payload or {}).get('overall', 'UNKNOWN'))}")
    except SystemExit as exc:
        lines.append(f"beta_run=EXIT_{exc.code}")
    except Exception as exc:
        lines.append(f"beta_run=ERROR:{exc}")

    report = project_root() / "reports" / "validation" / "card_art_iteration_full_pass_report.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta el pase completo de iteracion artistica fuera del runtime.")
    parser.add_argument("--ids", nargs="*", default=ANCHOR_IDS)
    args = parser.parse_args()
    report = run_iteration(list(args.ids or ANCHOR_IDS))
    print(f"[card_art_iteration] report={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
