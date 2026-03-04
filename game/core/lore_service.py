from __future__ import annotations

import os
from pathlib import Path

from game.core.paths import data_dir
from game.core.safe_io import load_json


class LoreService:
    def __init__(self):
        project_root = Path(__file__).resolve().parents[2]
        lore_base = project_root / "game" / "data" / "lore"
        if not lore_base.exists():
            lore_base = data_dir() / "lore"
        self.base = lore_base
        self.paths = {
            "world": self.base / "world.txt",
            "dialogues": self.base / "dialogues.json",
            "events": self.base / "events.json",
            "enemies": self.base / "enemies.json",
            "dialogues_combat": self.base / "dialogues_combat.json",
            "dialogues_events": self.base / "dialogues_events.json",
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
            "dialogues_combat": {},
            "dialogues_events": {},
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

        events = load_json(self.paths["events"], default={})
        if isinstance(events, dict):
            fr = events.get("fragments", [])
            if isinstance(fr, list) and fr:
                payload["event_fragments"] = fr

        enemies = load_json(self.paths["enemies"], default={})
        if isinstance(enemies, dict):
            payload["enemy_lore"] = enemies

        dcombat = load_json(self.paths["dialogues_combat"], default={})
        devents = load_json(self.paths["dialogues_events"], default={})
        payload["dialogues_combat"] = dcombat if isinstance(dcombat, dict) else {}
        payload["dialogues_events"] = devents if isinstance(devents, dict) else {}

        triggers = set()
        enemies = 0
        if isinstance(payload["dialogues_combat"], dict):
            for k, v in payload["dialogues_combat"].items():
                if isinstance(v, dict):
                    enemies += 1
                    triggers.update(v.keys())
        print(f"[load] dialogues_combat OK triggers={len(triggers)} enemies={enemies}")

        if self.missing:
            self.status = "MISSING"
        return payload

    def dialogue(self, side: str, trigger: str, enemy_id: str) -> list[str]:
        if side == "enemy":
            src = self.data.get("enemy", {}).get(enemy_id, {})
            return src.get(trigger, []) if isinstance(src, dict) else []
        return self.data.get("chakana", {}).get(trigger, []) if isinstance(self.data.get("chakana", {}), dict) else []

    def emit(self, trigger: str, enemy_id: str, context: dict | None = None) -> tuple[str, str]:
        dc = self.data.get("dialogues_combat", {}) if isinstance(self.data.get("dialogues_combat", {}), dict) else {}
        item = dc.get(enemy_id, dc.get("default", {})) if isinstance(dc, dict) else {}
        aliases = {"combat_start": "start", "enemy_big_attack": "enemy_attack_big"}
        trig = item.get(trigger, item.get(aliases.get(trigger, ""), {})) if isinstance(item, dict) else {}
        if not isinstance(trig, dict):
            trig = item.get("start", {}) if isinstance(item, dict) else {}
        enemy = trig.get("enemy", "La Trama te prueba.") if isinstance(trig, dict) else "La Trama te prueba."
        hero = trig.get("chakana", "Respiro. Calculo. Ejecuto.") if isinstance(trig, dict) else "Respiro. Calculo. Ejecuto."
        return str(enemy), str(hero)
