from __future__ import annotations

import subprocess
import sys

from .common import ROOT


CANONICAL_CHECKS: list[tuple[str, list[str]]] = [
    ("doctor", [sys.executable, "-m", "tools.doctor"]),
    ("card-coherence", [sys.executable, "-m", "tools.qa.check_card_coherence"]),
    ("combat-content-lock", [sys.executable, "-m", "tools.qa.check_combat_content_lock"]),
    ("deck-system", [sys.executable, "-m", "tools.qa.check_deck_system"]),
    ("beta-run-flow", [sys.executable, "-m", "tools.qa.check_beta_run_flow"]),
]


def run_check(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or "").strip().splitlines()
    err = (proc.stderr or "").strip().splitlines()
    last = out[-1] if out else (err[-1] if err else "")
    return proc.returncode, last


def run_suite() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for label, command in CANONICAL_CHECKS:
        rc, last = run_check(command)
        results.append(
            {
                "label": label,
                "command": command,
                "returncode": rc,
                "last": last,
                "status": "PASS" if rc == 0 else "WARNING",
            }
        )
    return results
