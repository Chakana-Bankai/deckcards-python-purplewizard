from pathlib import Path
import re

from . import art_pipeline, audio_pipeline, manifest_manager, qa_smoke, ui_audit
from .common import ROOT, write_text_report, rel


def _status_from_report(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "UNREADABLE"
    upper = text.upper()
    if "OVERALL=WARNING" in upper or "OVERALL=FAIL" in upper:
        return "WARNING"
    for match in re.finditer(r"\brc=(\d+)\b", text):
        if int(match.group(1)) != 0:
            return "WARNING"
    if "BROKEN" in upper or "FAIL" in upper:
        return "WARNING"
    return "OK"


def run(*, dry_run: bool = False):
    report = ROOT / "reports" / "qa" / "cli_validation_report.txt"
    checks = [
        ("manifest-audit", manifest_manager.run_audit),
        ("art-audit", art_pipeline.run),
        ("audio-audit", audio_pipeline.run),
        ("ui-audit", ui_audit.run),
        ("qa-smoke", qa_smoke.run),
    ]
    lines = ["mode=cli_validation", f"dry_run={dry_run}", ""]
    overall = "PASS"
    for name, fn in checks:
        subreport = fn(dry_run=dry_run)
        status = _status_from_report(subreport)
        if status != "OK":
            overall = "WARNING"
        lines.append(f"- {name}: {status} report={rel(subreport)}")
    lines += [
        "",
        f"overall={overall}",
        "checks=manifest-audit,art-audit,audio-audit,ui-audit,qa-smoke",
        "note=lightweight CLI validation only; no heavy runtime or bulk content generation in this phase",
    ]
    return write_text_report(report, "chakana_studio cli validation", lines)
