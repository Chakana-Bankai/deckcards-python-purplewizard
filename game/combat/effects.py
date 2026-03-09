from __future__ import annotations

from game.combat.actions import ApplyStatus, DealDamage, DrawCards, ExhaustCard, GainBlock, GainEnergy, ModifyStat


def check_cond(cond: dict, state, target) -> bool:
    if "stat_gte" in cond:
        stat, value = cond["stat_gte"]
        return state.player.get(stat, 0) >= value
    if cond.get("target_has_debuff"):
        return any(k in target.statuses for k in ("weak", "frail", "vulnerable", "break"))
    if "enemy_hp_lt" in cond:
        return target.hp < cond["enemy_hp_lt"]
    return False


def _effect_call_key(card_instance, target, effects) -> tuple:
    cid = str(getattr(getattr(card_instance, "definition", None), "id", "?"))
    tid = str(getattr(target, "id", "player")) if target is not None else "none"
    types = []
    for e in list(effects or [])[:8]:
        if isinstance(e, dict):
            types.append(str(e.get("type", "?")))
        else:
            types.append("?")
    return (cid, tid, tuple(types), len(list(effects or [])))


def interpret_effects(
    state,
    card_instance,
    target,
    effects: list[dict],
    _depth: int = 0,
    _chain_guard: set | None = None,
    _step_budget: list[int] | None = None,
    _call_stack: list[tuple] | None = None,
):
    # Hard recursion protection against effect-loop chains.
    if _depth > 16:
        return
    if _chain_guard is None:
        _chain_guard = set()
    if _step_budget is None:
        # Global action budget per resolution tree.
        _step_budget = [180]
    if _step_budget[0] <= 0:
        return
    if _call_stack is None:
        _call_stack = []

    if not isinstance(effects, list) or not effects:
        return

    call_key = _effect_call_key(card_instance, target, effects)
    if call_key in _call_stack:
        return

    _call_stack.append(call_key)
    try:
        for effect in effects:
            _step_budget[0] -= 1
            if _step_budget[0] <= 0:
                return
            if not isinstance(effect, dict):
                continue
            t = effect.get("type")
            if t == "damage":
                state.queue.push(DealDamage("player", target, int(effect.get("amount", 0))))
            elif t in {"block", "gain_block"}:
                state.queue.push(GainBlock("player", int(effect.get("amount", 0))))
            elif t == "draw":
                state.queue.push(DrawCards(int(effect.get("amount", 0))))
            elif t in {"energy", "gain_mana"}:
                state.queue.push(GainEnergy(int(effect.get("amount", 0))))
            elif t == "gain_mana_next_turn":
                state.next_turn_bonus_energy += int(effect.get("amount", 0))
            elif t == "status":
                who = target if card_instance.definition.target == "enemy" else "player"
                state.queue.push(ApplyStatus(who, effect["name"], effect["stacks"]))
            elif t == "rupture":
                state.queue.push(ModifyStat("player", "rupture", int(effect.get("amount", 0))))
            elif t == "if":
                if check_cond(effect.get("cond", {}), state, target):
                    interpret_effects(
                        state,
                        card_instance,
                        target,
                        list(effect.get("then", []) or []),
                        _depth + 1,
                        _chain_guard,
                        _step_budget,
                        _call_stack,
                    )
            elif t == "exhaust_self":
                state.queue.push(ExhaustCard(card_instance))
            elif t == "heal":
                state.heal_player(int(effect.get("amount", 0)))
            elif t == "scry":
                state.begin_scry(int(effect.get("amount", 3)))
            elif t == "apply_break":
                if target and hasattr(target, "statuses"):
                    target.statuses["break"] = target.statuses.get("break", 0) + int(effect.get("amount", 0))
            elif t == "weaken_enemy":
                state.player["statuses"]["enemy_damage_down"] = state.player["statuses"].get("enemy_damage_down", 0) + int(effect.get("amount", 0))
            elif t == "vulnerable_enemy":
                if target and hasattr(target, "statuses"):
                    target.statuses["vulnerable"] = target.statuses.get("vulnerable", 0) + int(effect.get("amount", 0))
            elif t == "copy_last_played":
                last = state.last_played_card
                if last and (effect.get("baston_once") is None or not state.baston_used):
                    if effect.get("baston_once"):
                        state.baston_used = True
                    if last is card_instance:
                        continue
                    last_effects = list(getattr(getattr(last, "definition", None), "effects", []) or [])
                    if not last_effects:
                        continue
                    edge = (id(card_instance), id(last))
                    if edge in _chain_guard:
                        continue
                    _chain_guard.add(edge)
                    interpret_effects(state, card_instance, target, last_effects, _depth + 1, _chain_guard, _step_budget, _call_stack)
            elif t == "copy_next_played":
                state.player["statuses"]["copy_next"] = 1
            elif t == "retain":
                card_instance.retain_flag = bool(effect.get("amount", 1))
            elif t == "self_break":
                state.player["rupture"] += int(effect.get("amount", 0))
            elif t == "self_damage":
                state.player["hp"] = max(1, state.player["hp"] - int(effect.get("amount", 0)))
            elif t == "draw_if_enemy_break":
                if target and getattr(target, "statuses", {}).get("break", 0) > 0:
                    state.draw(int(effect.get("amount", 1)))
            elif t == "damage_if_enemy_break":
                if target and getattr(target, "statuses", {}).get("break", 0) > 0:
                    state.queue.push(DealDamage("player", target, int(effect.get("amount", 0))))
            elif t == "draw_on_kill":
                state.pending_if_kill = [{"type": "draw", "amount": int(effect.get("amount", 1))}]
            elif t == "draw_if_direction_played":
                if effect.get("direction") in state.harmony_last3:
                    state.draw(int(effect.get("amount", 1)))
            elif t == "draw_if_no_block":
                if state.player.get("block", 0) == 0:
                    state.draw(int(effect.get("amount", 1)))
            elif t == "gain_block_if_no_direction":
                if effect.get("direction") not in state.harmony_last3:
                    state.player["block"] += int(effect.get("amount", 0))
            elif t == "gain_mana_if_enemy_attack_intent":
                en = next((e for e in state.enemies if e.alive), None)
                if en and en.current_intent().get("intent") == "attack":
                    state.player["energy"] += int(effect.get("amount", 0))
            elif t == "double_block_cap":
                extra = min(state.player.get("block", 0), int(effect.get("amount", 12)))
                state.player["block"] += extra
            elif t == "discount_next_attack":
                state.player["statuses"]["discount_next_attack"] = int(effect.get("amount", 1))
            elif t == "reduce_hand_card_cost":
                if state.hand:
                    state.hand[0].temp_cost = max(0, state.hand[0].cost - int(effect.get("amount", 1)))
            elif t == "ritual_trama":
                if len(set(state.harmony_last3[-3:])) == 3 and len(state.harmony_last3) >= 3:
                    state.queue.push(DealDamage("player", target, 12))
                    state.heal_player(4)
                else:
                    state.queue.push(DealDamage("player", target, 8))
            elif t == "if_kill":
                state.pending_if_kill = effect.get("then", [])
            elif t == "damage_plus_rupture":
                amount = effect["base"] + state.player["rupture"] * effect["per_rupture"]
                state.queue.push(DealDamage("player", target, amount))
            elif t == "set_rupture":
                state.player["rupture"] = effect["amount"]
    finally:
        # Keep stack balanced even if any effect raises unexpectedly.
        if _call_stack:
            _call_stack.pop()
