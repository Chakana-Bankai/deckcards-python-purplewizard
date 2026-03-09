from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import pygame

from engine.creative_direction import CreativeArtDirector, QualityEvaluator
from game.art.gen_art32 import seed_from_id
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.art.gen_card_art_advanced import generate as generate_advanced
from game.content.card_art_generator import PromptBuilder

ROOT = Path(__file__).resolve().parents[2]
CARDS_PATH = ROOT / "game" / "data" / "cards.json"
OUT_DIR = ROOT / "assets" / "sprites" / "cards"
REPORT = ROOT / "creative_art_master_upgrade_report.txt"


def _card_type(card: dict) -> str:
    tags = {str(t).lower() for t in (card.get("tags") or [])}
    role = str(card.get("role", "")).lower()
    family = str(card.get("family", "")).lower()
    if "attack" in tags or role == "attack" or family in {"crimson_chaos"}:
        return "attack"
    if "block" in tags or "defense" in tags or role == "defense" or family in {"emerald_spirit"}:
        return "defense"
    if "ritual" in tags or role == "ritual" or family in {"violet_arcane"}:
        return "ritual"
    if "draw" in tags or "scry" in tags or "control" in tags or role == "control" or family in {"azure_cosmic"}:
        return "control"
    if str(card.get("rarity", "")).lower() == "legendary":
        return "legendary"
    return "spirit"


def _set_id(card: dict, prompt: str) -> str:
    sid = str(card.get("set") or "").strip().lower()
    if sid:
        return sid
    low = str(prompt or "").lower()
    if "hiperboria" in low or "hiperborea" in low or "hip_" in low:
        return "hiperborea"
    if "archon" in low or "arconte" in low or "void" in low:
        return "archon"
    return "base"


def main() -> int:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))

    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT / "assets" / "archive" / "creative_master_upgrade" / ts
    backup_dir.mkdir(parents=True, exist_ok=True)

    evaluator = QualityEvaluator()
    director = CreativeArtDirector()
    pb = PromptBuilder()

    upgraded = 0
    skipped = 0
    before_scores = []
    after_scores = []

    for card in cards:
        cid = str(card.get("id", "")).strip()
        if not cid:
            continue
        out_path = OUT_DIR / f"{cid}.png"

        before = evaluator.evaluate_art_file(out_path).overall if out_path.exists() else 0.0
        before_scores.append(before)

        # Skip only already-good art to avoid useless churn.
        if out_path.exists() and before >= 0.55:
            after_scores.append(before)
            skipped += 1
            continue

        if out_path.exists():
            shutil.copy2(out_path, backup_dir / out_path.name)

        entry = pb.build_entry(card)
        prompt = str(entry.get("prompt_text", ""))
        ctype = _card_type(card)
        set_id = _set_id(card, prompt)
        rarity = str(card.get("rarity", "common")).lower()
        seed = seed_from_id(cid, GEN_CARD_ART_VERSION)

        def _gen(target_path: Path, use_seed: int) -> dict:
            return generate_advanced(cid, ctype, prompt, use_seed, target_path)

        result = director.evolve(
            card_id=cid,
            set_id=set_id,
            base_seed=seed,
            out_path=out_path,
            generate_fn=_gen,
            threshold=0.70 if rarity == "legendary" else 0.62,
        )

        after = evaluator.evaluate_art_file(out_path).overall if out_path.exists() else 0.0
        after_scores.append(after)

        if after > before:
            upgraded += 1

    avg_before = sum(before_scores) / max(1, len(before_scores))
    avg_after = sum(after_scores) / max(1, len(after_scores))

    lines = [
        "CHAKANA CREATIVE ART MASTER UPGRADE",
        f"generated_at={datetime.now().isoformat(timespec='seconds')}",
        f"cards_total={len(cards)}",
        f"upgraded={upgraded}",
        f"skipped_good={skipped}",
        f"avg_before={avg_before:.3f}",
        f"avg_after={avg_after:.3f}",
        f"backup_dir={backup_dir}",
        "status=PASS" if avg_after >= 0.45 else "status=WARNING",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[creative_art_master] report={REPORT}")
    print(f"[creative_art_master] avg_before={avg_before:.3f} avg_after={avg_after:.3f} upgraded={upgraded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
