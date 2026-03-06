from __future__ import annotations

from game.combat.actions import ActionQueue, ApplyStatus, DealDamage, GainBlock
from game.combat.card import CardDef, CardInstance
from game.combat.effects import interpret_effects
from game.combat.enemy import Enemy
from game.core.paths import data_dir
from game.core.rng import SeededRNG
from game.core.safe_io import load_json
from game.telemetry.logger import TelemetryLogger


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
        self.player.setdefault("harmony_seal_used", False)
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
        self.balance = self._load_balance_config()
        self.energy_per_turn = int(self.balance.get("energy_per_turn", 3) or 3)
        self.draw_per_turn = int(self.balance.get("draw_per_turn", 3) or 3)
        self.hand_max = int(self.balance.get("hand_max", 6) or 6)
        self.ui_cooldown_ms = int(self.balance.get("ui_cooldown_ms", 200) or 200)
        self.fatigue_enabled = bool(self.balance.get("fatigue_enabled", True))
        self.fatigue_start = int(self.balance.get("fatigue_start", 1) or 1)
        self.fatigue_growth = int(self.balance.get("fatigue_growth", 1) or 1)
        self.fatigue_counter = 0
        self.telemetry = TelemetryLogger("INFO")
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

    def _load_balance_config(self):
        raw = load_json(data_dir() / "balance" / "combat.json", default={})
        if not isinstance(raw, dict):
            raw = {}
        return {
            "energy_per_turn": int(raw.get("energy_per_turn", 3) or 3),
            "draw_per_turn": int(raw.get("draw_per_turn", 3) or 3),
            "hand_max": int(raw.get("hand_max", 6) or 6),
            "ui_cooldown_ms": int(raw.get("ui_cooldown_ms", 200) or 200),
            "fatigue_enabled": bool(raw.get("fatigue_enabled", True)),
            "fatigue_start": int(raw.get("fatigue_start", 1) or 1),
            "fatigue_growth": int(raw.get("fatigue_growth", 1) or 1),
        }

    def start_player_turn(self):
        self.turn += 1
        self.combat_events.append({"type":"turn_start"})
        self.player["energy"] = self.energy_per_turn + self.next_turn_bonus_energy + (1 if self.player["statuses"].get("energized", 0) > 0 else 0)
        self.next_turn_bonus_energy = 0
        self.player["block"] = 0
        if self.fatigue_enabled and self.fatigue_counter > 0:
            fatigue_dmg = self.fatigue_start + max(0, self.fatigue_counter - 1) * self.fatigue_growth
            self.player["hp"] = max(0, int(self.player.get("hp", 0)) - fatigue_dmg)
            self.combat_events.append({"type": "fatigue", "amount": fatigue_dmg, "counter": self.fatigue_counter})
            self.telemetry.info("fatigue_tick", amount=fatigue_dmg, counter=self.fatigue_counter, hp=self.player.get("hp", 0))
        self.draw(self.draw_per_turn)

    def draw(self, n):
        for _ in range(max(0, int(n or 0))):
            if len(self.hand) >= self.hand_max:
                self.combat_events.append({"type": "draw_skipped", "reason": "hand_full", "hand": len(self.hand)})
                break
            if not self.draw_pile:
                if self.discard_pile:
                    self.draw_pile = self.discard_pile
                    self.discard_pile = []
                    self.rng.shuffle(self.draw_pile)
                    if self.fatigue_enabled:
                        self.fatigue_counter += 1
                        self.telemetry.info("fatigue_reshuffle", fatigue_counter=self.fatigue_counter)
                else:
                    self.result = "defeat"
                    self.combat_events.append({"type": "deck_empty", "message": "Derrota: tu mazo se ha vaciado."})
                    self.telemetry.info("deck_empty_defeat", draw=0, discard=0)
                    break
            if self.draw_pile and len(self.hand) < self.hand_max:
                self.hand.append(self.draw_pile.pop())

    def play_card(self, hand_index: int, target_idx: int | None = None):
        if hand_index < 0 or hand_index >= len(self.hand):
            return
        card = self.hand[hand_index]
        play_cost = int(card.cost or 0)
        if card.definition.tags and "attack" in card.definition.tags and self.player["statuses"].get("discount_next_attack", 0) > 0:
            play_cost = max(0, play_cost - 1)
            self.player["statuses"]["discount_next_attack"] = max(0, self.player["statuses"].get("discount_next_attack", 0) - 1)
        if play_cost > self.player["energy"]:
            return
        if card.definition.target == "enemy":
            if target_idx is None or target_idx >= len(self.enemies) or not self.enemies[target_idx].alive:
                self.needs_target = hand_index
                return
            target = self.enemies[target_idx]
        else:
            target = self.enemies[0] if self.enemies else None
        self.player["energy"] -= play_cost
        if self.harmony_chaos_pending:
            self.harmony_chaos_pending = False
        self.hand.pop(hand_index)
        harmony_packet = self.resolve_harmony_packet(card)
        self._track_harmony(card.definition.direction if hasattr(card.definition, "direction") else "ESTE")
        interpret_effects(self, card, target, card.definition.effects)
        self.apply_harmony_packet(harmony_packet, source=getattr(card.definition, "id", "card"))
        self.combat_events.append({"type": "card_played", "card_id": getattr(card.definition, "id", "-")})
        self.last_played_card = card
        if self.player["statuses"].get("copy_next",0)>0:
            self.player["statuses"]["copy_next"] = 0
            interpret_effects(self, card, target, card.definition.effects)
        if card not in self.exhaust_pile:
            self.discard_pile.append(card)

    def gain_harmony(self, amount: int):
        add = max(0, int(amount or 0))
        cur = int(self.player.get("harmony_current", 0) or 0)
        mx = max(1, int(self.player.get("harmony_max", 10) or 10))
        cur = max(0, min(mx, cur + add))
        self.player["harmony_current"] = cur
        thr = max(1, int(self.player.get("harmony_ready_threshold", 6) or 6))
        was_ready = bool(self.player.get("harmony_ready", False))
        now_ready = cur >= thr
        self.player["harmony_ready"] = now_ready
        if now_ready and not was_ready:
            self.combat_events.append({"type": "harmony_ready", "message": "Armonía lista: desata tu sello."})
            self.telemetry.info("harmony_ready_cross", current=cur, threshold=thr)

    def consume_harmony(self, amount: int) -> bool:
        need = max(0, int(amount or 0))
        cur = int(self.player.get("harmony_current", 0) or 0)
        if cur < need:
            return False
        self.player["harmony_current"] = max(0, cur - need)
        thr = max(1, int(self.player.get("harmony_ready_threshold", 6) or 6))
        self.player["harmony_ready"] = int(self.player.get("harmony_current", 0)) >= thr
        return True

    def resolve_harmony_packet(self, card):
        effects = list(getattr(getattr(card, "definition", None), "effects", []) or [])
        tags = set(getattr(getattr(card, "definition", None), "tags", []) or [])
        delta = 1 if ("ritual" in tags or "armonia" in tags or "harmony" in tags) else 0
        consume = 0
        for ef in effects:
            if not isinstance(ef, dict):
                continue
            t = str(ef.get("type", "")).lower()
            if t == "harmony_delta":
                delta += int(ef.get("amount", 0) or 0)
            elif t == "consume_harmony":
                consume += max(1, int(ef.get("amount", 1) or 1))

        return {"delta": delta, "consume": consume}

    def apply_harmony_packet(self, packet: dict | None, source: str = "card"):
        packet = packet or {}
        delta = int(packet.get("delta", 0) or 0)
        consume = int(packet.get("consume", 0) or 0)
        before = int(self.player.get("harmony_current", 0) or 0)
        if delta > 0:
            self.gain_harmony(delta)
        if consume > 0:
            self.consume_harmony(consume)
        after = int(self.player.get("harmony_current", 0) or 0)
        self.telemetry.info("harmony_change", source=source, before=before, delta=delta, consume=consume, after=after)

    def activate_harmony_seal(self):
        cur = int(self.player.get("harmony_current", 0) or 0)
        thr = max(1, int(self.player.get("harmony_ready_threshold", 6) or 6))
        if cur < thr:
            return False, "Armonía no está LISTA"
        if bool(self.player.get("harmony_seal_used", False)):
            return False, "SELLO ya usado en este combate"
        self.player["harmony_seal_used"] = True
        self.player["harmony_current"] = 0
        self.player["harmony_ready"] = False
        self.player["energy"] = int(self.player.get("energy", 0) or 0) + 2
        self.combat_events.append({"type": "harmony_seal", "message": "SELLO activado: +2 Energía este turno."})
        return True, "SELLO activado"

    def end_turn(self):
        for c in self.hand:
            if getattr(c, "retain_flag", False):
                c.retain_flag = False
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
                self.combat_events.append({"type": "enemy_action", "intent": "enemy_attack", "enemy": enemy.id})
            elif intent_kind == "defend":
                value = intent.get("value", [5, 5])
                low = value[0] if isinstance(value, list) else int(value)
                high = value[1] if isinstance(value, list) and len(value) > 1 else low
                self.queue.push(GainBlock(enemy, self.rng.randint(low, high)))
                self.combat_events.append({"type": "enemy_action", "intent": "enemy_defend", "enemy": enemy.id})
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
        self.player["block"] = max(0, int(self.player.get("block", 0) or 0))
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
            if bool(self.player.get("harmony_ready", False)):
                amount += 1
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


    def pile_counts(self) -> dict:
        draw = getattr(self, "draw_pile", None)
        hand = getattr(self, "hand", None)
        discard = getattr(self, "discard_pile", None)
        return {
            "draw": len(draw) if isinstance(draw, (list, tuple)) else 0,
            "hand": len(hand) if isinstance(hand, (list, tuple)) else 0,
            "discard": len(discard) if isinstance(discard, (list, tuple)) else 0,
        }

    def get_draw_pile(self):
        return list(getattr(self, "draw_pile", []) or [])

    def get_discard_pile(self):
        return list(getattr(self, "discard_pile", []) or [])

    def pop_events(self):
        events = self.combat_events[:]
        self.combat_events.clear()
        return events
