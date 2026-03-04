from __future__ import annotations

import json
from pathlib import Path

from game.core.safe_io import load_json


class LoreEngine:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.base = self.project_root / "game" / "data" / "lore"
        self.map_narration = {}
        self.combat_dialogues = {}
        self.loaded_map = False
        self.loaded_combat = False
        self.loaded = False
        self.last_trigger = "-"
        self.keys_count = 0
        self.load_all()

    def _load_alias(self, primary: str, fallback: str):
        primary_path = self.base / primary
        data = load_json(primary_path, default=None)
        if isinstance(data, dict):
            return data
        fallback_path = self.base / fallback
        data = load_json(fallback_path, default={})
        return data if isinstance(data, dict) else {}

    def load_all(self):
        self.map_narration = self._load_alias("map_narration.json", "dialogues_events.json")
        self.combat_dialogues = self._load_alias("combat_dialogues.json", "dialogues_combat.json")
        self.keys_count = len(self.combat_dialogues)
        self.loaded_map = bool(self.map_narration)
        self.loaded_combat = bool(self.combat_dialogues)
        self.loaded = self.loaded_map and self.loaded_combat
        print(f"[load] map_narration={'OK' if self.loaded_map else 'MISSING'} combat_dialogues={'OK' if self.loaded_combat else 'MISSING'}")

    def get_map_narration(self, key: str = "default") -> str:
        item = self.map_narration.get(key, self.map_narration.get("default", []))
        if isinstance(item, list) and item:
            return str(item[0])
        if isinstance(item, str):
            return item
        return "La Trama murmura entre rutas."

    def get_combat_lines(self, enemy_id: str, trigger: str) -> tuple[str, str]:
        self.last_trigger = trigger
        item = self.combat_dialogues.get(enemy_id, self.combat_dialogues.get("default", {}))
        aliases = {"combat_start": "start", "enemy_big_attack": "enemy_attack_big"}
        trig = item.get(trigger, item.get(aliases.get(trigger, ""), {})) if isinstance(item, dict) else {}
        if not isinstance(trig, dict):
            trig = item.get("start", {}) if isinstance(item, dict) else {}
        enemy = trig.get("enemy", "La Trama te prueba.") if isinstance(trig, dict) else "La Trama te prueba."
        hero = trig.get("chakana", "Respiro. Calculo. Ejecuto.") if isinstance(trig, dict) else "Respiro. Calculo. Ejecuto."
        return str(enemy), str(hero)

    def get_lines(self, enemy_id: str, trigger: str) -> tuple[str, str]:
        return self.get_combat_lines(enemy_id, trigger)
