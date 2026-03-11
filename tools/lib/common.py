from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / 'reports'


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace('\\', '/')
    except Exception:
        return str(path).replace('\\', '/')


def write_text_report(path: Path, title: str, lines: list[str]) -> Path:
    ensure_dir(path.parent)
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    body = [title, f'generated={stamp}', ''] + [str(x) for x in lines]
    path.write_text('\n'.join(body) + '\n', encoding='utf-8')
    return path


def write_json(path: Path, payload: dict) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return path
