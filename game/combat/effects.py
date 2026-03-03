from __future__ import annotations

from game.combat.actions import (
    ApplyStatus,
    DealDamage,
    DrawCards,
    ExhaustCard,
    GainBlock,
    GainEnergy,
    ModifyStat,
)


def check_cond(cond: dict, state, target) -> bool:
    if "stat_gte" in cond:
        stat, value = cond["stat_gte"]
        return state.player.get(stat, 0) >= value
    if cond.get("target_has_debuff"):
        return any(k in target.statuses for k in ("weak", "frail"))
    if "enemy_hp_lt" in cond:
        return target.hp < cond["enemy_hp_lt"]
    return False


def interpret_effects(state, card_instance, target, effects: list[dict]):
    for effect in effects:
        t = effect["type"]
        if t == "damage":
            state.queue.push(DealDamage("player", target, effect["amount"]))
        elif t == "block":
            state.queue.push(GainBlock("player", effect["amount"]))
        elif t == "draw":
            state.queue.push(DrawCards(effect["amount"]))
        elif t == "energy":
            state.queue.push(GainEnergy(effect["amount"]))
        elif t == "status":
            who = target if card_instance.definition.target == "enemy" else "player"
            state.queue.push(ApplyStatus(who, effect["name"], effect["stacks"]))
        elif t == "rupture":
            state.queue.push(ModifyStat("player", "rupture", effect["amount"]))
        elif t == "if":
            if check_cond(effect["cond"], state, target):
                interpret_effects(state, card_instance, target, effect["then"])
        elif t == "exhaust_self":
            state.queue.push(ExhaustCard(card_instance))
        elif t == "choose":
            # MVP: auto-elige opción 1.
            interpret_effects(state, card_instance, target, effect["options"][0])
        elif t == "heal":
            state.heal_player(effect["amount"])
        elif t == "scry":
            state.begin_scry(effect.get("amount", 3))
        elif t == "convert_block_to_damage":
            amount = min(state.player["block"], effect["amount"])
            state.player["block"] -= amount
            state.queue.push(DealDamage("player", target, amount))
        elif t == "if_kill":
            state.pending_if_kill = effect["then"]
        elif t == "damage_plus_rupture":
            amount = effect["base"] + state.player["rupture"] * effect["per_rupture"]
            state.queue.push(DealDamage("player", target, amount))
        elif t == "set_rupture":
            state.player["rupture"] = effect["amount"]
        elif t in {"exhaust_from_hand", "cleanse_or_dispel", "zero_and_double_play"}:
            pass
        else:
            print(f"[effects] warning: unsupported effect type '{t}'")
