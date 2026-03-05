from __future__ import annotations

from game.combat.card import CardDef, CardInstance


def _card_instance(card_dict):
    return CardInstance(CardDef(**card_dict))


def build_reward_normal(rng, card_pool, player_state) -> dict:
    _ = player_state
    pool = list(card_pool or [])
    picks = [_card_instance(rng.choice(pool)) for _ in range(3)] if pool else []
    return {"type": "choose1of3", "cards": picks}


def build_reward_boss(rng, card_pool, relic_pool, player_state) -> dict:
    _ = player_state
    cards = []
    pool = list(card_pool or [])
    if pool:
        for _ in range(5):
            cards.append(_card_instance(rng.choice(pool)))
    relic = None
    rpool = list(relic_pool or [])
    if rpool:
        relic = rng.choice(rpool)
    return {"type": "boss_pack", "cards": cards, "relic": relic}


def build_reward_guide(event_id, rng, card_pool, player_state) -> dict:
    _ = (event_id, rng, player_state)
    pool = list(card_pool or [])
    atk_pool = [c for c in pool if "attack" in (c.get("tags") or [])] or pool
    options = [
        {
            "title": "Sabiduría",
            "lore": "El guía revela patrones de la Trama.",
            "effect_label": "+1 Armonía permanente",
            "effects": [{"type": "gain_harmony_perm", "amount": 1}],
        },
        {
            "title": "Poder",
            "lore": "Canalizas fuerza ancestral para el próximo tramo.",
            "effect_label": "Añade 2 cartas de Ataque",
            "effects": [{"type": "gain_cards", "cards": [rng.choice(atk_pool).get("id", "strike") if atk_pool else "strike", rng.choice(atk_pool).get("id", "strike") if atk_pool else "strike"]}],
        },
        {
            "title": "Sacrificio",
            "lore": "Entregas parte del dolor para seguir avanzando.",
            "effect_label": "Cura 25% y pierde 1 carta aleatoria",
            "effects": [{"type": "heal_percent", "amount": 0.25}, {"type": "lose_random_deck_card", "amount": 1}],
        },
    ]
    return {"type": "guide_choice", "options": options}
