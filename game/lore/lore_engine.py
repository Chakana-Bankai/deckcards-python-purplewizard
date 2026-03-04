from __future__ import annotations

from pathlib import Path

from game.core.safe_io import load_json


class LoreEngine:
    def __init__(self, project_root: Path):
        self.base = project_root / "game" / "data" / "lore"
        self.dialogues_combat = {}
        self.dialogues_events = {}
        self.loaded = False
        self.last_trigger = "-"
        self.keys_count = 0
        self.load_all()

    def load_all(self):
        dcombat = load_json(self.base / "dialogues_combat.json", default={})
        devents = load_json(self.base / "dialogues_events.json", default={})
        self.dialogues_combat = dcombat if isinstance(dcombat, dict) else {}
        self.dialogues_events = devents if isinstance(devents, dict) else {}
        self.keys_count = len(self.dialogues_combat)
        self.loaded = bool(self.dialogues_combat)
        triggers = set()
        enemies = 0
        for _, v in self.dialogues_combat.items():
            if isinstance(v, dict):
                enemies += 1
                triggers.update(v.keys())
        print(f"[load] dialogues_combat OK triggers={len(triggers)} enemies={enemies}")

    def get_lines(self, enemy_id: str, trigger: str) -> tuple[str, str]:
        self.last_trigger = trigger
        item = self.dialogues_combat.get(enemy_id, self.dialogues_combat.get("default", {}))
        aliases = {"combat_start": "start", "enemy_big_attack": "enemy_attack_big"}
        trig = item.get(trigger, item.get(aliases.get(trigger, ""), {})) if isinstance(item, dict) else {}
        if not isinstance(trig, dict):
            trig = item.get("start", {}) if isinstance(item, dict) else {}
        enemy = trig.get("enemy", "La Trama te prueba.") if isinstance(trig, dict) else "La Trama te prueba."
        hero = trig.get("chakana", "Respiro. Calculo. Ejecuto.") if isinstance(trig, dict) else "Respiro. Calculo. Ejecuto."
        return str(enemy), str(hero)
