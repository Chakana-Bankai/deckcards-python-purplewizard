from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path

from game.core.paths import assets_dir, data_dir
from game.core.safe_io import load_json
from game.ui.system.icons import icon_for_effect
from game.ui.system.typography import CONTEXT_FONT_SIZES
from tools.qa_phase9_supervision import _load_sets, run_phase9_report

ROOT = Path(__file__).resolve().parents[1]

OUT_QA_TXT = ROOT / "qa_report_visual_system_normalization.txt"
OUT_QA_MD = ROOT / "qa_report_visual_system_normalization.md"
OUT_CONTENT = ROOT / "content_generation_supervision_report.txt"
OUT_ASSETS = ROOT / "asset_classification_report.txt"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _score_legibility() -> dict:
    required = {
        "combat_title",
        "combat_label",
        "combat_value",
        "card_title",
        "card_type",
        "card_effect",
        "card_lore",
        "card_footer",
        "codex_header",
        "map_label",
        "shop_header",
    }
    available = set(CONTEXT_FONT_SIZES.keys())
    miss = sorted(required - available)
    score = max(0, 100 - len(miss) * 8)
    return {"score": score, "missing_contexts": miss, "available_contexts": sorted(available)}


def _score_icon_visibility(cards: list[dict]) -> dict:
    required = ["damage", "block", "heal", "draw", "retain", "energy", "ritual", "harmony", "rupture", "exhaust"]
    miss_required = [k for k in required if icon_for_effect(k) == "unknown"]
    used_missing = set()
    for c in cards:
        for e in list(c.get("effects", []) or []):
            if isinstance(e, dict):
                et = str(e.get("type", "")).strip().lower()
                if et and icon_for_effect(et) == "unknown":
                    used_missing.add(et)
    score = max(0, 100 - len(miss_required) * 10 - len(used_missing) * 2)
    return {
        "score": score,
        "missing_required_icons": miss_required,
        "missing_used_effect_icons": sorted(used_missing),
    }


def _hiperborea_visibility(base: list[dict], hip: list[dict]) -> dict:
    shop_source = list(load_json(data_dir() / "cards_hiperboria.json", default={}).get("cards", []) or [])
    codex_hip = load_json(data_dir() / "codex_cards_hiperboria.json", default={})
    codex_hip_cards = list(codex_hip.get("cards", []) or []) if isinstance(codex_hip, dict) else []

    shop_hip_ids = {str(c.get("id", "")) for c in shop_source if isinstance(c, dict)}
    codex_hip_ids = {str(c.get("id", "")) for c in codex_hip_cards if isinstance(c, dict)}
    data_hip_ids = {str(c.get("id", "")) for c in hip if isinstance(c, dict)}

    missing_in_codex = sorted(data_hip_ids - codex_hip_ids)
    missing_in_data = sorted(codex_hip_ids - data_hip_ids)
    shop_coverage = len(shop_hip_ids & data_hip_ids)

    return {
        "base_cards": len(base),
        "hiperboria_cards": len(hip),
        "codex_hiperboria_cards": len(codex_hip_ids),
        "shop_hiperboria_candidates": shop_coverage,
        "missing_in_codex": missing_in_codex[:60],
        "codex_orphans": missing_in_data[:60],
    }


def _asset_classification() -> dict:
    roots = {
        "curated": assets_dir() / "curated",
        "generated": assets_dir() / "generated",
        "fallback": assets_dir() / "fallback",
        "deprecated": assets_dir() / "deprecated",
        "visual_generated": ROOT / "game" / "visual" / "generated",
        "audio_generated": ROOT / "game" / "audio" / "generated",
    }
    counts = {}
    for key, path in roots.items():
        if path.exists():
            counts[key] = len([p for p in path.rglob("*") if p.is_file()])
        else:
            counts[key] = 0

    card_dir = assets_dir() / "sprites" / "cards"
    file_sizes = []
    if card_dir.exists():
        for p in card_dir.glob("*.png"):
            file_sizes.append(p.stat().st_size)
    near_dupe_risk = 0
    if file_sizes:
        avg = statistics.mean(file_sizes)
        near_dupe_risk = len([s for s in file_sizes if abs(s - avg) / max(1.0, avg) < 0.02])

    return {
        "counts": counts,
        "card_sprite_count": len(file_sizes),
        "near_duplicate_size_risk": near_dupe_risk,
    }


def _content_generation_supervision(cards: list[dict]) -> dict:
    art_manifest = load_json(data_dir() / "art_manifest_cards.json", default={})
    bgm_manifest = load_json(data_dir() / "bgm_manifest.json", default={})

    families = {}
    for c in cards:
        fam = str(c.get("archetype", c.get("family", "unknown"))).lower()
        families[fam] = families.get(fam, 0) + 1

    motifs = set()
    for c in cards:
        for t in list(c.get("tags", []) or []):
            motifs.add(str(t).lower())

    art_items = {}
    if isinstance(art_manifest, dict):
        art_items = art_manifest.get("items", {}) if isinstance(art_manifest.get("items", {}), dict) else {}
    art_coverage = len(art_items)

    audio_contexts = sorted(list(bgm_manifest.keys())) if isinstance(bgm_manifest, dict) else []
    audio_variants = 0
    for _k, row in (bgm_manifest.items() if isinstance(bgm_manifest, dict) else []):
        if isinstance(row, dict):
            audio_variants += len(list(row.get("variants", []) or []))

    diversity_score = max(0, min(100, int(len(motifs) * 2 + len(families) * 8 + min(audio_variants, 40))))
    return {
        "card_family_distribution": families,
        "tag_diversity": len(motifs),
        "art_manifest_items": art_coverage,
        "audio_contexts": audio_contexts,
        "audio_variants": audio_variants,
        "procedural_diversity_score": diversity_score,
    }


def generate_reports() -> int:
    version = load_json(data_dir() / "version.json", default={})
    base, hip, cards = _load_sets()
    phase9 = run_phase9_report()

    legibility = _score_legibility()
    icons = _score_icon_visibility(cards)
    hip_vis = _hiperborea_visibility(base, hip)
    assets = _asset_classification()
    supervision = _content_generation_supervision(cards)

    status = "PASS"
    if legibility["missing_contexts"] or icons["missing_required_icons"]:
        status = "WARNING"

    qa_payload = {
        "generated_at": _now(),
        "version": version.get("version", "n/a"),
        "build": version.get("build", "n/a"),
        "status": status,
        "legibility": legibility,
        "icon_visibility": icons,
        "hiperborea_visibility": hip_vis,
        "baseline_phase9": {
            "avg_turns_battle": phase9.get("avg_turns_battle", 0),
            "avg_turns_boss": phase9.get("avg_turns_boss", 0),
            "missing_kpi_icons": phase9.get("missing_kpi_icons", 0),
            "art_failures": phase9.get("art_failures", 0),
        },
    }

    qa_txt = [
        "VISUAL SYSTEM NORMALIZATION QA REPORT",
        "=" * 46,
        json.dumps(qa_payload, ensure_ascii=False, indent=2),
    ]
    qa_md = [
        "# Visual System Normalization QA Report",
        "",
        f"- Status: **{status}**",
        "- Generated: " + _now(),
        "",
        "```json",
        json.dumps(qa_payload, ensure_ascii=False, indent=2),
        "```",
    ]

    content_txt = {
        "generated_at": _now(),
        "version": version.get("version", "n/a"),
        "supervision": supervision,
        "notes": [
            "No destructive cleanup applied in this pass.",
            "Diversity score is a heuristic for supervision, not gameplay quality.",
            "Use this report to prioritize curated replacements and generator tuning.",
        ],
    }

    asset_txt = {
        "generated_at": _now(),
        "version": version.get("version", "n/a"),
        "asset_classification": assets,
        "policy": {
            "curated_priority": True,
            "generated_as_cache": True,
            "fallback_safe": True,
            "aggressive_delete": False,
        },
    }

    OUT_QA_TXT.write_text("\n".join(qa_txt) + "\n", encoding="utf-8")
    OUT_QA_MD.write_text("\n".join(qa_md) + "\n", encoding="utf-8")
    OUT_CONTENT.write_text(json.dumps(content_txt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ASSETS.write_text(json.dumps(asset_txt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[qa_visual_norm] txt={OUT_QA_TXT.name}")
    print(f"[qa_visual_norm] md={OUT_QA_MD.name}")
    print(f"[qa_visual_norm] content={OUT_CONTENT.name}")
    print(f"[qa_visual_norm] assets={OUT_ASSETS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(generate_reports())
