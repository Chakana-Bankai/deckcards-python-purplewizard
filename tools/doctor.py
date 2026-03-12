from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tools.lib.tooling_stack import console, load_tool_env

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
    console.print('[doctor] git:')
    try:
        out = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True, stderr=subprocess.STDOUT)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        console.print(f'  tracked_changes={len(lines)}')
        if lines:
            for ln in lines[:12]:
                console.print(f'  {ln}')
            if len(lines) > 12:
                console.print(f'  ... +{len(lines) - 12} more')
    except Exception as exc:
        console.print(f'  unavailable ({exc})')
        console.print('  run manually: git status')


def _folder_checks() -> None:
    console.print('[doctor] folders:')
    folders = [
        (ROOT / "assets" / "art_reference", "support_reference"),
        (ROOT / "assets" / "_archive", "archive_root"),
        (ROOT / "game" / "data", "runtime_data"),
        (ROOT / "game" / "assets" / "curated", "curated_assets"),
        (ROOT / "game" / "assets" / "sprites" / "cards", "runtime_card_art"),
        (ROOT / "game" / "audio" / "generated", "runtime_audio_generated"),
        (ROOT / "game" / "visual" / "generated", "runtime_visual_generated"),
    ]
    for p, label in folders:
        exists = p.exists()
        console.print(f"  {label}: {p.relative_to(ROOT)} => {'OK' if exists else 'MISSING'}")


def _autogen_files_checks() -> None:
    console.print('[doctor] autogen manifests:')
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
        console.print(f"  {p.relative_to(ROOT)}: {state}, mtime={_fmt_age(ts)}{hint}")


def main() -> int:
    env = load_tool_env(ROOT)
    console.print('[doctor] Chakana Dev Workflow Report')
    console.print(f'[doctor] python={sys.version.split()[0]} cwd={os.getcwd()} env={env.chakana_env} reports_dir={env.reports_dir}')
    try:
        _git_status_report()
        _folder_checks()
        _autogen_files_checks()
        console.print('[doctor] done')
        return 0
    except Exception as exc:
        console.print(f'[doctor] WARNING unexpected error: {exc}')
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
