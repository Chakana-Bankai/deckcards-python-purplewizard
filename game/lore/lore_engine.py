from __future__ import annotations

import json
import random
from pathlib import Path

from game.core.safe_io import load_json


class LoreEngine:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.base = self.project_root / "game" / "data" / "lore"
        self.map_narration = {}
        self.combat_dialogues = {}
        self.combat_event_dialogues = {}
        self.loaded_map = False
        self.loaded_combat = False
        self.loaded = False
        self.last_trigger = "-"
        self.keys_count = 0
        self._line_memory: dict[str, str] = {}
        self.load_all()

    def _load_alias(self, primary: str, fallback: str):
        primary_path = self.base / primary
        data = load_json(primary_path, default=None)
        if isinstance(data, dict):
            return data
        fallback_path = self.base / fallback
        data = load_json(fallback_path, default={})
        return data if isinstance(data, dict) else {}

    def _load_event_dialogues(self) -> dict:
        path = self.project_root / "game" / "data" / "combat_dialogue.json"
        data = load_json(path, default={})
        return data if isinstance(data, dict) else {}

    def load_all(self):
        self.map_narration = self._load_alias("map_narration.json", "dialogues_events.json")
        self.combat_dialogues = self._load_alias("combat_dialogues.json", "dialogues_combat.json")
        self.combat_event_dialogues = self._load_event_dialogues()
        self.keys_count = len(self.combat_dialogues)
        self.loaded_map = bool(self.map_narration)
        self.loaded_combat = bool(self.combat_dialogues) or bool(self.combat_event_dialogues)
        self.loaded = self.loaded_map and self.loaded_combat
        print(
            f"[load] map_narration={'OK' if self.loaded_map else 'MISSING'} "
            f"combat_dialogues={'OK' if self.loaded_combat else 'MISSING'}"
        )

    def get_map_narration(self, key: str = "default") -> str:
        item = self.map_narration.get(key, self.map_narration.get("default", []))
        if isinstance(item, list) and item:
            return str(item[0])
        if isinstance(item, str):
            return item
        return "La Trama murmura entre rutas."

    def _pick_from_pool(self, event_key: str, speaker: str, fallback: str) -> str:
        event_item = self.combat_event_dialogues.get(event_key, {}) if isinstance(self.combat_event_dialogues, dict) else {}
        pool = event_item.get(speaker, []) if isinstance(event_item, dict) else []
        if isinstance(pool, str):
            pool = [pool]
        choices = [str(x).strip() for x in pool if str(x).strip()]
        if not choices:
            return fallback
        mem_key = f"{event_key}:{speaker}"
        prev = self._line_memory.get(mem_key)
        if len(choices) > 1 and prev in choices:
            choices = [c for c in choices if c != prev] or choices
        line = random.choice(choices)
        self._line_memory[mem_key] = line
        return line

    def get_combat_lines(self, enemy_id: str, trigger: str) -> tuple[str, str]:
        self.last_trigger = trigger
        item = self.combat_dialogues.get(enemy_id, self.combat_dialogues.get("default", {}))
        aliases = {
            "combat_start": "start",
            "enemy_big_attack": "enemy_attack_big",
            "player_low_hp": "player_low",
            "enemy_low_hp": "enemy_low",
            "seal_ready": "harmony_ready",
            "seal_release": "harmony_seal",
        }

        trig = item.get(trigger, item.get(aliases.get(trigger, ""), {})) if isinstance(item, dict) else {}
        if not isinstance(trig, dict):
            trig = item.get("start", {}) if isinstance(item, dict) else {}

        enemy_fallback = trig.get("enemy", "La Trama te prueba.") if isinstance(trig, dict) else "La Trama te prueba."
        hero_fallback = trig.get("chakana", "Respiro. Calculo. Ejecuto.") if isinstance(trig, dict) else "Respiro. Calculo. Ejecuto."

        enemy = self._pick_from_pool(trigger, "enemy", str(enemy_fallback))
        hero = self._pick_from_pool(trigger, "chakana", str(hero_fallback))
        return str(enemy), str(hero)

    def get_lines(self, enemy_id: str, trigger: str) -> tuple[str, str]:
        return self.get_combat_lines(enemy_id, trigger)
