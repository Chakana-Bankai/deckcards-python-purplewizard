from __future__ import annotations

from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json


class LoreService:
    def __init__(self):
        self.base = data_dir() / "lore"
        self.paths = {
            "world": self.base / "world.txt",
            "dialogues": self.base / "dialogues.json",
            "events": self.base / "events.json",
            "enemies": self.base / "enemies.json",
        }
        self.status = "OK"
        self.missing: list[str] = []
        self.data = self._load()

    def _load(self) -> dict:
        payload = {
            "world_text": "",
            "enemy": {},
            "chakana": {},
            "event_fragments": ["El guía espera tu elección."],
            "enemy_lore": {},
        }
        try:
            payload["world_text"] = self.paths["world"].read_text(encoding="utf-8").strip()
        except Exception:
            self.missing.append(str(self.paths["world"]))

        dialogs = load_json(self.paths["dialogues"], default={})
        if isinstance(dialogs, dict):
            payload["enemy"] = dialogs.get("enemy", {}) if isinstance(dialogs.get("enemy", {}), dict) else {}
            payload["chakana"] = dialogs.get("chakana", {}) if isinstance(dialogs.get("chakana", {}), dict) else {}
            payload["ending_lines"] = dialogs.get("ending_lines", [])
        else:
            self.missing.append(str(self.paths["dialogues"]))

        events = load_json(self.paths["events"], default={})
        if isinstance(events, dict):
            fr = events.get("fragments", [])
            if isinstance(fr, list) and fr:
                payload["event_fragments"] = fr
        else:
            self.missing.append(str(self.paths["events"]))

        enemies = load_json(self.paths["enemies"], default={})
        if isinstance(enemies, dict):
            payload["enemy_lore"] = enemies
        else:
            self.missing.append(str(self.paths["enemies"]))

        if self.missing:
            self.status = "MISSING"
        return payload

    def dialogue(self, side: str, trigger: str, enemy_id: str) -> list[str]:
        if side == "enemy":
            src = self.data.get("enemy", {}).get(enemy_id, {})
            return src.get(trigger, []) if isinstance(src, dict) else []
        return self.data.get("chakana", {}).get(trigger, []) if isinstance(self.data.get("chakana", {}), dict) else []
