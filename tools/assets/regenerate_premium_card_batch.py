from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from game.art.gen_art32 import seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.art.gen_card_art_advanced import generate as generate_single_pass
from game.content.card_art_generator import CardArtGenerator, PromptBuilder, export_prompts
from game.core.paths import assets_dir, data_dir, project_root

DEFAULT_BATCH = [
    "BASE-SOLAR-SKILL-CHAKANA_DE_LUZ",
    "BASE-GUIDE-GUARD-FUSION_ESPIRITUAL",
    "BASE-ORACLE-RITUAL-RITUAL_DE_LA_TRAMA",
    "HYP-SOLAR-SKILL-GUERRERO_ASTRAL_DE_HIPERBOREA_XX",
    "HYP-GUIDE-RITUAL-GUARDIAN_DEL_VELO_POLAR_XX",
    "HYP-ORACLE-RITUAL-ORACULO_DEL_HORIZONTE_BOREAL_XX",
    "ARC-ARCHON-SKILL-ARCANO_DEL_VACIO_34",
    "ARC-ARCHON-RITUAL-ARCANO_DEL_VACIO_39",
    "ARC-ARCHON-SKILL-ARCANO_DEL_VACIO_38",
]

BATCH_PRESETS = {
    "starter_showcase": [
        "BASE-SOLAR-SKILL-CHAKANA_DE_LUZ",
        "BASE-SOLAR-ATTACK-ESTALLIDO_ARCANO",
        "BASE-GUIDE-GUARD-CAMPO_PROTECTOR",
        "BASE-ORACLE-RITUAL-RITUAL_DE_LA_TRAMA",
    ],
    "hiperboria_showcase": [
        "HYP-SOLAR-SKILL-GUERRERO_ASTRAL_DE_HIPERBOREA_XX",
        "HYP-GUIDE-RITUAL-GUARDIAN_DEL_VELO_POLAR_XX",
        "HYP-ORACLE-RITUAL-ORACULO_DEL_HORIZONTE_BOREAL_XX",
    ],
    "archon_showcase": [
        "ARC-ARCHON-ATTACK-ARCANO_DEL_VACIO_01",
        "ARC-ARCHON-RITUAL-ARCANO_DEL_VACIO_03",
        "ARC-ARCHON-GUARD-ARCANO_DEL_VACIO_04",
        "ARC-ARCHON-SKILL-ARCANO_DEL_VACIO_02",
    ],
}

LAYER_STANDARD = [
    "background_base",
    "environment",
    "subject_character",
    "focus_object",
    "magic_effects",
    "integration_depth_pass",
]


def _load_cards() -> list[dict]:
    cards = []
    for name in ("cards.json", "cards_hiperboria.json", "cards_arconte.json"):
        path = data_dir() / name
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        cards.extend(raw if isinstance(raw, list) else raw.get("cards", []))
    return [c for c in cards if isinstance(c, dict) and c.get("id")]


def _write_manifest_entry(card_id: str, mode: str) -> None:
    manifest_path = data_dir() / "art_manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    items = payload.get("items")
    if not isinstance(items, dict):
        items = {}
        payload["items"] = items
    items[card_id] = {
        "path": f"game/assets/sprites/cards/{card_id}.png",
        "mode": mode,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _pick_cards(all_cards: list[dict], args: argparse.Namespace) -> list[dict]:
    by_id = {str(c.get("id")): c for c in all_cards}
    if args.all:
        chosen = list(all_cards)
    elif args.ids:
        chosen = [by_id[cid] for cid in args.ids if cid in by_id]
    else:
        chosen = [by_id[cid] for cid in BATCH_PRESETS.get(args.batch, DEFAULT_BATCH) if cid in by_id]

    if args.set:
        target_set = str(args.set).strip().lower()
        chosen = [c for c in chosen if str(c.get("set", "")).strip().lower() == target_set]
    if args.family:
        target_family = str(args.family).strip().lower()
        pb = PromptBuilder()
        chosen = [c for c in chosen if str(pb.family_for(c)).strip().lower() == target_family]
    if args.offset:
        chosen = chosen[args.offset :]
    if args.limit is not None:
        chosen = chosen[: args.limit]
    return chosen


def _render_card(card: dict, pb: PromptBuilder, engine: str) -> dict:
    cid = str(card.get("id"))
    entry = pb.build_entry(card)
    prompt = str(entry.get("prompt_text", "") or "")
    family = str(entry.get("family", card.get("role", "") or "spirit"))
    out_path = assets_dir() / "sprites" / "cards" / f"{cid}.png"

    if engine == "creative_director":
        gen = CardArtGenerator()
        result = gen.ensure_art(
            cid,
            list(card.get("tags", []) or []),
            str(card.get("rarity", "common")),
            mode="force_regen",
            family=family,
            symbol=str(card.get("symbol", "") or ""),
            prompt=prompt,
        )
    else:
        result = generate_single_pass(
            cid,
            family,
            prompt,
            seed_from_id(cid, GEN_CARD_ART_VERSION),
            out_path,
        )

    result = dict(result or {})
    result["path"] = str(out_path)
    result["family"] = family
    result["references"] = list(entry.get("reference_cues", []) or [])
    _write_manifest_entry(cid, engine)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenera arte de cartas por templates fuera del runtime.")
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--batch", choices=sorted(BATCH_PRESETS.keys()), default="starter_showcase")
    parser.add_argument("--all", action="store_true", help="Regenera todas las cartas del pool cargado.")
    parser.add_argument("--set", choices=["base", "hiperboria", "hiperborea", "arconte", "archon"], default=None)
    parser.add_argument("--family", choices=["attack", "defense", "control", "ritual", "spirit"], default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--engine", choices=["direct_single_pass", "creative_director"], default="direct_single_pass")
    args = parser.parse_args()

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)

    all_cards = _load_cards()
    export_prompts(all_cards)
    chosen = _pick_cards(all_cards, args)
    pb = PromptBuilder()
    written = []
    for card in chosen:
        cid = str(card.get("id"))
        res = _render_card(card, pb, args.engine)
        refs = ",".join(list(res.get("references", []))[:3])
        written.append(
            f"{cid}|engine={args.engine}|generator={res.get('generator_used', 'unknown')}|family={res.get('family', '')}|refs={refs}"
        )

    out = project_root() / "reports" / "validation" / "premium_card_batch_report.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "status=ok",
        f"engine={args.engine}",
        f"batch={'all_cards' if args.all else args.batch}",
        f"cards={len(written)}",
        "layer_standard=" + ",".join(LAYER_STANDARD),
        "composition_rule=background+environment+subject+object+effects+integration",
        *written,
    ]
    out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"[premium_cards] report={out}")
    print(f"[premium_cards] cards={len(written)} engine={args.engine}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
