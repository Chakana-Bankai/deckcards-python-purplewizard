from __future__ import annotations

from game.combat.actions import ActionQueue, ApplyStatus, DealDamage, GainBlock
from game.combat.card import CardDef, CardInstance
from game.combat.effects import interpret_effects
from game.combat.enemy import Enemy
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json


DEFAULT_CARDS = [
    {
        "id": "strike",
        "name_key": "card_strike_name",
        "text_key": "card_strike_desc",
        "rarity": "basic",
        "cost": 1,
        "target": "enemy",
        "tags": ["attack"],
        "effects": [{"type": "damage", "amount": 6}],
    },
    {
        "id": "defend",
        "name_key": "card_defend_name",
        "text_key": "card_defend_desc",
        "rarity": "basic",
        "cost": 1,
        "target": "self",
        "tags": ["skill"],
        "effects": [{"type": "block", "amount": 5}],
    },
]

DEFAULT_ENEMY = {
    "id": "dummy",
    "name_key": "enemy_voidling_name",
    "hp": [20, 20],
    "pattern": [{"intent": "attack", "value": [5, 5]}],
}


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
        self.start_line = rng.choice(["lore_short_1", "lore_short_2", "lore_short_3"]) or "lore_short_1"
        self.cards = self._load_cards()
        self.enemies = self._spawn_enemies(enemy_ids)
        deck_ids = run_state.get("deck", []) or ["strike"] * 5 + ["defend"] * 5
        self.draw_pile = [CardInstance(self.cards.get(card_id, self.cards["strike"])) for card_id in deck_ids]
        self.discard_pile = []
        self.hand = []
        self.exhaust_pile = []
        self.needs_target = None
        self.result = None
        self.screen_shake = 0.0
        self.combat_events = []
        self.start_player_turn()

    def _load_cards(self):
        raw = load_json(data_dir() / "cards.json", default=DEFAULT_CARDS)
        if not isinstance(raw, list):
            raw = DEFAULT_CARDS
        by_id = {}
        for entry in raw:
            try:
                card_def = CardDef(**entry)
                by_id[card_def.id] = card_def
            except Exception as exc:
                print(f"[combat] invalid card entry skipped: {exc}")
        for base in DEFAULT_CARDS:
            if base["id"] not in by_id:
                by_id[base["id"]] = CardDef(**base)
        return by_id

    def _spawn_enemies(self, enemy_ids):
        raw = load_json(data_dir() / "enemies.json", default=[DEFAULT_ENEMY])
        if not isinstance(raw, list) or not raw:
            raw = [DEFAULT_ENEMY]
        db = {}
        for entry in raw:
            if isinstance(entry, dict) and "id" in entry:
                db[entry["id"]] = entry
        if not db:
            db = {DEFAULT_ENEMY["id"]: DEFAULT_ENEMY}
        enemies = []
        for enemy_id in enemy_ids or [DEFAULT_ENEMY["id"]]:
            item = db.get(enemy_id, DEFAULT_ENEMY)
            hp_range = item.get("hp", [20, 20])
            min_hp = hp_range[0] if isinstance(hp_range, list) and hp_range else 20
            max_hp = hp_range[1] if isinstance(hp_range, list) and len(hp_range) > 1 else min_hp
            hp = self.rng.randint(min_hp, max_hp)
            pattern = item.get("pattern") or [{"intent": "attack", "value": [5, 5]}]
            enemies.append(Enemy(item.get("id", "dummy"), item.get("name_key", "enemy_voidling_name"), hp, hp, pattern))
        return enemies

    def start_player_turn(self):
        self.turn += 1
        self.combat_events.append({"type":"turn_start"})
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
            enemy.last_action_name = intent.get("name", intent.get("intent", "action"))
            intent_kind = intent.get("intent", "attack")
            if intent_kind == "attack":
                value = intent.get("value", [5, 5])
                low = value[0] if isinstance(value, list) else int(value)
                high = value[1] if isinstance(value, list) and len(value) > 1 else low
                self.queue.push(DealDamage(enemy, "player", self.rng.randint(low, high)))
            elif intent_kind == "defend":
                value = intent.get("value", [5, 5])
                low = value[0] if isinstance(value, list) else int(value)
                high = value[1] if isinstance(value, list) and len(value) > 1 else low
                self.queue.push(GainBlock(enemy, self.rng.randint(low, high)))
            elif intent_kind in {"debuff", "buff"}:
                target = "player" if intent_kind == "debuff" else enemy
                self.queue.push(ApplyStatus(target, intent.get("status", "weak"), intent.get("stacks", 1)))
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
            dealt = max(0, amount - blocked)
            self.player["hp"] -= dealt
            if dealt > 0:
                self.combat_events.append({"type":"damage","target":"player","amount":dealt})
        else:
            blocked = min(target.block, amount)
            target.block -= blocked
            dealt = max(0, amount - blocked)
            target.hp -= dealt
            if dealt > 0:
                self.combat_events.append({"type":"damage","target":target.id,"amount":dealt})
            if target.hp <= 0 and self.pending_if_kill:
                interpret_effects(self, CardInstance(self.cards["strike"]), target, self.pending_if_kill)
                self.pending_if_kill = None
        if amount >= 10:
            self.screen_shake = 0.25

    def gain_block(self, target, amount):
        if target == "player":
            self.player["block"] += amount
            self.combat_events.append({"type":"block","target":"player","amount":amount})
        else:
            target.block += amount
            self.combat_events.append({"type":"block","target":target.id,"amount":amount})

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
        self.combat_events.append({"type":"exhaust"})

    def discard_card(self, card):
        self.discard_pile.append(card)

    def pop_events(self):
        events = self.combat_events[:]
        self.combat_events.clear()
        return events
