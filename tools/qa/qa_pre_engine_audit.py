from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.core.paths import assets_dir, data_dir
from game.core.safe_io import load_json
from game.ui.components.card_renderer import (
    RENDER_CONTEXT_RULES,
    render_card_large,
    render_card_medium,
    render_card_preview,
    render_card_small,
)
from game.ui.components.holographic_oracle import HolographicOracleUI
from game.ui.layout.combat_layout import build_combat_layout
from game.ui.system.icons import ICON_ALIASES, icon_for_effect
from game.ui.system.safety import VIEW_CONTEXT_RULES
from game.ui.system.typography import CONTEXT_FONT_SIZES
from tools.qa_phase9_supervision import _load_sets, run_phase9_report


ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "qa_report_post_combat_polish_full.txt"
OUT_MD = ROOT / "qa_report_post_combat_polish_full.md"
STRUCTURE_AUDIT_MD = ROOT / "docs" / "PROJECT_STRUCTURE_AUDIT.md"
CLASSIFICATION_JSON = ROOT / "docs" / "PROJECT_STRUCTURE_CLASSIFICATION.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        return "n/a"


def _safe_json(path: Path, default):
    try:
        return load_json(path, default=default)
    except Exception:
        return default


def _iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return [p for p in path.rglob("*") if p.is_file()]


def _cards() -> tuple[list[dict], list[dict], list[dict]]:
    base, hip, all_cards = _load_sets()
    return list(base), list(hip), list(all_cards)


def _status(ok: bool, warn: bool = False) -> str:
    if ok and not warn:
        return "PASS"
    if ok and warn:
        return "WARNING"
    return "FAIL"


@dataclass
class Section:
    name: str
    status: str
    summary: str
    details: dict


def build_snapshot(base: list[dict], hip: list[dict], all_cards: list[dict]) -> dict:
    version = _safe_json(data_dir() / "version.json", default={})
    relics = _safe_json(data_dir() / "relics.json", default=[])
    enemies = _safe_json(data_dir() / "enemies" / "enemies_30.json", default=[])
    bosses = _safe_json(data_dir() / "enemies" / "bosses_3.json", default=[])

    codex_entries = 0
    for cp in data_dir().glob("codex*.json"):
        obj = _safe_json(cp, default={})
        if isinstance(obj, list):
            codex_entries += len(obj)
        elif isinstance(obj, dict):
            if isinstance(obj.get("cards"), list):
                codex_entries += len(obj["cards"])
            elif isinstance(obj.get("relics"), list):
                codex_entries += len(obj["relics"])
            elif isinstance(obj.get("sections"), list):
                codex_entries += len(obj["sections"])
            else:
                codex_entries += len(obj)

    generated_roots = [
        assets_dir() / "generated",
        ROOT / "game" / "visual" / "generated",
        ROOT / "game" / "audio" / "generated",
    ]
    curated_roots = [assets_dir() / "curated"]
    return {
        "game_version": str(version.get("version", "n/a")),
        "build_name": str(version.get("build", "n/a")),
        "git_commit_hash": _git_commit(),
        "generated_at": _now_iso(),
        "total_cards": len(all_cards),
        "total_cards_base": len(base),
        "total_cards_hiperboria": len(hip),
        "total_relics": len(relics) if isinstance(relics, list) else 0,
        "total_enemies": len(enemies) if isinstance(enemies, list) else 0,
        "total_bosses": len(bosses) if isinstance(bosses, list) else 0,
        "total_codex_entries": codex_entries,
        "total_generated_assets": sum(len(_iter_files(p)) for p in generated_roots),
        "total_curated_assets": sum(len(_iter_files(p)) for p in curated_roots),
    }


def _dialogue_rows(*objs) -> list[dict]:
    rows = []
    for obj in objs:
        if isinstance(obj, dict):
            for key, val in obj.items():
                if isinstance(val, dict):
                    rows.append({"id": str(val.get("id", key)), "key": key})
                elif isinstance(val, list):
                    rows.append({"id": str(key), "count": len(val)})
    return rows


def _registry_rows() -> dict[str, list[dict]]:
    _base, _hip, all_cards = _cards()
    codex = _safe_json(data_dir() / "codex.json", default={})
    codex_cards = _safe_json(data_dir() / "codex_cards_lore_set1.json", default={})
    codex_hip = _safe_json(data_dir() / "codex_cards_hiperboria.json", default={})
    codex_relics = _safe_json(data_dir() / "codex_relics_lore_set1.json", default={})

    codex_rows = []
    if isinstance(codex, dict):
        for sec in list(codex.get("sections", []) or []):
            if isinstance(sec, dict):
                codex_rows.append({"id": sec.get("id"), "title": sec.get("title", "")})

    civs = []
    civ_file = ROOT / "game" / "content" / "civilizations.py"
    if civ_file.exists():
        text = civ_file.read_text(encoding="utf-8", errors="replace")
        for cid in ("base_world", "hiperborea"):
            if f'"{cid}"' in text:
                civs.append({"id": cid})

    return {
        "cards": all_cards,
        "relics": _safe_json(data_dir() / "relics.json", default=[]),
        "enemies": _safe_json(data_dir() / "enemies" / "enemies_30.json", default=[]),
        "bosses": _safe_json(data_dir() / "enemies" / "bosses_3.json", default=[]),
        "biomes": _safe_json(data_dir() / "biomes.json", default=[]),
        "civilizations_sets": civs,
        "codex_entries": codex_rows
        + list((codex_cards.get("cards", []) if isinstance(codex_cards, dict) else []))
        + list((codex_hip.get("cards", []) if isinstance(codex_hip, dict) else []))
        + list((codex_relics.get("relics", []) if isinstance(codex_relics, dict) else [])),
        "dialogue_scene_entries": _dialogue_rows(
            _safe_json(data_dir() / "lore" / "dialogues.json", default={}),
            _safe_json(data_dir() / "lore" / "dialogues_events.json", default={}),
            _safe_json(data_dir() / "lore" / "dialogues_combat.json", default={}),
            _safe_json(data_dir() / "combat_dialogue.json", default={}),
        ),
    }

def _dialogue_enemy_ref_issues(enemy_ids: set[str]) -> list[str]:
    dcombat = _safe_json(data_dir() / "lore" / "dialogues_combat.json", default={})
    missing = []
    if isinstance(dcombat, dict):
        by_enemy = dcombat.get("by_enemy", {})
        if isinstance(by_enemy, dict):
            for key in by_enemy:
                eid = str(key).strip()
                if eid and eid not in enemy_ids:
                    missing.append(eid)
    return sorted(set(missing))


def audit_content_registry(all_cards: list[dict]) -> Section:
    regs = _registry_rows()
    missing_ids = {}
    duplicate_ids = {}
    for name, rows in regs.items():
        if not isinstance(rows, list):
            rows = []
        ids = [str((r or {}).get("id", "")).strip() for r in rows if isinstance(r, dict)]
        missing_ids[name] = [i for i in ids if not i]
        freq = {}
        for rid in ids:
            if rid:
                freq[rid] = freq.get(rid, 0) + 1
        duplicate_ids[name] = sorted([k for k, v in freq.items() if v > 1])

    card_ids = {str(c.get("id", "")).strip() for c in all_cards if isinstance(c, dict)}
    relic_ids = {str(r.get("id", "")).strip() for r in regs.get("relics", []) if isinstance(r, dict)}
    enemy_ids = {str(e.get("id", "")).strip() for e in regs.get("enemies", []) if isinstance(e, dict)}

    codex_missing_cards = []
    codex_missing_relics = []
    for row in regs.get("codex_entries", []):
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id", "")).strip()
        if not rid:
            continue
        if rid.startswith("hip_") or rid in card_ids:
            if rid not in card_ids:
                codex_missing_cards.append(rid)
        elif rid.startswith("relic_") or rid in {"violet_seal", "chakana_thread"}:
            if rid not in relic_ids:
                codex_missing_relics.append(rid)

    card_art_ids = {str(c.get("art", c.get("artwork", c.get("id", ""))) or c.get("id", "")) for c in all_cards}
    cards_dir = assets_dir() / "sprites" / "cards"
    art_files = [p.stem for p in cards_dir.glob("*.png")] if cards_dir.exists() else []
    unreferenced_assets = sorted([stem for stem in art_files if stem not in card_art_ids])
    refs_not_found = sorted([aid for aid in card_art_ids if aid not in set(art_files)])

    warn = any(
        [
            any(missing_ids.values()),
            any(duplicate_ids.values()),
            codex_missing_cards,
            codex_missing_relics,
            refs_not_found,
        ]
    )
    return Section(
        name="Content Registry",
        status=_status(True, warn=warn),
        summary=(
            f"registries={len(regs)} duplicate_ids={sum(len(v) for v in duplicate_ids.values())} "
            f"missing_ids={sum(len(v) for v in missing_ids.values())}"
        ),
        details={
            "registry_sizes": {k: len(v) if isinstance(v, list) else 0 for k, v in regs.items()},
            "missing_ids": missing_ids,
            "duplicate_ids": duplicate_ids,
            "orphaned_entries": {
                "codex_missing_cards": sorted(set(codex_missing_cards)),
                "codex_missing_relics": sorted(set(codex_missing_relics)),
                "dialogue_enemy_refs_not_found": _dialogue_enemy_ref_issues(enemy_ids),
            },
            "assets_existing_but_not_referenced": unreferenced_assets[:140],
            "references_to_removed_assets": refs_not_found[:140],
        },
    )


def audit_cards(base: list[dict], hip: list[dict], all_cards: list[dict]) -> Section:
    invalid_cards = []
    missing_lore = []
    missing_set = []
    missing_tags = []
    missing_art = []
    effect_icon_issues = []
    name_freq = {}

    for c in all_cards:
        cid = str(c.get("id", "")).strip()
        if not cid:
            invalid_cards.append("missing_id")
            continue
        name = str(c.get("name", c.get("name_key", ""))).strip()
        set_id = str(c.get("set", "")).strip()
        lore = str(c.get("lore", c.get("lore_text", ""))).strip()
        effects = c.get("effects", [])
        if not name or not set_id or not isinstance(effects, list) or not effects:
            invalid_cards.append(cid)
        if not lore:
            missing_lore.append(cid)
        if not set_id:
            missing_set.append(cid)
        if not isinstance(c.get("tags", []), list) or not c.get("tags"):
            missing_tags.append(cid)

        aid = str(c.get("art", c.get("artwork", cid)) or cid)
        if not (assets_dir() / "sprites" / "cards" / f"{aid}.png").exists():
            missing_art.append(cid)

        lname = name.lower()
        name_freq[lname] = name_freq.get(lname, 0) + 1
        for e in effects:
            if not isinstance(e, dict):
                effect_icon_issues.append(f"{cid}:invalid_effect")
                continue
            et = str(e.get("type", "")).strip().lower()
            if not et or icon_for_effect(et) == "unknown":
                effect_icon_issues.append(f"{cid}:{et or 'missing_type'}")

    duplicate_names = sorted([k for k, v in name_freq.items() if v > 1])
    totals_ok = len(all_cards) == 120 and len(base) == 60 and len(hip) == 60
    warn = any([invalid_cards, missing_lore, missing_set, missing_tags, missing_art, effect_icon_issues, duplicate_names])
    return Section(
        name="Cards",
        status=_status(totals_ok, warn=warn and totals_ok),
        summary=f"cards={len(all_cards)} base={len(base)} hiperboria={len(hip)} invalid={len(invalid_cards)}",
        details={
            "expected": {"total": 120, "base": 60, "hiperboria": 60},
            "actual": {"total": len(all_cards), "base": len(base), "hiperboria": len(hip)},
            "invalid_cards": invalid_cards[:140],
            "missing_lore": missing_lore[:140],
            "missing_set_tag": missing_set[:140],
            "missing_tags": missing_tags[:140],
            "missing_art": missing_art[:140],
            "duplicate_names": duplicate_names[:140],
            "effect_mapping_issues": effect_icon_issues[:240],
        },
    )


class _DummyLoc:
    def t(self, text):
        return str(text or "")


class _DummyAssets:
    def sprite(self, _category, _key, size, fallback=(86, 56, 132)):
        w, h = max(8, int(size[0])), max(8, int(size[1]))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((*fallback, 255))
        pygame.draw.rect(surf, (240, 240, 240), surf.get_rect(), 1, border_radius=4)
        return surf


def _dummy_app():
    if not pygame.font.get_init():
        pygame.font.init()
    app = SimpleNamespace()
    app.loc = _DummyLoc()
    app.assets = _DummyAssets()
    app.small_font = pygame.font.Font(None, 22)
    app.tiny_font = pygame.font.Font(None, 18)
    app.big_font = pygame.font.Font(None, 32)
    return app


def audit_card_render_contexts(cards: list[dict]) -> Section:
    contexts = {
        "combat_hand": "hand_view",
        "hover_preview": "hover_view",
        "deck_view": "deck_view",
        "codex_view": "codex_view",
        "shop_view": "shop_view",
        "pack_view": "pack_view",
        "archetype_preview": "archetype_preview",
    }
    app = _dummy_app()
    sample = list(cards[:4]) + [c for c in cards if str(c.get("id", "")).startswith("hip_")][:2]
    failures = []
    warnings = []
    per_context = {}

    for ctx_name, rc in contexts.items():
        ctx_warn = []
        if rc not in RENDER_CONTEXT_RULES:
            ctx_warn.append("missing_card_render_rule")
        if rc not in VIEW_CONTEXT_RULES:
            ctx_warn.append("missing_safety_rule")

        rendered = 0
        for card in sample:
            surf = pygame.Surface((700, 960), pygame.SRCALPHA)
            rect = pygame.Rect(90, 80, 520, 720)
            state = {"app": app, "render_context": rc, "hovered": rc in {"hover_view", "codex_view"}}
            try:
                if rc == "hand_view":
                    render_card_small(surf, rect, card, state=state)
                elif rc in {"hover_view", "codex_view"}:
                    render_card_preview(surf, rect, card, state=state)
                elif rc == "archetype_preview":
                    render_card_medium(surf, rect, card, state=state)
                else:
                    render_card_large(surf, rect, card, state=state)
                rendered += 1
                alpha = pygame.surfarray.array_alpha(surf.subsurface(rect))
                if int(alpha.max()) <= 0:
                    ctx_warn.append(f"transparent_render:{card.get('id')}")
            except Exception as exc:
                failures.append(f"{ctx_name}:{card.get('id')}:{exc}")

        per_context[ctx_name] = {"rendered": rendered, "warnings": sorted(set(ctx_warn))}
        warnings.extend(ctx_warn)

    return Section(
        name="Rendering",
        status=_status(not failures, warn=bool(warnings)),
        summary=f"contexts={len(contexts)} failures={len(failures)} warnings={len(set(warnings))}",
        details={
            "per_context": per_context,
            "render_failures": failures[:140],
            "warnings": sorted(set(warnings))[:240],
        },
    )

def audit_combat_hud() -> Section:
    layout = build_combat_layout(1920, 1080)
    top = layout.enemy_strip.h
    mid = layout.voices_panel.h
    bottom = layout.player_hud.h + layout.hand_area.h
    total = max(1, top + mid + bottom)
    ratios = {
        "top": round(top / total, 3),
        "mid": round(mid / total, 3),
        "bottom": round(bottom / total, 3),
    }
    required = ["damage", "block", "energy", "harmony", "heal", "retain", "rupture", "exhaust", "draw"]
    missing_icons = [k for k in required if icon_for_effect(k) == "unknown"]
    overlap = {
        "hand_vs_actions": layout.hand_area.colliderect(layout.actions_panel),
        "hand_vs_player": layout.hand_area.colliderect(layout.player_hud),
        "enemy_vs_topbar": layout.enemy_strip.colliderect(layout.topbar_rect),
    }
    warn = bool(missing_icons or any(overlap.values()))
    return Section(
        name="Combat HUD",
        status=_status(True, warn=warn),
        summary=f"ratios={ratios['top']}/{ratios['mid']}/{ratios['bottom']} missing_icons={len(missing_icons)}",
        details={"ratios": ratios, "expected": {"top": 0.30, "mid": 0.20, "bottom": 0.50}, "missing_icons": missing_icons, "overlap": overlap},
    )


def audit_hand_layout() -> Section:
    layout = build_combat_layout(1920, 1080)
    hand = layout.hand_area
    card_h = int(hand.h * 0.86)
    card_w = int(card_h * (320 / 460))
    checks = {}
    warnings = []
    for n in (3, 5, 7):
        spacing = max(36, int((hand.w - card_w) / max(1, n - 1)))
        total_w = card_w + (n - 1) * spacing
        left = hand.centerx - total_w // 2
        right = left + total_w
        in_bounds = left >= hand.x and right <= hand.right
        checks[str(n)] = {"spacing": spacing, "left": left, "right": right, "in_bounds": in_bounds}
        if not in_bounds:
            warnings.append(f"fan_out_of_bounds_{n}")
    return Section("Hand Layout", _status(True, warn=bool(warnings)), f"states=3 warnings={len(warnings)}", {"states": checks, "warnings": warnings})


def audit_fonts() -> Section:
    fdir = assets_dir() / "fonts"
    expected = ["chakana_pixel.ttf", "chakana_ui.ttf", "chakana_mono.ttf", "chakana_title.ttf", "chakana_lore.ttf"]
    missing_files = [f for f in expected if not (fdir / f).exists()]
    needed_ctx = ["combat_labels", "hud_numbers", "card_titles", "card_body", "lore_text", "map_labels", "codex_headers", "shop_headers"]
    missing_ctx = [c for c in needed_ctx if c not in CONTEXT_FONT_SIZES]
    warn = bool(missing_files or missing_ctx)
    return Section(
        name="Fonts",
        status=_status(True, warn=warn),
        summary=f"missing_custom_files={len(missing_files)} missing_contexts={len(missing_ctx)}",
        details={
            "font_dir": str(fdir),
            "missing_custom_files": missing_files,
            "fallback_font_count": len(missing_files),
            "registered_contexts": sorted(CONTEXT_FONT_SIZES.keys()),
            "missing_contexts": missing_ctx,
        },
    )


def audit_icons(all_cards: list[dict]) -> Section:
    required = ["damage", "block", "energy", "harmony", "ritual", "heal", "retain", "rupture", "exhaust", "draw", "draw_if"]
    missing_required = [k for k in required if icon_for_effect(k) == "unknown"]
    used = set()
    missing_mappings = []
    for c in all_cards:
        for e in list(c.get("effects", []) or []):
            if isinstance(e, dict):
                et = str(e.get("type", "")).strip().lower()
                if et:
                    used.add(et)
                    if icon_for_effect(et) == "unknown":
                        missing_mappings.append(et)
    dup_aliases = len(ICON_ALIASES) - len(set(ICON_ALIASES.keys()))
    warn = bool(missing_required or missing_mappings or dup_aliases)
    return Section(
        name="Icons",
        status=_status(True, warn=warn),
        summary=f"missing_required={len(missing_required)} missing_mappings={len(set(missing_mappings))}",
        details={
            "required_missing": missing_required,
            "missing_mapping_effect_types": sorted(set(missing_mappings))[:240],
            "duplicate_alias_entries": dup_aliases,
            "used_effect_types": len(used),
        },
    )


def audit_audio() -> Section:
    manifest = _safe_json(data_dir() / "bgm_manifest.json", default={})
    expected = {
        "menu": ["menu"],
        "map": ["map_umbral", "map_kaypacha", "map_hanan", "map_forest"],
        "shop": ["shop"],
        "combat": ["combat_umbral", "combat_kaypacha", "combat_hanan", "combat_forest"],
        "boss": ["boss"],
        "victory": ["victory"],
        "defeat": ["ending", "defeat"],
    }
    active = {}
    missing_ctx = []
    stale_manifest = []
    for ctx, keys in expected.items():
        key = next((k for k in keys if isinstance(manifest, dict) and k in manifest), None)
        if not key:
            missing_ctx.append(ctx)
            continue
        row = manifest.get(key, {})
        variants = list((row or {}).get("variants", []) or [])
        active[ctx] = {"track_key": key, "file": variants[0] if variants else ""}
        for rel in variants:
            if not (assets_dir() / rel).exists():
                stale_manifest.append(rel)

    gen_files = _iter_files(ROOT / "game" / "audio" / "generated")
    freq = {}
    for p in gen_files:
        freq[p.name] = freq.get(p.name, 0) + 1
    dup_files = [k for k, v in freq.items() if v > 1]

    warn = bool(missing_ctx or stale_manifest or dup_files)
    return Section(
        name="Audio",
        status=_status(True, warn=warn),
        summary=f"contexts_missing={len(missing_ctx)} stale_manifest_entries={len(stale_manifest)}",
        details={
            "active_track_by_context": active,
            "missing_contexts": missing_ctx,
            "cache_anomalies": {"stale_manifest_entries": stale_manifest[:120], "duplicate_generated_files": dup_files[:120]},
            "whistle_artifact_check": "manual_review_required",
        },
    )


def audit_scenes() -> Section:
    required_files = [
        ROOT / "game" / "ui" / "screens" / "studio_intro.py",
        ROOT / "game" / "ui" / "screens" / "intro.py",
        ROOT / "game" / "ui" / "screens" / "scene_fusion.py",
        ROOT / "game" / "ui" / "screens" / "pacha_transition.py",
    ]
    missing_files = [str(p) for p in required_files if not p.exists()]
    avatar_files = [
        assets_dir() / "curated" / "avatars" / "chakana_mage_master_concept.png",
        assets_dir() / "curated" / "avatars" / "chakana_mage_master_portrait.png",
        assets_dir() / "curated" / "avatars" / "chakana_mage_master_hologram.png",
    ]
    missing_avatars = [str(p.relative_to(ROOT)) for p in avatar_files if not p.exists()]
    lore_files = [
        data_dir() / "lore" / "dialogues.json",
        data_dir() / "lore" / "dialogues_events.json",
        data_dir() / "lore" / "dialogues_combat.json",
    ]
    missing_dialogues = [str(p.relative_to(ROOT)) for p in lore_files if not p.exists()]
    warn = bool(missing_files or missing_avatars or missing_dialogues)
    return Section(
        name="Scenes",
        status=_status(True, warn=warn),
        summary=f"missing_scene_files={len(missing_files)} missing_portrait_assets={len(missing_avatars)}",
        details={
            "missing_scene_files": missing_files,
            "missing_portrait_assets": missing_avatars,
            "missing_dialogue_files": missing_dialogues,
            "text_bounds_check": "wrapped dialogue blocks present; keep manual visual verification",
        },
    )


def audit_codex() -> Section:
    codex_py = ROOT / "game" / "ui" / "screens" / "codex.py"
    text = codex_py.read_text(encoding="utf-8", errors="replace") if codex_py.exists() else ""
    expected_tabs = ["base", "hiperborea", "relics", "enemies", "lore"]
    missing_tabs = [t for t in expected_tabs if t not in text.lower()]

    c_base = _safe_json(data_dir() / "codex_cards_lore_set1.json", default={})
    c_hip = _safe_json(data_dir() / "codex_cards_hiperboria.json", default={})
    c_rel = _safe_json(data_dir() / "codex_relics_lore_set1.json", default={})
    counts = {
        "base_cards": len((c_base.get("cards", []) if isinstance(c_base, dict) else [])),
        "hiperboria_cards": len((c_hip.get("cards", []) if isinstance(c_hip, dict) else [])),
        "relics": len((c_rel.get("relics", []) if isinstance(c_rel, dict) else [])),
    }
    empty_groups = [k for k, v in counts.items() if int(v) <= 0]
    warn = bool(missing_tabs or empty_groups)
    return Section("Codex", _status(True, warn=warn), f"missing_tabs={len(missing_tabs)} empty_groups={len(empty_groups)}", {"missing_tabs": missing_tabs, "group_counts": counts, "empty_groups": empty_groups})

def _bench(label: str, fn, loops: int = 80) -> dict:
    times = []
    for _ in range(loops):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
    return {
        "label": label,
        "avg_ms": round(statistics.mean(times), 3),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95) - 1], 3),
        "max_ms": round(max(times), 3),
    }


def audit_performance(all_cards: list[dict]) -> Section:
    app = _dummy_app()
    card = (all_cards or [{}])[0]
    surf = pygame.Surface((820, 1020), pygame.SRCALPHA)
    rect = pygame.Rect(150, 110, 520, 720)

    def card_render():
        render_card_medium(surf, rect, card, state={"app": app, "render_context": "combat_preview"})

    def hover_render():
        render_card_large(surf, rect, card, state={"app": app, "render_context": "hover_view", "hovered": True})

    def codex_preview():
        render_card_preview(surf, rect, card, state={"app": app, "render_context": "codex_view", "hovered": True})

    def combat_hud_render():
        l = build_combat_layout(1920, 1080)
        panel = pygame.Surface((l.enemy_strip.w, l.enemy_strip.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (18, 18, 24), panel.get_rect(), border_radius=14)
        for i, k in enumerate(("damage", "block", "energy", "harmony", "draw", "rupture")):
            icon = icon_for_effect(k)
            panel.blit(app.tiny_font.render(icon, True, (230, 230, 240)), (14 + i * 60, 18))

    holo = HolographicOracleUI()
    holo.show("El pulso de la Chakana responde.", trigger="run_start", speaker="chakana")
    screen = pygame.Surface((1920, 1080), pygame.SRCALPHA)

    def scene_render():
        holo.render(screen, app)

    benches = [
        _bench("card_render", card_render),
        _bench("hover_render", hover_render),
        _bench("combat_hud_render", combat_hud_render),
        _bench("codex_card_preview", codex_preview),
        _bench("scene_hologram_render", scene_render),
    ]
    heavy = [b for b in benches if b["avg_ms"] > 5.0]
    return Section("Performance", _status(True, warn=bool(heavy)), f"benchmarks={len(benches)} heavy_contexts={len(heavy)}", {"benchmarks_ms": benches, "heavy_contexts": heavy})


def build_classification() -> dict:
    rows = []
    for p in sorted((ROOT / "game").rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if "/__pycache__/" in rel or rel.endswith(".pyc"):
            continue
        cat = "game_specific"
        if rel.startswith("game/core/") or rel.startswith("game/combat/"):
            cat = "engine_candidate"
        elif rel.startswith("game/audio/") or rel.startswith("game/visual/"):
            cat = "engine_candidate"
        elif rel.startswith("game/ui/system/") or rel.startswith("game/ui/layout/"):
            cat = "engine_candidate"
        elif "/generated/" in rel:
            cat = "generated_asset"
        elif "/curated/" in rel:
            cat = "curated_asset"
        elif "/legacy/" in rel or "/deprecated/" in rel:
            cat = "legacy_or_deprecated"
        rows.append({"path": rel, "category": cat})

    counts = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    return {"generated_at": _now_iso(), "counts": counts, "files": rows}


def write_structure_audit_doc(classification: dict):
    counts = classification.get("counts", {})
    lines = [
        "# Project Structure Audit",
        "",
        f"- Generated: `{_now_iso()}`",
        f"- Root: `{ROOT}`",
        "",
        "## Domain Snapshot",
    ]
    for d in ["core", "combat", "ui", "visual", "audio", "narrative", "content", "tools"]:
        exists = (ROOT / "game" / d).exists() or (ROOT / d).exists()
        lines.append(f"- `{d}`: {'present' if exists else 'missing'}")
    lines.extend([
        "",
        "## Classification Counts",
    ])
    for k in sorted(counts):
        lines.append(f"- `{k}`: {counts[k]}")
    lines.extend([
        "",
        "## Canonical Ownership",
        "- Card renderer canonical path: `game/ui/components/card_renderer.py`",
        "- Audio ownership: `game/audio/*` + `game/data/bgm_manifest.json`",
        "- Portrait pipeline ownership: `game/visual/portrait_pipeline.py`",
        "- Curated avatar root: `game/assets/curated/avatars/`",
        "",
        "## Safe Import Shim Strategy",
        "- Keep wrapper modules on old paths if files move in future extraction passes.",
        "- Migrate low-risk utility modules first; defer gameplay-critical modules.",
        "",
        "## Asset Structure Prep",
        "- Current roots: `game/assets/curated`, `game/assets/generated`, `game/visual/generated`, `game/audio/generated`.",
        "- Target extraction structure: `assets/curated`, `assets/generated`, `assets/fallback`, `assets/deprecated`.",
        "- This pass is non-destructive: no broad asset moves or deletions.",
        "",
    ])
    STRUCTURE_AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    STRUCTURE_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def section_from_phase9(phase9: dict) -> Section:
    warn = any([
        int(phase9.get("invalid_cards", 0) or 0) > 0,
        int(phase9.get("relic_errors", 0) or 0) > 0,
        int(phase9.get("art_failures", 0) or 0) > 0,
        int(phase9.get("missing_kpi_icons", 0) or 0) > 0,
        int(phase9.get("deck_check_rc", 0) or 0) != 0,
    ])
    return Section(
        name="Baseline QA",
        status=_status(True, warn=warn),
        summary=(
            f"cards={phase9.get('cards_checked_total', 0)} avg_turns_battle={phase9.get('avg_turns_battle', 0)} "
            f"avg_turns_boss={phase9.get('avg_turns_boss', 0)} boss_win_rate={phase9.get('boss_win_rate', 0)}"
        ),
        details=phase9,
    )


def _risk_summary(sections: list[Section]) -> dict:
    p1, p2, p3 = [], [], []
    for sec in sections:
        line = f"{sec.name}: {sec.summary}"
        if sec.status == "FAIL":
            p1.append(line)
        elif sec.status == "WARNING":
            if sec.name in {"Cards", "Content Registry", "Combat HUD", "Audio", "Scenes"}:
                p2.append(line)
            else:
                p3.append(line)
    return {"priority_1_runtime": p1, "priority_2_visual_integrity": p2, "priority_3_maintainability": p3}


def _next_actions(sections: list[Section]) -> list[str]:
    name = {s.name: s for s in sections}
    rec = []
    if name.get("Fonts") and name["Fonts"].status != "PASS":
        rec.append("font pipeline consolidation (custom files + context mapping).")
    if name.get("Scenes") and name["Scenes"].status != "PASS":
        rec.append("master avatar art pass (curated concept/portrait/hologram).")
    if name.get("Rendering") and name["Rendering"].status != "PASS":
        rec.append("card renderer context cleanup (overflow + footer safety).")
    if name.get("Codex") and name["Codex"].status != "PASS":
        rec.append("codex tab/content binding pass.")
    if name.get("Audio") and name["Audio"].status != "PASS":
        rec.append("audio cache/manifest cleanup and context track verification.")
    if not rec:
        rec.append("no blockers detected; proceed to extraction planning pass.")
    return rec


def _render_section_text(sec: Section) -> list[str]:
    lines = [f"[{sec.status}] {sec.name}", f"  {sec.summary}"]
    for line in json.dumps(sec.details, ensure_ascii=False, indent=2).splitlines()[:180]:
        lines.append(f"  {line}")
    lines.append("")
    return lines


def _render_section_md(sec: Section) -> list[str]:
    return [f"## {sec.name} — {sec.status}", "", sec.summary, "", "```json", json.dumps(sec.details, ensure_ascii=False, indent=2), "```", ""]


def generate_reports() -> tuple[Path, Path]:
    pygame.init()
    base, hip, all_cards = _cards()
    snapshot = build_snapshot(base, hip, all_cards)
    phase9 = run_phase9_report()

    sections = [
        section_from_phase9(phase9),
        audit_content_registry(all_cards),
        audit_cards(base, hip, all_cards),
        audit_card_render_contexts(all_cards),
        audit_combat_hud(),
        audit_hand_layout(),
        audit_fonts(),
        audit_icons(all_cards),
        audit_audio(),
        audit_scenes(),
        audit_codex(),
        audit_performance(all_cards),
    ]

    overall = "FAIL" if any(s.status == "FAIL" for s in sections) else "WARNING" if any(s.status == "WARNING" for s in sections) else "PASS"
    risks = _risk_summary(sections)
    actions = _next_actions(sections)

    txt = [
        "CHAKANA PRE-ENGINE QA AUDITOR + SAFE RESTRUCTURE PASS",
        "=" * 68,
        "",
        "Build Snapshot",
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        "",
        f"Overall Status: {overall}",
        "",
    ]
    for sec in sections:
        txt.extend(_render_section_text(sec))
    txt.extend(["Risk Summary", json.dumps(risks, ensure_ascii=False, indent=2), "", "Recommended Next Actions"])
    for i, item in enumerate(actions, start=1):
        txt.append(f"{i}. {item}")

    md = ["# QA Report Post Combat Polish (Full)", "", f"- Overall Status: **{overall}**", "", "## Build Snapshot", "```json", json.dumps(snapshot, ensure_ascii=False, indent=2), "```", ""]
    for sec in sections:
        md.extend(_render_section_md(sec))
    md.extend(["## Risks", "```json", json.dumps(risks, ensure_ascii=False, indent=2), "```", "", "## Recommended Next Actions"])
    for i, item in enumerate(actions, start=1):
        md.append(f"{i}. {item}")

    OUT_TXT.write_text("\n".join(txt) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    classification = build_classification()
    CLASSIFICATION_JSON.write_text(json.dumps(classification, ensure_ascii=False, indent=2), encoding="utf-8")
    write_structure_audit_doc(classification)

    return OUT_TXT, OUT_MD


def main() -> int:
    txt, md = generate_reports()
    print(f"[qa_pre_engine] report_txt={txt}")
    print(f"[qa_pre_engine] report_md={md}")
    print(f"[qa_pre_engine] structure_audit={STRUCTURE_AUDIT_MD}")
    print(f"[qa_pre_engine] classification={CLASSIFICATION_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
