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
    def __init__(self, rng: SeededRNG, run_state: dict, enemy_ids: list[str], cards_data: list[dict] | None = None, enemies_data: list[dict] | None = None):
        self.rng = rng
        self.run_state = run_state
        self.queue = ActionQueue()
        self.player = run_state["player"]
        self.player.setdefault("statuses", {})
        self.player.setdefault("harmony_current", 0)
        self.player.setdefault("harmony_max", 10)
        self.player.setdefault("harmony_ready_threshold", 6)
        self.player.setdefault("harmony_ready", False)
        self.player["block"] = 0
        self.turn = 0
        self.pending_if_kill = None
        self.start_line_time = 2.0
        self.start_line = rng.choice(["lore_short_1", "lore_short_2", "lore_short_3"]) or "lore_short_1"
        self.cards = self._load_cards(cards_data)
        self.enemies = self._spawn_enemies(enemy_ids, enemies_data)
        first_id = next(iter(self.cards.keys()))
        deck_ids = run_state.get("deck", []) or [first_id] * 10
        self.draw_pile = [CardInstance(self.cards.get(card_id, self.cards[first_id])) for card_id in deck_ids]
        self.discard_pile = []
        self.hand = []
        self.exhaust_pile = []
        self.needs_target = None
        self.result = None
        self.screen_shake = 0.0
        self.combat_events = []
        self.scry_pending = []
        self.player_damage_taken = 0
        self.harmony_last3 = []
        self.harmony_chaos_pending = False
        self.harmony_focus_damage_bonus = 0
        self.next_turn_bonus_energy = 0
        self.last_played_card = None
        self.baston_used = False
        self.start_player_turn()

    def _load_cards(self, cards_data=None):
        raw = cards_data if cards_data else load_json(data_dir() / "cards.json", default=DEFAULT_CARDS)
        if not isinstance(raw, list):
            raw = DEFAULT_CARDS
        by_id = {}
        for entry in raw:
            try:
                card_def = CardDef(**entry)
                by_id[card_def.id] = card_def
            except Exception as exc:
                print(f"[combat] invalid card entry skipped: {exc}")
        if not by_id:
            for base in DEFAULT_CARDS:
                if base["id"] not in by_id:
                    by_id[base["id"]] = CardDef(**base)
        return by_id

    def _spawn_enemies(self, enemy_ids, enemies_data=None):
        raw = enemies_data if enemies_data else load_json(data_dir() / "enemies.json", default=[DEFAULT_ENEMY])
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
            en = Enemy(item.get("id", "dummy"), item.get("name_key", "enemy_voidling_name"), hp, hp, pattern)
            en.fable_lesson_key = item.get("fable_lesson_key", "duda")
            enemies.append(en)
        return enemies

    def start_player_turn(self):
        self.turn += 1
        self.combat_events.append({"type":"turn_start"})
        self.player["energy"] = 3 + self.next_turn_bonus_energy + (1 if self.player["statuses"].get("energized", 0) > 0 else 0)
        self.next_turn_bonus_energy = 0
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
        extra_cost = 1 if self.harmony_chaos_pending else 0
        if card.definition.tags and "attack" in card.definition.tags and self.player["statuses"].get("discount_next_attack",0)>0:
            extra_cost = max(0, extra_cost-1)
            self.player["statuses"]["discount_next_attack"] = max(0,self.player["statuses"].get("discount_next_attack",0)-1)
        if card.cost + extra_cost > self.player["energy"]:
            return
        if card.definition.target == "enemy":
            if target_idx is None or target_idx >= len(self.enemies) or not self.enemies[target_idx].alive:
                self.needs_target = hand_index
                return
            target = self.enemies[target_idx]
        else:
            target = self.enemies[0] if self.enemies else None
        self.player["energy"] -= (card.cost + extra_cost)
        if self.harmony_chaos_pending:
            self.harmony_chaos_pending = False
        self.hand.pop(hand_index)
        self._track_harmony(card.definition.direction if hasattr(card.definition, "direction") else "ESTE")
        self._apply_harmony_resource(card)
        interpret_effects(self, card, target, card.definition.effects)
        self.combat_events.append({"type": "card_played", "card_id": getattr(card.definition, "id", "-")})
        self.last_played_card = card
        if self.player["statuses"].get("copy_next",0)>0:
            self.player["statuses"]["copy_next"] = 0
            interpret_effects(self, card, target, card.definition.effects)
        if card not in self.exhaust_pile:
            self.discard_pile.append(card)

    def _apply_harmony_resource(self, card):
        effects = list(getattr(getattr(card, "definition", None), "effects", []) or [])
        delta = 1
        consume = 0
        for ef in effects:
            if not isinstance(ef, dict):
                continue
            t = str(ef.get("type", "")).lower()
            if t == "harmony_delta":
                delta += int(ef.get("amount", 0) or 0)
            elif t == "consume_harmony":
                consume += max(1, int(ef.get("amount", 1) or 1))

        cur = int(self.player.get("harmony_current", 0) or 0)
        mx = max(1, int(self.player.get("harmony_max", 10) or 10))
        cur = max(0, min(mx, cur + delta - consume))
        self.player["harmony_current"] = cur

        thr = max(1, int(self.player.get("harmony_ready_threshold", 6) or 6))
        was_ready = bool(self.player.get("harmony_ready", False))
        now_ready = cur >= thr
        self.player["harmony_ready"] = now_ready
        if now_ready and not was_ready:
            self.combat_events.append({"type": "harmony_ready", "message": "Armonía lista: desata tu sello."})

    def end_turn(self):
        kept = [c for c in self.hand if getattr(c, "retain_flag", False)]
        for c in kept:
            c.retain_flag = False
        self.discard_pile.extend([c for c in self.hand if c not in kept])
        self.hand = kept
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
            elif intent_kind == "break":
                self.player["rupture"] += int(intent.get("stacks", 1))
            elif intent_kind == "heal":
                enemy.hp = min(enemy.max_hp, enemy.hp + int(intent.get("stacks", 1)))
            elif intent_kind == "channel":
                pass
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
        if source == "player" and self.harmony_focus_damage_bonus > 0:
            amount += self.harmony_focus_damage_bonus
            self.harmony_focus_damage_bonus = 0
        if target == "player":
            weakv = self.player["statuses"].get("enemy_damage_down",0)
            if weakv > 0:
                amount = max(0, amount - weakv)
                self.player["statuses"]["enemy_damage_down"] = max(0, weakv-1)
            if self.player["statuses"].get("phase", 0) > 0:
                amount = amount // 2
                self.remove_status("player", "phase", 1)
            blocked = min(self.player["block"], amount)
            self.player["block"] -= blocked
            dealt = max(0, amount - blocked)
            self.player["hp"] -= dealt
            if dealt > 0:
                self.player_damage_taken += dealt
                self.combat_events.append({"type":"damage","target":"player","amount":dealt})
        else:
            if getattr(target, "statuses", {}).get("vulnerable",0) > 0:
                amount += target.statuses.get("vulnerable",0)
                target.statuses["vulnerable"] = max(0,target.statuses.get("vulnerable",0)-1)
            blocked = min(target.block, amount)
            target.block -= blocked
            dealt = max(0, amount - blocked)
            target.hp -= dealt
            if dealt > 0:
                self.combat_events.append({"type":"damage","target":target.id,"amount":dealt})
            if target.hp <= 0 and self.pending_if_kill:
                first_id = next(iter(self.cards.keys()))
                interpret_effects(self, CardInstance(self.cards[first_id]), target, self.pending_if_kill)
                self.pending_if_kill = None
        if amount >= 10:
            self.screen_shake = 0.25

    def gain_block(self, target, amount):
        if target == "player":
            weakv = self.player["statuses"].get("enemy_damage_down",0)
            if weakv > 0:
                amount = max(0, amount - weakv)
                self.player["statuses"]["enemy_damage_down"] = max(0, weakv-1)
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


    def begin_scry(self, amount: int):
        n = max(0, min(amount, len(self.draw_pile)))
        self.scry_pending = list(self.draw_pile[-n:])[::-1]
        self.combat_events.append({"type": "scry", "amount": n})

    def apply_scry_order(self, ordered_cards):
        n = len(ordered_cards)
        if n <= 0:
            self.scry_pending = []
            return
        self.draw_pile = self.draw_pile[:-n] + list(ordered_cards[::-1])
        self.scry_pending = []

    def apply_scry_keep(self, keep_card):
        pending = list(self.scry_pending or [])
        if not pending:
            self.scry_pending = []
            return
        keep = keep_card if keep_card in pending else pending[0]
        rest = [c for c in pending if c is not keep]
        n = len(pending)
        self.draw_pile = self.draw_pile[:-n]
        for c in rest:
            self.discard_pile.append(c)
        self.draw_pile.append(keep)
        self.scry_pending = []

    def _track_harmony(self, direction: str):
        d = (direction or "ESTE").upper()
        self.harmony_last3.append(d)
        self.harmony_last3 = self.harmony_last3[-3:]
        if len(self.harmony_last3) < 3:
            return
        a,b,c = self.harmony_last3
        if len(set(self.harmony_last3)) == 3:
            self.next_turn_bonus_energy += 1
            self.player["block"] += 2
            self.combat_events.append({"type":"harmony","kind":"BALANCE"})
        elif a == b == c:
            if a == "ESTE":
                self.harmony_focus_damage_bonus += 3
            elif a == "SUR":
                self.player["block"] += 4
            elif a == "NORTE":
                self.draw(1)
            elif a == "OESTE":
                alive = next((e for e in self.enemies if e.alive), None)
                if alive:
                    alive.statuses["break"] = alive.statuses.get("break",0)+1
                self.heal_player(1)
            self.combat_events.append({"type":"harmony","kind":"FOCUS","direction":a})
        elif a == c and a != b:
            self.harmony_chaos_pending = True
            self.combat_events.append({"type":"harmony","kind":"CHAOS"})

    def pop_events(self):
        events = self.combat_events[:]
        self.combat_events.clear()
        return events
