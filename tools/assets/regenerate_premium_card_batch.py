from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from game.content.card_art_generator import CardArtGenerator, export_prompts
from game.core.paths import data_dir, project_root


DEFAULT_BATCH = [
    "chakana_de_luz",
    "fusion_espiritual",
    "ritual_de_la_trama",
    "hip_cosmic_warrior_20",
    "hip_harmony_guardian_20",
    "hip_oracle_of_fate_20",
    "arc_058",
    "arc_059",
    "arc_060",
]


def _load_cards() -> list[dict]:
    cards = []
    for name in ("cards.json", "cards_hiperboria.json", "cards_arconte.json"):
        path = data_dir() / name
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        cards.extend(raw if isinstance(raw, list) else raw.get("cards", []))
    return [c for c in cards if isinstance(c, dict) and c.get("id")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenera un lote premium de cartas fuera del runtime.")
    parser.add_argument("--ids", nargs="*", default=DEFAULT_BATCH)
    args = parser.parse_args()

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    all_cards = _load_cards()
    by_id = {str(c.get("id")): c for c in all_cards}
    chosen = [by_id[cid] for cid in args.ids if cid in by_id]
    export_prompts(all_cards)
    gen = CardArtGenerator()
    written = []
    for card in chosen:
        cid = str(card.get("id"))
        res = gen.ensure_art(
            cid,
            list(card.get("tags", []) or []),
            str(card.get("rarity", "common")),
            mode="force_regen",
            family=str(card.get("role", "") or ""),
            symbol=str(card.get("symbol", "") or ""),
            prompt=(str(card.get("effect_text", "") or "") + " " + str(card.get("lore_text", "") or "")).strip(),
        )
        written.append(f"{cid}={Path(str(res.get('path'))).name}")

    out = project_root() / "reports" / "validation" / "premium_card_batch_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(["status=ok", f"cards={len(written)}", *written]) + "\n", encoding="utf-8")
    print(f"[premium_cards] report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
