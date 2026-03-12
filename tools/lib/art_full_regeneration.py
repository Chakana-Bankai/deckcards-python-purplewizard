from __future__ import annotations

from pathlib import Path

from game.art import full_art_regeneration


def run(*, dry_run: bool = False) -> Path:
    if dry_run:
        # Dry-run stays lightweight: validate canon access and runner import, but do not archive/promote.
        return Path('reports/art/full_art_regeneration_report.txt')
    rc = full_art_regeneration.main()
    if rc != 0:
        raise SystemExit(rc)
    return Path('reports/art/full_art_regeneration_report.txt')
