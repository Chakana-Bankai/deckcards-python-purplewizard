from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "qa" / "reports"
DOCS = ROOT / "docs" / "architecture"


def _group_reports(paths: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        stem = p.stem.lower()
        if stem.startswith("qa_report_build"):
            key = "qa_report_build"
        elif "combat" in stem and "upgrade" in stem:
            key = "combat_system_upgrade"
        elif "visual" in stem and "consistency" in stem:
            key = "visual_consistency"
        elif "archetype" in stem and "balance" in stem:
            key = "archetype_balance"
        elif "legacy" in stem and "cleanup" in stem:
            key = "legacy_cleanup"
        elif "consolidation" in stem:
            key = "consolidation"
        elif "ui" in stem and "hierarchy" in stem:
            key = "ui_hierarchy"
        elif "audio" in stem and "direction" in stem:
            key = "audio_direction"
        else:
            key = stem
        groups[key].append(p)
    for k in list(groups.keys()):
        groups[k] = sorted(groups[k], key=lambda x: x.stat().st_mtime)
    return groups


def main() -> int:
    current = sorted((QA / "current").glob("*.txt")) + sorted((QA / "current").glob("*.md"))
    archive = sorted((QA / "archive").glob("*.txt")) + sorted((QA / "archive").glob("*.md"))

    groups = _group_reports(current + archive)

    # Canonical active report per group: prefer current latest, else latest archive.
    canonical: dict[str, Path] = {}
    for key, files in groups.items():
        current_files = [p for p in files if "\\current\\" in str(p) or "/current/" in str(p)]
        pick = current_files[-1] if current_files else files[-1]
        canonical[key] = pick

    out_index = QA / "ACTIVE_REPORTS.md"
    lines = []
    lines.append("# QA Active Reports")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("Canonical active report per group:")
    lines.append("")
    for key in sorted(canonical.keys()):
        p = canonical[key]
        rel = p.relative_to(ROOT)
        lines.append(f"- `{key}` -> `{rel}`")
    lines.append("")
    lines.append("Policy:")
    lines.append("- Keep only latest in `qa/reports/current` as active reference.")
    lines.append("- Keep history in `qa/reports/archive`.")
    lines.append("- Do not delete archive automatically in this pass.")
    out_index.write_text("\n".join(lines) + "\n", encoding="utf-8")

    DOCS.mkdir(parents=True, exist_ok=True)
    report = DOCS / "non_destructive_cleanup_guided_report.txt"
    rep = []
    rep.append("CHAKANA NON-DESTRUCTIVE CLEANUP GUIDED REPORT")
    rep.append("")
    rep.append(f"generated_at={datetime.now().isoformat(timespec='seconds')}")
    rep.append(f"qa_current_count={len(current)}")
    rep.append(f"qa_archive_count={len(archive)}")
    rep.append(f"group_count={len(groups)}")
    rep.append("")
    rep.append("[canonical_groups]")
    for key in sorted(canonical.keys()):
        rep.append(f"- {key}: {canonical[key].relative_to(ROOT)}")
    rep.append("")
    rep.append("[recommendations]")
    rep.append("- Keep ACTIVE_REPORTS.md as single entrypoint for QA status.")
    rep.append("- New QA outputs should overwrite same group file in current when possible.")
    rep.append("- Promote only final milestone reports to docs/archive summaries.")
    report.write_text("\n".join(rep) + "\n", encoding="utf-8")

    print(f"[cleanup_guided] wrote={out_index}")
    print(f"[cleanup_guided] wrote={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
