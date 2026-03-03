"""Safe data loading with clear logs and defaults."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path, default):
    try:
        if not path.exists():
            print(f"[safe_io] missing file: {path}")
            return default
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"[safe_io] invalid JSON in {path}: {exc}")
        return default
    except Exception as exc:
        print(f"[safe_io] failed loading {path}: {exc}")
        return default
