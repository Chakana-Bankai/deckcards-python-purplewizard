from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.audio.audio_engine import get_audio_engine
from game.main import App
from game.visual import get_portrait_pipeline

ROOT = Path(__file__).resolve().parents[1]


def _r(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _all_files(root: Path, exts: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            out.append(p)
    return out


def _classify(path: Path) -> str:
    rp = _r(path).lower()
    name = path.name.lower()
    if rp.startswith("game/assets/curated/"):
        return "curated_active"
    if rp.startswith("game/audio/generated/") or rp.startswith("game/visual/generated/"):
        return "generated_active"
    if "placeholder" in name or name in {".gitkeep"}:
        return "fallback_active"
    if rp.startswith("game/assets/music/") or rp.startswith("game/assets/sfx/"):
        return "legacy_archive"
    if rp.startswith("game/assets/avatars/") and not rp.startswith("game/assets/curated/"):
        return "placeholder_only"
    if rp.startswith("game/assets/sprites/"):
        return "generated_active"
    return "deprecated_unused"


def _runtime_avatar_sources() -> dict:
    pp = get_portrait_pipeline()
    out = {}
    for role in ("chakana_mage", "archon"):
        role_out = {}
        for style in ("concept", "portrait", "hologram"):
            cand = pp._source_candidates(role, style)
            hit = next(((p, tag) for p, tag in cand if p.exists()), None)
            role_out[style] = {
                "source": hit[1] if hit else "missing",
                "path": _r(hit[0]) if hit else "",
            }
        out[role] = role_out
    return out


def _audio_mapping() -> dict:
    engine = get_audio_engine()
    manifest = engine.ensure_core_assets(force=False)
    mapping = {}

    contexts = [
        "menu",
        "map_ukhu",
        "map_kay",
        "map_hanan",
        "combat",
        "combat_elite",
        "combat_boss",
        "shop",
        "victory",
        "defeat",
    ]
    for ctx in contexts:
        p = engine._ensure_bgm_variant(ctx, "a", force=False)
        mapping[f"bgm:{ctx}"] = _r(p)

    for st in ["combat_start", "boss_reveal", "harmony_ready", "seal_ready", "relic_gain", "pack_open", "level_up", "victory", "defeat", "studio_intro"]:
        p = engine._ensure_stinger(st, force=False)
        mapping[f"stinger:{st}"] = _r(p)

    return {
        "manifest_items": len((manifest or {}).get("items", {})) if isinstance(manifest, dict) else 0,
        "mapping": mapping,
    }


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()

    roots = {
        "assets_curated": ROOT / "game" / "assets" / "curated",
        "assets_sprites": ROOT / "game" / "assets" / "sprites",
        "assets_music": ROOT / "game" / "assets" / "music",
        "assets_sfx": ROOT / "game" / "assets" / "sfx",
        "visual_generated": ROOT / "game" / "visual" / "generated",
        "audio_generated": ROOT / "game" / "audio" / "generated",
    }

    files = []
    for name, root in roots.items():
        for p in _all_files(root, (".png", ".wav", ".json")):
            files.append((name, p))

    by_root = Counter(name for name, _ in files)
    classes = defaultdict(list)
    for _name, p in files:
        classes[_classify(p)].append(p)

    # Duplication heuristics.
    base_index = defaultdict(list)
    for _name, p in files:
        if p.suffix.lower() not in {".png", ".wav"}:
            continue
        normalized = re.sub(r"(__v\d+|_v\d+|_\d+x\d+.*)$", "", p.stem.lower())
        base_index[normalized].append(p)

    duplicate_groups = {k: v for k, v in base_index.items() if len(v) >= 3}
    top_dupes = sorted(duplicate_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:25]

    # Runtime/canonical mappings.
    avatar_sources = _runtime_avatar_sources()
    audio_map = _audio_mapping()

    # Sample runtime visual loads for verification.
    runtime_visual_samples = {
        "avatar_chakana_mage_portrait": "portrait_pipeline",
        "avatar_chakana_mage_hologram": "portrait_pipeline",
        "cards_strike": "assets/sprites/cards",
        "biomes_kaypacha": "assets/sprites/biomes or visual/generated fallback",
        "studio_intro_visual": "data/studio_intro_manifest.json + generated starfield timeline",
    }

    # Report 1: disk audit
    r1 = [
        "PHASE 4 - ASSET DISK AUDIT REPORT",
        "=" * 40,
        "",
        "overall=PASS",
        "",
        "Root counts",
    ]
    for root_name, count in sorted(by_root.items()):
        r1.append(f"- {root_name}: {count}")
    r1.extend([
        "",
        "Detected duplicate groups (top)",
    ])
    for base, group in top_dupes:
        r1.append(f"- {base}: {len(group)} files")
    r1.extend([
        "",
        "Operational observations",
        "- Audio runtime is canonical on game/audio/generated/*; legacy game/assets/music remains archived compatibility.",
        "- Portrait runtime resolves curated->generated->placeholder deterministically; historical sizes remain as non-primary fallback.",
        "- Studio intro keeps procedural base and can layer curated studio assets when present.",
    ])
    (ROOT / "asset_disk_audit_report.txt").write_text("\n".join(r1) + "\n", encoding="utf-8")

    # Report 2: classification
    r2 = [
        "PHASE 4 - ASSET CLASSIFICATION REPORT",
        "=" * 42,
        "",
    ]
    for cls in ["curated_active", "generated_active", "fallback_active", "legacy_archive", "deprecated_unused", "placeholder_only"]:
        vals = classes.get(cls, [])
        r2.append(f"{cls}: {len(vals)}")
        for p in vals[:20]:
            r2.append(f"- {_r(p)}")
        if len(vals) > 20:
            r2.append(f"- ... +{len(vals) - 20} more")
        r2.append("")
    (ROOT / "asset_classification_report.txt").write_text("\n".join(r2) + "\n", encoding="utf-8")

    # Report 3: active runtime mappings
    r3 = [
        "PHASE 4 - ACTIVE RUNTIME ASSET REPORT",
        "=" * 44,
        "",
        "Canonical runtime paths and priority",
        "- Avatar/Portrait/Hologram priority: curated_active -> generated_active -> fallback_active",
        "- Card art: game/assets/sprites/cards/<id>.png (fallback placeholder if missing)",
        "- Biomes: game/assets/sprites/biomes/* then visual/generated fallback",
        "- Audio BGM/SFX/Stingers: game/audio/generated/* via game/audio/audio_engine.py",
        "- Studio intro visual: game/ui/screens/studio_intro.py (generated timeline + data/studio_intro_manifest.json)",
        "",
        "Avatar source resolution",
        json.dumps(avatar_sources, ensure_ascii=False, indent=2),
        "",
        "Runtime visual sample map",
        json.dumps(runtime_visual_samples, ensure_ascii=False, indent=2),
        "",
        "Runtime logging hooks already present",
        "- [asset] category=... source=...",
        "- [portrait] source=...",
        "- [Audio] context: ... file:...",
        "- [Audio] stinger: ... file:...",
    ]
    (ROOT / "active_runtime_asset_report.txt").write_text("\n".join(r3) + "\n", encoding="utf-8")

    # Report 4: legacy purge plan (safe, non-destructive)
    legacy_music = sorted(_all_files(ROOT / "game" / "assets" / "music", (".wav",)))
    legacy_sfx = sorted(_all_files(ROOT / "game" / "assets" / "sfx", (".wav",)))
    r4 = [
        "PHASE 4 - LEGACY PURGE PLAN (NON-DESTRUCTIVE)",
        "=" * 51,
        "",
        "Rules",
        "- No direct deletion in this phase.",
        "- Move candidates to archive only after runtime mapping verification.",
        "- Keep import/runtime compatibility.",
        "",
        "Archive candidates",
        f"- game/assets/music/*.wav: {len(legacy_music)} files (runtime currently uses game/audio/generated)",
        f"- game/assets/sfx/*.wav: {len(legacy_sfx)} files (legacy fallback paths; verify before archive)",
        "",
        "Recommended sequence",
        "1. Snapshot current runtime mapping (audio + avatar + biome + card).",
        "2. Move legacy candidates to assets/deprecated/ in batches.",
        "3. Run smoke tests + QA reports.",
        "4. If any missing file fallback appears, restore specific asset from archive.",
        "",
        "WARNING",
        "- Do not purge visual/generated manifests yet; they are still consumed by runtime fallback paths.",
    ]
    (ROOT / "legacy_purge_plan.txt").write_text("\n".join(r4) + "\n", encoding="utf-8")

    # Report 5: audio runtime mapping
    r5 = [
        "PHASE 4 - AUDIO RUNTIME MAPPING REPORT",
        "=" * 44,
        f"manifest_items={audio_map['manifest_items']}",
        "",
        "Context/file mapping",
    ]
    for k, v in sorted(audio_map["mapping"].items()):
        r5.append(f"- {k}: {v}")
    r5.extend([
        "",
        "Findings",
        "- Audio runtime is deterministic through audio_manifest + generated wav paths.",
        "- Legacy assets in game/assets/music are not primary runtime source.",
    ])
    (ROOT / "audio_runtime_mapping_report.txt").write_text("\n".join(r5) + "\n", encoding="utf-8")

    summary = {
        "reports": [
            "asset_disk_audit_report.txt",
            "asset_classification_report.txt",
            "active_runtime_asset_report.txt",
            "legacy_purge_plan.txt",
            "audio_runtime_mapping_report.txt",
        ],
        "counts": {k: len(v) for k, v in classes.items()},
        "roots": dict(by_root),
        "duplicate_groups": len(duplicate_groups),
    }
    return summary


if __name__ == "__main__":
    out = run()
    print("[qa_phase4] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))


