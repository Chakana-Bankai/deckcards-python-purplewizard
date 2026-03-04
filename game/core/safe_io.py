"""Safe data loading with clear logs and defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Any


def load_json(path: Path, default, optional: bool = False, auto_create: Callable[[], Any] | None = None):
    try:
        if not path.exists():
            if optional:
                print(f"[safe_io] optional missing file: {path}")
            else:
                print(f"[safe_io] missing file: {path}")
            if auto_create is not None:
                try:
                    payload = auto_create()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("w", encoding="utf-8") as fh:
                        json.dump(payload, fh, ensure_ascii=False, indent=2)
                    return payload
                except Exception as exc:
                    print(f"[safe_io] failed auto-create {path}: {exc}")
            return default
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"[safe_io] invalid JSON in {path}: {exc}")
        return default
    except Exception as exc:
        print(f"[safe_io] failed loading {path}: {exc}")
        return default


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    tmp_path.replace(path)
