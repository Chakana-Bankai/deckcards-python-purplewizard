from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pygame

from game.audio.audio_engine import get_audio_engine
from game.core.paths import assets_dir, data_dir, project_root
from game.core.safe_io import atomic_write_json
from game.visual.generators.avatar_generator import AvatarGenerator
from game.visual.generators.biome_generator import BiomeGenerator


CORE_AUDIO_EXPORTS = {
    "menu_main": ("bgm", "menu_a"),
    "map_exploration": ("bgm", "map_kay_a"),
    "shop_ritual": ("bgm", "shop_a"),
    "combat_standard": ("bgm", "combat_a"),
    "boss_battle": ("bgm", "combat_boss_a"),
    "reward_reveal": ("bgm", "victory_a"),
    "defeat_stinger": ("stinger", "defeat"),
    "victory_stinger": ("stinger", "victory"),
    "civilization_reveal": ("stinger", "relic_gain"),
    "studio_logo_intro": ("stinger", "studio_intro"),
}

CORE_STINGERS = [
    "studio_intro",
    "combat_start",
    "boss_reveal",
    "relic_gain",
    "victory",
    "defeat",
    "pack_open",
    "level_up",
    "harmony_ready",
    "seal_ready",
]


@dataclass
class RegenReports:
    audio_lines: list[str]
    visual_lines: list[str]
    sanitize_lines: list[str]


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _write_report(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _collect_files(root: Path, suffix: str) -> list[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.rglob(f"*{suffix}") if p.is_file()])


def _archive_files(paths: Iterable[Path], archive_root: Path, root_prefix: Path, keep_names: set[str] | None = None) -> list[str]:
    moved: list[str] = []
    keep_names = keep_names or set()
    archive_root.mkdir(parents=True, exist_ok=True)
    for p in paths:
        if p.name in keep_names:
            continue
        rel = p.relative_to(root_prefix)
        target = archive_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(target))
        moved.append(str(rel).replace("\\", "/"))
    return moved


def _ensure_audio_regen(reports: RegenReports) -> set[Path]:
    engine = get_audio_engine()
    old_manifest_path = Path(engine.manifest_path)
    old_manifest = {}
    if old_manifest_path.exists():
        try:
            old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            old_manifest = {}

    reports.audio_lines.append("## Audio Regeneration")
    reports.audio_lines.append(f"timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}")
    reports.audio_lines.append("action=ensure_core_assets(force=True)")
    engine.ensure_core_assets(force=True)

    items = engine._manifest.get("items", {}) if isinstance(engine._manifest, dict) else {}
    active_paths: set[Path] = set()

    def item_path(item_id: str) -> Path:
        row = items.get(item_id, {}) if isinstance(items, dict) else {}
        raw = str((row or {}).get("file_path", "")).strip()
        return Path(raw) if raw else Path()

    for st in CORE_STINGERS:
        path = engine._ensure_stinger(st, force=True)
        active_paths.add(path)
        reports.audio_lines.append(f"stinger={st} file={path}")

    export_dir = engine.generated_root / "core"
    export_dir.mkdir(parents=True, exist_ok=True)
    for context_name, (kind, src_id) in CORE_AUDIO_EXPORTS.items():
        if kind == "bgm":
            source = item_path(src_id)
            out = export_dir / f"{context_name}.wav"
        else:
            source = item_path(f"stinger_{src_id}")
            out = export_dir / f"{context_name}.wav"
        if not source.exists():
            reports.audio_lines.append(f"warning=missing_source context={context_name} source={source}")
            continue
        shutil.copy2(source, out)
        active_paths.add(out)
        reports.audio_lines.append(f"context={context_name} old={source.name} new={out.relative_to(project_root())}")

    for _k, meta in (items.items() if isinstance(items, dict) else []):
        p = Path(str((meta or {}).get("file_path", "")))
        if p.exists():
            active_paths.add(p)

    generated_files = _collect_files(engine.generated_root, ".wav")
    stale = [p for p in generated_files if p not in active_paths]
    archive_root = engine.generated_root / "_deprecated" / _now_tag()
    moved = _archive_files(stale, archive_root, engine.generated_root, keep_names={".gitkeep"})
    reports.sanitize_lines.append("## Audio Sanitization")
    reports.sanitize_lines.append(f"stale_audio_archived={len(moved)} archive={archive_root.relative_to(project_root())}")
    for rel in moved:
        reports.sanitize_lines.append(f"archived_audio={rel}")

    bgm_manifest_path = data_dir() / "bgm_manifest.json"
    bgm_manifest = {}
    if bgm_manifest_path.exists():
        try:
            bgm_manifest = json.loads(bgm_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            bgm_manifest = {}
    if not isinstance(bgm_manifest, dict):
        bgm_manifest = {}
    bgm_manifest["_core_context_map"] = {
        "version": "0.9.104",
        "generated_at": int(time.time()),
        "contexts": {
            ctx: f"game/audio/generated/core/{ctx}.wav"
            for ctx in CORE_AUDIO_EXPORTS.keys()
        },
    }
    atomic_write_json(bgm_manifest_path, bgm_manifest)
    reports.audio_lines.append("manifest=game/data/bgm_manifest.json updated=_core_context_map")

    old_items = old_manifest.get("items", {}) if isinstance(old_manifest, dict) else {}
    for ctx, (_kind, src_id) in CORE_AUDIO_EXPORTS.items():
        old_ref = None
        if src_id in old_items:
            old_ref = str((old_items.get(src_id) or {}).get("file_path", ""))
        if src_id.startswith("stinger_") and src_id in old_items:
            old_ref = str((old_items.get(src_id) or {}).get("file_path", ""))
        reports.audio_lines.append(f"mapping={ctx} old={old_ref or '-'}")

    return active_paths


def _render_studio_branding(reports: RegenReports) -> list[Path]:
    out_dir = assets_dir() / "curated" / "studio"
    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    w, h = 1024, 576
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        p = y / max(1, h - 1)
        c = (
            int(8 + (28 - 8) * p),
            int(8 + (18 - 8) * p),
            int(18 + (52 - 18) * p),
        )
        pygame.draw.line(base, c, (0, y), (w, y))
    cx, cy = w // 2, int(h * 0.44)
    for r, a in [(132, 30), (96, 44), (62, 62)]:
        pygame.draw.circle(base, (210, 196, 255, a), (cx, cy), r, 1)
    step = 22
    pygame.draw.rect(base, (236, 236, 246, 230), (cx - step // 2, cy - step // 2, step, step), 2)
    pygame.draw.line(base, (236, 236, 246, 220), (cx - 76, cy), (cx + 76, cy), 2)
    pygame.draw.line(base, (236, 236, 246, 220), (cx, cy - 76), (cx, cy + 76), 2)
    try:
        font = pygame.font.SysFont("arial", 58, bold=True)
    except Exception:
        font = None
    if font is not None:
        title = font.render("CHAKANA STUDIO", True, (246, 246, 252))
        base.blit(title, title.get_rect(center=(cx, int(h * 0.76))))

    logo = out_dir / "chakana_studio_logo.png"
    pygame.image.save(base, str(logo))
    created.append(logo)

    glyph = pygame.Surface((256, 256), pygame.SRCALPHA)
    gx, gy = 128, 128
    pygame.draw.circle(glyph, (220, 206, 255, 60), (gx, gy), 98, 1)
    pygame.draw.rect(glyph, (236, 236, 246, 240), (gx - 14, gy - 14, 28, 28), 2)
    pygame.draw.line(glyph, (236, 236, 246, 220), (gx - 74, gy), (gx + 74, gy), 2)
    pygame.draw.line(glyph, (236, 236, 246, 220), (gx, gy - 74), (gx, gy + 74), 2)
    glyph_path = out_dir / "chakana_loading_glyph.png"
    pygame.image.save(glyph, str(glyph_path))
    created.append(glyph_path)

    emblem = pygame.Surface((256, 256), pygame.SRCALPHA)
    pygame.draw.polygon(emblem, (236, 236, 246, 230), [(128, 24), (232, 128), (128, 232), (24, 128)], 2)
    pygame.draw.circle(emblem, (180, 124, 255, 82), (128, 128), 90, 1)
    emblem_path = out_dir / "chakana_emblem.png"
    pygame.image.save(emblem, str(emblem_path))
    created.append(emblem_path)

    reports.visual_lines.append("## Studio Branding")
    for p in created:
        reports.visual_lines.append(f"created={p.relative_to(project_root())}")
    return created


def _ensure_visual_regen(reports: RegenReports) -> set[Path]:
    active_paths: set[Path] = set()
    reports.visual_lines.append("## Visual Regeneration")
    reports.visual_lines.append(f"timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}")

    av = AvatarGenerator()
    curated = assets_dir() / "curated" / "avatars"
    curated.mkdir(parents=True, exist_ok=True)
    master_targets = {
        "chakana_mage_master_concept.png": ("menu", (768, 1024)),
        "chakana_mage_master_portrait.png": ("menu", (512, 768)),
        "chakana_mage_master_hologram.png": ("combat_hud", (256, 320)),
    }
    for filename, (variant, size) in master_targets.items():
        surf = av.render(variant, size)
        out = curated / filename
        pygame.image.save(surf, str(out))
        active_paths.add(out)
        reports.visual_lines.append(f"avatar_curated={out.relative_to(project_root())}")

    sprite_avatar_dir = assets_dir() / "sprites" / "avatar"
    sprite_avatar_dir.mkdir(parents=True, exist_ok=True)
    runtime_avatar = {
        "chakana_mage_concept.png": curated / "chakana_mage_master_concept.png",
        "chakana_mage_portrait.png": curated / "chakana_mage_master_portrait.png",
        "chakana_mage_hologram.png": curated / "chakana_mage_master_hologram.png",
    }
    for name, src in runtime_avatar.items():
        out = sprite_avatar_dir / name
        shutil.copy2(src, out)
        active_paths.add(out)
        reports.visual_lines.append(f"avatar_runtime={out.relative_to(project_root())}")

    bg = BiomeGenerator()
    biome_targets = [
        ("ukhu", "ukhu_pacha"),
        ("kaypacha", "kay_pacha"),
        ("hanan", "hanan_pacha"),
        ("fractura_chakana", "fractura_chakana"),
        ("hiperborea", "hanan_pacha"),
        ("ritual_cavern", "ukhu_pacha"),
        ("astral_codex", "kay_pacha"),
    ]
    biome_dir = assets_dir() / "sprites" / "biomes"
    biome_dir.mkdir(parents=True, exist_ok=True)
    for name, biome_id in biome_targets:
        surf = bg.render_panel(biome_id, (1142, 852), motif="bg")
        out = biome_dir / f"{name}.png"
        pygame.image.save(surf, str(out))
        active_paths.add(out)
        reports.visual_lines.append(f"biome={name} source={biome_id} file={out.relative_to(project_root())}")

    studio_paths = _render_studio_branding(reports)
    active_paths.update(studio_paths)

    studio_manifest_path = data_dir() / "studio_intro_manifest.json"
    studio_manifest = {
        "version": "studio_intro_cosmic_v3_curated_regen",
        "seed": int(time.time()) % 100000,
        "duration": 4.0,
        "updated_at": int(time.time()),
        "source": "generated_or_cache",
        "branding_asset": "game/assets/curated/studio/chakana_studio_logo.png",
    }
    atomic_write_json(studio_manifest_path, studio_manifest)
    reports.visual_lines.append("studio_manifest=game/data/studio_intro_manifest.json refreshed")

    gen_root = project_root() / "game" / "visual" / "generated"
    stale: list[Path] = []
    for p in _collect_files(gen_root, ".png"):
        if p.name == ".gitkeep":
            continue
        if p not in active_paths and ("portraits" in str(p).lower() or "biomes" in str(p).lower()):
            stale.append(p)
    archive_root = gen_root / "_deprecated" / _now_tag()
    moved = _archive_files(stale, archive_root, gen_root, keep_names={".gitkeep"})
    reports.sanitize_lines.append("## Visual Sanitization")
    reports.sanitize_lines.append(f"stale_visual_archived={len(moved)} archive={archive_root.relative_to(project_root())}")
    for rel in moved:
        reports.sanitize_lines.append(f"archived_visual={rel}")

    return active_paths


def _write_reports(reports: RegenReports) -> None:
    _write_report(project_root() / "regen_audio_report.txt", reports.audio_lines)
    _write_report(project_root() / "regen_visual_report.txt", reports.visual_lines)
    _write_report(project_root() / "active_asset_sanitization_report.txt", reports.sanitize_lines)


def _update_version() -> None:
    version_path = data_dir() / "version.json"
    payload = {}
    if version_path.exists():
        try:
            payload = json.loads(version_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["version"] = "0.9.104"
    payload["build"] = "Curated Regen + Cache Reset"
    payload["date"] = time.strftime("%Y-%m-%d")
    atomic_write_json(version_path, payload)

    py_version = project_root() / "game" / "version.py"
    py_version.write_text('VERSION = "0.9.104"\n', encoding="utf-8")


def main() -> int:
    pygame.init()
    reports = RegenReports(audio_lines=[], visual_lines=[], sanitize_lines=[])
    _ensure_audio_regen(reports)
    _ensure_visual_regen(reports)
    _update_version()
    _write_reports(reports)
    print("[curated_regen] done")
    print(f"[curated_regen] report={project_root() / 'regen_audio_report.txt'}")
    print(f"[curated_regen] report={project_root() / 'regen_visual_report.txt'}")
    print(f"[curated_regen] report={project_root() / 'active_asset_sanitization_report.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
