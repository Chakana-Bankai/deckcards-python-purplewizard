from __future__ import annotations

import json
from pathlib import Path

from game.combat.actions import ActionQueue, DealDamage, GainBlock, ApplyStatus
from game.combat.card import CardDef, CardInstance
from game.combat.effects import interpret_effects
from game.combat.enemy import Enemy
from game.core.rng import SeededRNG
from game.settings import DATA_DIR


class CombatState:
    def __init__(self, rng: SeededRNG, run_state: dict, enemy_ids: list[str]):
        self.rng = rng
        self.run_state = run_state
        self.queue = ActionQueue()
        self.player = run_state["player"]
        self.player.setdefault("statuses", {})
        self.player["block"] = 0
        self.turn = 0
        self.pending_if_kill = None
        self.start_line_time = 2.0
        self.start_line = rng.choice(["lore_short_1", "lore_short_2", "lore_short_3"])
        self.cards = self._load_cards()
        self.enemies = self._spawn_enemies(enemy_ids)
        self.draw_pile = [CardInstance(self.cards[cid]) for cid in run_state["deck"]]
        self.discard_pile = []
        self.hand = []
        self.exhaust_pile = []
        self.needs_target = None
        self.result = None
        self.screen_shake = 0.0
        self.start_player_turn()

    def _load_cards(self):
        raw = json.loads((Path(DATA_DIR) / "cards.json").read_text(encoding="utf-8"))
        return {c["id"]: CardDef(**c) for c in raw}

    def _spawn_enemies(self, ids):
        db = {e["id"]: e for e in json.loads((Path(DATA_DIR) / "enemies.json").read_text(encoding="utf-8"))}
        enemies = []
        for eid in ids:
            item = db[eid]
            hp = self.rng.randint(item["hp"][0], item["hp"][1])
            enemies.append(Enemy(eid, item["name_key"], hp, hp, item["pattern"]))
        return enemies

    def start_player_turn(self):
        self.turn += 1
        self.player["energy"] = 3 + (1 if self.player["statuses"].get("energized", 0) > 0 else 0)
        self.player["block"] = 0
        self.draw(5)

    def draw(self, n):
        for _ in range(n):
            if not self.draw_pile:
                self.draw_pile = self.discard_pile
                self.discard_pile = []
                self.rng.shuffle(self.draw_pile)
            if self.draw_pile:
                self.hand.append(self.draw_pile.pop())

    def play_card(self, hand_index: int, target_idx: int | None = None):
        if hand_index < 0 or hand_index >= len(self.hand):
            return
        card = self.hand[hand_index]
        if card.cost > self.player["energy"]:
            return
        if card.definition.target == "enemy":
            if target_idx is None or target_idx >= len(self.enemies) or not self.enemies[target_idx].alive:
                self.needs_target = hand_index
                return
            target = self.enemies[target_idx]
        else:
            target = self.enemies[0] if self.enemies else None
        self.player["energy"] -= card.cost
        self.hand.pop(hand_index)
        interpret_effects(self, card, target, card.definition.effects)
        if card not in self.exhaust_pile:
            self.discard_pile.append(card)

    def end_turn(self):
        self.discard_pile.extend(self.hand)
        self.hand.clear()
        self.enemy_turn()
        if self.result is None:
            self.start_player_turn()

    def enemy_turn(self):
        self.player["block"] = 0
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            intent = enemy.current_intent()
            if intent["intent"] == "attack":
                val = self.rng.randint(intent["value"][0], intent["value"][1])
                self.queue.push(DealDamage(enemy, "player", val))
            elif intent["intent"] == "defend":
                val = self.rng.randint(intent["value"][0], intent["value"][1])
                self.queue.push(GainBlock(enemy, val))
            elif intent["intent"] in {"debuff", "buff"}:
                self.queue.push(ApplyStatus("player" if intent["intent"] == "debuff" else enemy, intent["status"], intent["stacks"]))
            enemy.advance_intent()

    def update(self, dt):
        self.start_line_time = max(0.0, self.start_line_time - dt)
        self.queue.update(self)
        if self.screen_shake > 0:
            self.screen_shake = max(0, self.screen_shake - dt)
        if all(not e.alive for e in self.enemies):
            self.result = "victory"
        if self.player["hp"] <= 0:
            self.result = "defeat"

    def deal_damage(self, source, target, amount):
        if source == "player" and self.player["statuses"].get("weak", 0) > 0:
            amount = int(amount * 0.75)
        if target == "player":
            if self.player["statuses"].get("phase", 0) > 0:
                amount = amount // 2
                self.remove_status("player", "phase", 1)
            blocked = min(self.player["block"], amount)
            self.player["block"] -= blocked
            self.player["hp"] -= max(0, amount - blocked)
        else:
            blocked = min(target.block, amount)
            target.block -= blocked
            target.hp -= max(0, amount - blocked)
            if target.hp <= 0 and self.pending_if_kill:
                from game.combat.effects import interpret_effects
                interpret_effects(self, CardInstance(self.cards["strike"]), target, self.pending_if_kill)
                self.pending_if_kill = None
        if amount >= 10:
            self.screen_shake = 0.25

    def gain_block(self, target, amount):
        if target == "player":
            self.player["block"] += amount
        else:
            target.block += amount

    def apply_status(self, target, name, stacks):
        status_pool = self.player["statuses"] if target == "player" else target.statuses
        status_pool[name] = status_pool.get(name, 0) + stacks

    def remove_status(self, target, name, stacks=None):
        status_pool = self.player["statuses"] if target == "player" else target.statuses
        if name not in status_pool:
            return
        if stacks is None:
            status_pool.pop(name, None)
        else:
            status_pool[name] -= stacks
            if status_pool[name] <= 0:
                status_pool.pop(name, None)

    def heal_player(self, amount):
        self.player["hp"] = min(self.player["max_hp"], self.player["hp"] + amount)

    def exhaust_card(self, card):
        if card in self.discard_pile:
            self.discard_pile.remove(card)
        self.exhaust_pile.append(card)

    def discard_card(self, card):
        self.discard_pile.append(card)
