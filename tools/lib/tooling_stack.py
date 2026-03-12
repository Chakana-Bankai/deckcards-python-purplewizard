from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

ROOT = Path(__file__).resolve().parents[2]
console = Console(highlight=False)


class ToolCliSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    command: str
    dry_run: bool = False
    force: bool = False
    generate_all: bool = False


class ToolEnvSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    chakana_env: str = Field(default='development')
    reports_dir: str = Field(default='reports')
    rich_enabled: bool = Field(default=True)


def load_tool_env(root: Path | None = None) -> ToolEnvSpec:
    base = Path(root or ROOT)
    load_dotenv(base / '.env', override=False)
    load_dotenv(base / '.env.local', override=True)
    payload = {
        'chakana_env': __import__('os').environ.get('CHAKANA_ENV', 'development'),
        'reports_dir': __import__('os').environ.get('CHAKANA_REPORTS_DIR', 'reports'),
        'rich_enabled': str(__import__('os').environ.get('CHAKANA_RICH', '1')).strip().lower() not in {'0', 'false', 'no'},
    }
    return ToolEnvSpec(**payload)


def validate_cli_payload(payload: dict[str, Any]) -> ToolCliSpec:
    return ToolCliSpec(**payload)


def render_report_path(label: str, report_path: Path) -> None:
    console.print(f'[green][{label}][/green] report={report_path}')
