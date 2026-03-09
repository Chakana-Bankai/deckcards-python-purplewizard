from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.core.paths import data_dir
from game.core.safe_io import load_json

ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "final_gameplay_integration_fix_report.txt"
OUT_MD = ROOT / "final_gameplay_integration_fix_report.md"
OUT_KNOT = ROOT / "system_knot_audit_report.txt"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def _status_from_report(path: Path, default: str = "WARNING") -> str:
    if not path.exists():
        return "FAIL"
    txt = path.read_text(encoding="utf-8", errors="replace")
    for line in txt.splitlines():
        line_l = line.strip().lower()
        if line_l.startswith("overall="):
            val = line.split("=", 1)[1].strip().upper()
            if val in {"PASS", "WARNING", "FAIL"}:
                return val
    return default


def _version_build() -> tuple[str, str]:
    v = load_json(data_dir() / "version.json", default={})
    return str(v.get("version", "n/a")), str(v.get("build", "n/a"))


def run_phase8_integration() -> dict:
    checks: list[CheckResult] = []

    qa_jobs = [
        ("phase1_gameplay_blockers", [sys.executable, "-m", "tools.qa_phase1_gameplay_blockers"], ROOT / "gameplay_blocker_report.txt"),
        ("phase2_pack_shop", [sys.executable, "-m", "tools.qa_phase2_pack_shop_integration"], ROOT / "pack_shop_integration_report.txt"),
        ("phase3_hologram_dialogue", [sys.executable, "-m", "tools.qa_phase3_hologram_dialogue"], ROOT / "hologram_dialogue_integration_report.txt"),
        ("phase3b_event_system", [sys.executable, "-m", "tools.qa_phase3b_event_system"], ROOT / "event_node_refactor_report.txt"),
        ("phase4_asset_pipeline", [sys.executable, "-m", "tools.qa_phase4_asset_pipeline_audit"], ROOT / "asset_disk_audit_report.txt"),
        ("phase5_visual_audio_upgrade", [sys.executable, "-m", "tools.qa_phase5_visual_audio_upgrade"], ROOT / "visual_pipeline_upgrade_report.txt"),
        ("phase6_combat_hud", [sys.executable, "-m", "tools.qa_phase6_combat_hud"], ROOT / "combat_hud_polish_report.txt"),
        ("phase7_extended", [sys.executable, "-m", "tools.qa_phase7_extended"], ROOT / "qa_report_phase7_extended.txt"),
    ]

    for name, cmd, report_path in qa_jobs:
        code, out, err = _run(cmd)
        status = _status_from_report(report_path)
        if code != 0:
            status = "FAIL"
            detail = f"exit={code} report={report_path.name}"
        else:
            detail = f"report={report_path.name}"
        if status == "WARNING" and err.strip():
            detail += " warnings_in_stderr"
        checks.append(CheckResult(name=name, status=status, detail=detail))

    key_reports = {
        "gameplay_blocker_report": (ROOT / "gameplay_blocker_report.txt").exists(),
        "pack_shop_integration_report": (ROOT / "pack_shop_integration_report.txt").exists(),
        "hologram_dialogue_report": (ROOT / "hologram_dialogue_integration_report.txt").exists(),
        "event_system_reports": (ROOT / "event_node_refactor_report.txt").exists() and (ROOT / "event_system_design_report.txt").exists(),
        "asset_pipeline_reports": (ROOT / "asset_disk_audit_report.txt").exists() and (ROOT / "active_runtime_asset_report.txt").exists(),
        "visual_pipeline_reports": (ROOT / "visual_pipeline_upgrade_report.txt").exists() and (ROOT / "portrait_pipeline_upgrade_report.txt").exists(),
        "combat_hud_report": (ROOT / "combat_hud_polish_report.txt").exists(),
        "phase7_extended_report": (ROOT / "qa_report_phase7_extended.txt").exists(),
    }

    pass_count = sum(1 for c in checks if c.status == "PASS")
    warn_count = sum(1 for c in checks if c.status == "WARNING")
    fail_count = sum(1 for c in checks if c.status == "FAIL")

    overall = "PASS"
    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARNING"

    return {
        "overall": overall,
        "checks": [c.__dict__ for c in checks],
        "summary": {
            "pass": pass_count,
            "warning": warn_count,
            "fail": fail_count,
            "reports_present": key_reports,
        },
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _text_report(payload: dict) -> str:
    version, build = _version_build()
    lines = [
        "CHAKANA - FINAL GAMEPLAY INTEGRATION FIX REPORT",
        "=" * 60,
        f"version={version}",
        f"build={build}",
        f"generated_at={payload.get('timestamp', '')}",
        f"overall={payload.get('overall', 'WARNING')}",
        "",
        "Checks",
    ]
    for c in payload.get("checks", []):
        lines.append(f"- {c.get('name')}: {c.get('status')} ({c.get('detail')})")
    lines += [
        "",
        "Summary",
        f"- PASS={payload.get('summary', {}).get('pass', 0)}",
        f"- WARNING={payload.get('summary', {}).get('warning', 0)}",
        f"- FAIL={payload.get('summary', {}).get('fail', 0)}",
        "",
        "Report Presence",
    ]
    for k, v in payload.get("summary", {}).get("reports_present", {}).items():
        lines.append(f"- {k}: {'OK' if v else 'MISSING'}")
    lines.append("")
    return "\n".join(lines)


def _knot_report(payload: dict) -> str:
    checks = {c["name"]: c["status"] for c in payload.get("checks", [])}
    rows = [
        ("gameplay -> combat", checks.get("phase1_gameplay_blockers", "WARNING")),
        ("combat -> rewards/packs", checks.get("phase2_pack_shop", "WARNING")),
        ("narrative -> hologram", checks.get("phase3_hologram_dialogue", "WARNING")),
        ("events -> node flow", checks.get("phase3b_event_system", "WARNING")),
        ("content -> assets runtime", checks.get("phase4_asset_pipeline", "WARNING")),
        ("visual/audio pipeline", checks.get("phase5_visual_audio_upgrade", "WARNING")),
        ("combat HUD polish", checks.get("phase6_combat_hud", "WARNING")),
        ("unlock + variety + visibility", checks.get("phase7_extended", "WARNING")),
    ]
    lines = [
        "CHAKANA - SYSTEM KNOT AUDIT",
        "=" * 40,
        f"overall={payload.get('overall', 'WARNING')}",
        "",
    ]
    for label, status in rows:
        lines.append(f"- {label}: {status}")

    lines += [
        "",
        "Priority Risks",
        "- P1 runtime_break: none detected" if payload.get("overall") != "FAIL" else "- P1 runtime_break: check failed phases above",
        "- P2 visual_integrity: keep monitoring HUD/card/codex snapshots in Full HD",
        "- P3 extraction_readiness: consolidate duplicate UI paths into canonical modules incrementally",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    payload = run_phase8_integration()
    txt = _text_report(payload)
    md = "```text\n" + txt + "\n```\n"
    knot = _knot_report(payload)

    OUT_TXT.write_text(txt, encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_KNOT.write_text(knot, encoding="utf-8")

    print(json.dumps({
        "overall": payload.get("overall"),
        "txt": str(OUT_TXT.name),
        "md": str(OUT_MD.name),
        "knot": str(OUT_KNOT.name),
    }, ensure_ascii=False, indent=2))
    return 0 if payload.get("overall") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
