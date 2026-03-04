from __future__ import annotations


class CombatDialogueController:
    def __init__(self, lore_engine, set_lines_fn):
        self.lore_engine = lore_engine
        self.set_lines_fn = set_lines_fn
        self.last_intent_key = ""

    def fire(self, enemy_id: str, trigger: str):
        e, c = self.lore_engine.get_combat_lines(enemy_id, trigger)
        self.set_lines_fn(e, c, trigger)

    def on_combat_start(self, enemy_id: str):
        self.fire(enemy_id, "start")

    def on_intent(self, enemy_id: str, intent_label: str):
        label = str(intent_label or "").lower()
        if "ata" in label:
            key = "intent_attack"
        elif "def" in label or "blo" in label:
            key = "intent_defend"
        else:
            key = "intent_other"
        if key != self.last_intent_key:
            self.last_intent_key = key
            self.fire(enemy_id, key)

    def on_player_low(self, enemy_id: str):
        self.fire(enemy_id, "player_low")

    def on_victory(self, enemy_id: str):
        self.fire(enemy_id, "victory")

    def on_defeat(self, enemy_id: str):
        self.fire(enemy_id, "defeat")
