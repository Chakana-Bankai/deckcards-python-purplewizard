"""Safe data loading with clear logs and defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


_WARNED_IO: set[str] = set()


def _log_once(key: str, message: str):
    if key in _WARNED_IO:
        return
    _WARNED_IO.add(key)
    print(message)


def load_json(path: Path, default, optional: bool = False, auto_create: Callable[[], Any] | None = None):
    try:
        if not path.exists():
            if optional:
                _log_once(f"optional_missing:{path}", f"[safe_io] optional missing file: {path}")
            else:
                _log_once(f"missing:{path}", f"[safe_io] missing file: {path}")
            if auto_create is not None:
                try:
                    payload = auto_create()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("w", encoding="utf-8") as fh:
                        json.dump(payload, fh, ensure_ascii=False, indent=2)
                    return payload
                except Exception as exc:
                    _log_once(f"autocreate_fail:{path}", f"[safe_io] failed auto-create {path}: {exc}")
            return default
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        _log_once(f"invalid_json:{path}", f"[safe_io] invalid JSON in {path}: {exc}")
        return default
    except Exception as exc:
        _log_once(f"load_fail:{path}", f"[safe_io] failed loading {path}: {exc}")
        return default


def _json_bytes(payload: Any, *, sort_keys: bool = True) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=sort_keys)
    if not text.endswith("\n"):
        text += "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with tmp_path.open("wb") as fh:
        fh.write(_json_bytes(payload, sort_keys=True))
    tmp_path.replace(path)


def atomic_write_json_if_changed(path: Path, payload: Any, *, sort_keys: bool = True) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_bytes = _json_bytes(payload, sort_keys=sort_keys)
    if path.exists():
        try:
            if path.read_bytes() == new_bytes:
                return False
        except Exception:
            pass
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp_path.write_bytes(new_bytes)
    tmp_path.replace(path)
    return True
