from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
QA = ROOT / "qa"
TOOLS = ROOT / "tools"
GAME = ROOT / "game"


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _list_files(base: Path, exts: set[str] | None = None) -> list[Path]:
    out = []
    if not base.exists():
        return out
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if exts and p.suffix.lower() not in exts:
            continue
        out.append(p)
    return sorted(out)


def _is_experimental(name: str) -> bool:
    low = name.lower()
    keys = ["template", "draft", "tmp", "experimental", "notes", "plan", "audit"]
    return any(k in low for k in keys)


def _is_outdated(name: str) -> bool:
    low = name.lower()
    return ("archive" in low) or bool(re.search(r"0_9_10[0-5]", low))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return ""


def document_audit() -> str:
    files = _list_files(DOCS, {".md", ".txt", ".json"}) + _list_files(QA, {".md", ".txt"}) + _list_files(TOOLS, {".py", ".md", ".txt"})

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for p in files:
        try:
            by_hash[_sha1(p)].append(p)
        except Exception:
            continue

    exact_dups = [grp for grp in by_hash.values() if len(grp) > 1]
    outdated = [p for p in files if _is_outdated(str(p.relative_to(ROOT)).replace("\\", "/"))]
    experimental = [p for p in files if _is_experimental(p.name)]

    qa_reports = _list_files(QA / "reports", {".txt", ".md"})
    qa_by_stem: dict[str, list[Path]] = defaultdict(list)
    for p in qa_reports:
        stem = re.sub(r"_0_9_[0-9a-z_\.]+", "", p.stem.lower())
        stem = re.sub(r"_latest.*", "", stem)
        qa_by_stem[stem].append(p)
    redundant_qa = {k: sorted(v) for k, v in qa_by_stem.items() if len(v) > 2}

    lines = []
    lines.append("CHAKANA DOCUMENT AUDIT REPORT")
    lines.append("")
    lines.append(f"generated_at={datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"docs_files={len(_list_files(DOCS))}")
    lines.append(f"qa_files={len(_list_files(QA))}")
    lines.append(f"tools_files={len(_list_files(TOOLS))}")
    lines.append("")

    lines.append("[duplicate_documents_exact_hash]")
    if not exact_dups:
        lines.append("none")
    else:
        for grp in exact_dups[:40]:
            lines.append(f"- hash_group size={len(grp)}")
            for p in grp:
                lines.append(f"  - {p.relative_to(ROOT)}")

    lines.append("")
    lines.append("[outdated_or_archived_candidates]")
    for p in outdated[:120]:
        lines.append(f"- {p.relative_to(ROOT)}")

    lines.append("")
    lines.append("[experimental_or_planning_candidates]")
    for p in experimental[:120]:
        lines.append(f"- {p.relative_to(ROOT)}")

    lines.append("")
    lines.append("[redundant_qa_report_groups]")
    if not redundant_qa:
        lines.append("none")
    else:
        for k, arr in sorted(redundant_qa.items()):
            lines.append(f"- group={k} count={len(arr)}")
            for p in arr[-3:]:
                lines.append(f"  - keep_candidate={p.relative_to(ROOT)}")

    return "\n".join(lines) + "\n"


def ensure_lore_canon() -> str:
    p = DOCS / "lore" / "Lore_Canon.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    text = """# Lore Canon

## Cosmologia Chakana
La Trama se sostiene sobre la Chakana como eje de equilibrio entre planos. Toda energia ritual, armonia y ruptura se interpreta como desajuste o restauracion del balance cosmico.

## Historia de Hiperborea
Hiperborea representa una civilizacion ancestral avanzada que domino tecnologia cristalina y arquitectura sagrada. Su conocimiento no es DLC externo: emerge como memoria olvidada dentro de la progresion de run.

## Facciones Arconte
Los Arcontes son entidades de corrupcion del vacio. Su doctrina altera la Trama por control, entropia y miedo. Visualmente y narrativamente se describen como opresivos, fracturados y hostiles al equilibrio.

## Planos de Existencia
- Hanan Pacha: plano superior, guardianes y vision.
- Kay Pacha: plano vivo, decision tactica y camino del jugador.
- Ukhu/Uku Pacha: plano profundo, sombras, deuda ritual y corrupcion.

## Arquetipos del Jugador
- Cosmic Warrior: presion ofensiva y cierre rapido.
- Harmony Guardian: supervivencia, conversion de defensa y control de ritmo.
- Oracle of Fate: lectura, combinacion y valor progresivo.

## Regla de lenguaje canon
El texto visible para jugador evita IDs tecnicos, snake_case y etiquetas de debug. Los nombres deben mantener tono mistico, espiritual y legible en espanol.
"""
    p.write_text(text, encoding="utf-8")
    return str(p.relative_to(ROOT))


def ensure_art_direction() -> str:
    p = DOCS / "design" / "Art_Direction.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    text = """# Art Direction

## Identidad visual por set
- Base: geometria mistica, motivos Chakana, paleta oro/violeta.
- Hiperborea: civilizacion ancestral avanzada, templos atlantes polares, tecnologia cristalina, blanco marmol/hielo/oro antiguo.
- Arconte: entidades oscuras, corrupcion del vacio, horror gnostico, paleta purpura oscuro/carmesi/negro.

## Reglas de composicion narrativa
Cada carta debe comunicar:
1. Subject: personaje u objeto principal (50-60% del encuadre).
2. Action: energia/movimiento visible (10-20%).
3. Environment: contexto de fondo legible (20-30%).

## Reglas de legibilidad
- No estirar arte.
- Mantener claridad en Full HD.
- Evitar ruido geometrico dominante sobre motivo central.
- Reservar tratamiento premium para legendarias (glow + detalle adicional).

## Avatar y holograma
- Retrato canon: 512x512, foco rostro/capucha/simbolo Chakana.
- Holograma: scanline, glow suave, energia transparente.
- Evitar overlay blanco agresivo.

## Consistencia UI
Iconografia, color y jerarquia tipografica deben coincidir entre combate, codex, shop y mapa.
"""
    p.write_text(text, encoding="utf-8")
    return str(p.relative_to(ROOT))


def build_system_reference() -> str:
    # Canonical one-doc-per-system mapping.
    rows = [
        ("combat_system", "docs/canon/systems/CHAKANA_COMBAT_SYSTEM_1_0.md", "canonical"),
        ("card_system", "docs/canon/systems/CHAKANA_CARD_SYSTEM_1_0.md", "canonical"),
        ("shop_system", "docs/design/game_design_document.md", "canonical_section:shop"),
        ("avatar_system", "docs/lore/avatar_curated_checklist.md", "canonical"),
        ("art_system", "docs/design/Art_Direction.md", "canonical"),
        ("audio_system", "docs/canon/systems/CHAKANA_AUDIO_SYSTEM_1_0.md", "canonical"),
    ]

    lines = [
        "# System Reference",
        "",
        "Canonical references after consolidation.",
        "",
        "| System | Canonical document | Status |",
        "|---|---|---|",
    ]
    for a, b, c in rows:
        lines.append(f"| {a} | `{b}` | {c} |")

    lines += [
        "",
        "## Duplicate handling",
        "- Legacy and archive docs remain for traceability.",
        "- Active references should point to canonical documents above.",
        "- New lore/art canon files replace fragmented style notes.",
    ]
    return "\n".join(lines) + "\n"


def render_consistency() -> str:
    py_files = _list_files(GAME, {".py"})
    text_by_file = {p: _read_text(p) for p in py_files}

    card_renderer_refs = []
    alt_card_renderer_defs = []
    avatar_refs = []
    holo_refs = []

    for p, t in text_by_file.items():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if "card_renderer" in t and ("render_card_preview" in t or "render_card_small" in t):
            card_renderer_refs.append(rel)
        if rel.startswith("game/ui/") and re.search(r"def\s+render_card", t) and "ui/components/card_renderer.py" not in rel:
            alt_card_renderer_defs.append(rel)
        if "assets.sprite(\"avatar\"" in t or "chakana_mage_master" in t:
            avatar_refs.append(rel)
        if "scanline" in t.lower() or "hologram" in t.lower():
            holo_refs.append(rel)

    lines = []
    lines.append("CHAKANA RENDER CONSISTENCY REPORT")
    lines.append("")
    lines.append("[cards]")
    lines.append("- canonical_renderer=game/ui/components/card_renderer.py")
    lines.append(f"- renderer_references={len(card_renderer_refs)}")
    for r in sorted(set(card_renderer_refs))[:40]:
        lines.append(f"  - {r}")
    lines.append(f"- alternate_renderer_defs={len(set(alt_card_renderer_defs))}")
    for r in sorted(set(alt_card_renderer_defs))[:20]:
        lines.append(f"  - potential_mismatch={r}")

    lines.append("")
    lines.append("[avatars_holograms]")
    lines.append(f"- avatar_ref_files={len(set(avatar_refs))}")
    lines.append(f"- hologram_ref_files={len(set(holo_refs))}")
    lines.append("- canonical_avatar_assets=game/assets/curated/avatars")

    lines.append("")
    lines.append("[ui_pipeline_status]")
    if alt_card_renderer_defs:
        lines.append("WARNING: alternate render definitions detected; keep calls routed through canonical card_renderer where possible.")
    else:
        lines.append("PASS: single card renderer path detected.")

    return "\n".join(lines) + "\n"


def _collect_manifest_audio_paths() -> set[str]:
    out: set[str] = set()

    for mf in [GAME / "data" / "bgm_manifest.json", GAME / "audio" / "audio_manifest.json"]:
        if not mf.exists():
            continue
        try:
            payload = json.loads(mf.read_text(encoding="utf-8-sig"))
        except Exception:
            continue

        def walk(v):
            if isinstance(v, dict):
                for vv in v.values():
                    walk(vv)
            elif isinstance(v, list):
                for vv in v:
                    walk(vv)
            elif isinstance(v, str):
                low = v.lower()
                if any(low.endswith(ext) for ext in [".wav", ".ogg", ".mp3"]):
                    out.add(low.replace("\\", "/"))

        walk(payload)

    return out


def asset_cleanup() -> str:
    asset_files = _list_files(GAME / "assets", {".png", ".wav", ".ogg", ".mp3"}) + _list_files(GAME / "audio", {".wav", ".ogg", ".mp3"})

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for p in asset_files:
        try:
            by_hash[_sha1(p)].append(p)
        except Exception:
            continue

    dup_groups = [grp for grp in by_hash.values() if len(grp) > 1]

    placeholders = []
    for p in asset_files:
        low = p.name.lower()
        if any(k in low for k in ["placeholder", "fallback", "dummy", "temp", "probe", "test"]):
            placeholders.append(p)

    audio_files = [p for p in asset_files if p.suffix.lower() in {".wav", ".ogg", ".mp3"}]
    refs = _collect_manifest_audio_paths()

    unused_audio = []
    for p in audio_files:
        rel = str(p.relative_to(ROOT)).replace("\\", "/").lower()
        full = str(p).replace("\\", "/").lower()
        name = p.name.lower()
        hit = any((name in r) or (rel in r) or (full in r) for r in refs)
        if not hit:
            unused_audio.append(p)

    lines = []
    lines.append("CHAKANA ASSET CLEANUP REPORT")
    lines.append("")
    lines.append(f"assets_scanned={len(asset_files)}")
    lines.append(f"duplicate_asset_groups={len(dup_groups)}")
    lines.append(f"placeholder_candidates={len(placeholders)}")
    lines.append(f"unused_audio_candidates={len(unused_audio)}")

    lines.append("")
    lines.append("[duplicate_asset_groups_sample]")
    for grp in dup_groups[:30]:
        lines.append(f"- group size={len(grp)}")
        for p in grp[:5]:
            lines.append(f"  - {p.relative_to(ROOT)}")

    lines.append("")
    lines.append("[placeholder_candidates_sample]")
    for p in placeholders[:80]:
        lines.append(f"- {p.relative_to(ROOT)}")

    lines.append("")
    lines.append("[unused_audio_candidates_sample]")
    for p in unused_audio[:120]:
        lines.append(f"- {p.relative_to(ROOT)}")

    return "\n".join(lines) + "\n"


def final_consolidation() -> str:
    lines = []
    lines.append("CHAKANA PROJECT CONSOLIDATION REPORT")
    lines.append("")
    lines.append("[alignment]")
    lines.append("- lore: docs/lore/Lore_Canon.md")
    lines.append("- art direction: docs/design/Art_Direction.md")
    lines.append("- systems map: system_reference.md")
    lines.append("- render audit: render_consistency_report.txt")
    lines.append("- asset audit: asset_cleanup_report.txt")

    lines.append("")
    lines.append("[canonical_structures]")
    lines.append("- runtime systems remain non-destructively in place")
    lines.append("- docs/systems/*.md are canonical for gameplay/combat/card/enemy/relic/meta")
    lines.append("- lore canon unified in a single document")
    lines.append("- art direction unified in a single document")

    lines.append("")
    lines.append("[warnings]")
    lines.append("- archive contains many historical reports; keep but avoid using as active source")
    lines.append("- some tool wrappers duplicate modules by design for backward compatibility")
    lines.append("- audio canonical doc should be migrated from archive to docs/systems in a later pass")

    lines.append("")
    lines.append("[next_actions]")
    lines.append("1. Keep only latest QA report in qa/reports/current as active reference")
    lines.append("2. Migrate soundtrack canonical plan from archive to docs/canon/systems/CHAKANA_AUDIO_SYSTEM_1_0.md")
    lines.append("3. Optional: create a machine-readable canonical index for docs and reports")

    return "\n".join(lines) + "\n"


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    write_file(ROOT / "document_audit_report.txt", document_audit())

    lore_path = ensure_lore_canon()
    art_path = ensure_art_direction()

    system_ref_text = build_system_reference()
    system_ref_text += f"\n\nUpdated with: `{lore_path}` and `{art_path}`\n"
    write_file(ROOT / "system_reference.md", system_ref_text)

    write_file(ROOT / "render_consistency_report.txt", render_consistency())
    write_file(ROOT / "asset_cleanup_report.txt", asset_cleanup())
    write_file(ROOT / "chakana_project_consolidation_report.txt", final_consolidation())

    print("[chakana_audit] wrote=document_audit_report.txt")
    print("[chakana_audit] wrote=system_reference.md")
    print("[chakana_audit] wrote=docs/lore/Lore_Canon.md")
    print("[chakana_audit] wrote=docs/design/Art_Direction.md")
    print("[chakana_audit] wrote=render_consistency_report.txt")
    print("[chakana_audit] wrote=asset_cleanup_report.txt")
    print("[chakana_audit] wrote=chakana_project_consolidation_report.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
