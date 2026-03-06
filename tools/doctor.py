from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _safe_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except Exception:
        return None


def _fmt_age(ts: float | None) -> str:
    if ts is None:
        return "missing"
    delta = max(0, int(time.time() - ts))
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def _git_status_report() -> None:
    print("[doctor] git:")
    try:
        out = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True, stderr=subprocess.STDOUT)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        print(f"  tracked_changes={len(lines)}")
        if lines:
            for ln in lines[:12]:
                print(f"  {ln}")
            if len(lines) > 12:
                print(f"  ... +{len(lines) - 12} more")
    except Exception as exc:
        print(f"  unavailable ({exc})")
        print("  run manually: git status")


def _folder_checks() -> None:
    print("[doctor] folders:")
    folders = [
        ROOT / "assets" / "sprites" / "cards",
        ROOT / "assets" / "music",
        ROOT / "game" / "data",
        ROOT / "game" / "assets" / "sprites" / "cards",
        ROOT / "game" / "assets" / "music",
    ]
    for p in folders:
        exists = p.exists()
        print(f"  {p.relative_to(ROOT)}: {'OK' if exists else 'MISSING'}")


def _autogen_files_checks() -> None:
    print("[doctor] autogen manifests:")
    files = [
        ROOT / "game" / "data" / "art_manifest.json",
        ROOT / "game" / "data" / "bgm_manifest.json",
        ROOT / "game" / "data" / "card_prompts.json",
    ]
    for p in files:
        ts = _safe_mtime(p)
        state = "OK" if ts is not None else "MISSING"
        hint = ""
        if ts is not None and (time.time() - ts) < 3600:
            hint = " (recently updated; check autogen churn)"
        print(f"  {p.relative_to(ROOT)}: {state}, mtime={_fmt_age(ts)}{hint}")


def main() -> int:
    print("[doctor] Chakana Dev Workflow Report")
    print(f"[doctor] python={sys.version.split()[0]} cwd={os.getcwd()}")
    try:
        _git_status_report()
        _folder_checks()
        _autogen_files_checks()
        print("[doctor] done")
        return 0
    except Exception as exc:
        print(f"[doctor] WARNING unexpected error: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
