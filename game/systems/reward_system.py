from __future__ import annotations

from game.combat.card import CardDef, CardInstance


def _card_instance(card_dict):
    return CardInstance(CardDef(**card_dict))


def _safe_pick(rng, pool, fallback):
    source = list(pool or [])
    if source:
        return rng.choice(source)
    fb = list(fallback or [])
    return rng.choice(fb) if fb else None


def _pick_unique(rng, pool, count, fallback=None):
    src = list(pool or [])
    out = []
    while src and len(out) < count:
        card = rng.choice(src)
        src.remove(card)
        out.append(card)
    while len(out) < count:
        extra = _safe_pick(rng, pool, fallback)
        if extra is None:
            break
        out.append(extra)
    return out


def _pack_profile_for_state(rng, player_state) -> dict:
    level = int((player_state or {}).get("level", 1) or 1)
    roll = rng.random()
    if level <= 1:
        if roll < 0.68:
            return {"id": "normal_pack", "title": "Pack Normal", "lore": "Fragmentos estables para consolidar la ruta."}
        return {"id": "ritual_reward_pack", "title": "Pack Ritual", "lore": "Ecos rituales para acelerar la armonia."}
    if roll < 0.44:
        return {"id": "normal_pack", "title": "Pack Normal", "lore": "Refuerza tu base sin perder ritmo."}
    if roll < 0.72:
        return {"id": "rare_choice_pack", "title": "Eleccion Rara", "lore": "Tres bifurcaciones de alto impacto."}
    if roll < 0.9:
        return {"id": "ritual_reward_pack", "title": "Pack Ritual", "lore": "Mecanicas de rito y lectura de flujo."}
    return {"id": "legendary_reward", "title": "Recompensa Legendaria", "lore": "La Trama abre una opcion excepcional."}


def build_reward_normal(rng, card_pool, player_state) -> dict:
    pool = list(card_pool or [])
    if not pool:
        return {"type": "choose1of3", "cards": [], "pack_category": "normal_pack", "pack_title": "Pack Normal", "pack_lore": "Sin cartas disponibles."}

    common_pool = [c for c in pool if c.get("rarity") in {"basic", "common"}] or pool
    uncommon_pool = [c for c in pool if c.get("rarity") == "uncommon"] or common_pool
    rare_pool = [c for c in pool if c.get("rarity") == "rare"] or uncommon_pool
    legendary_pool = [c for c in pool if c.get("rarity") == "legendary"] or rare_pool
    ritual_pool = [
        c
        for c in pool
        if any(tag in {"ritual", "harmony", "scry", "draw", "control"} for tag in (c.get("tags") or []))
    ] or uncommon_pool

    profile = _pack_profile_for_state(rng, player_state)
    pack_id = profile["id"]

    if pack_id == "rare_choice_pack":
        picks = _pick_unique(rng, rare_pool + uncommon_pool, 3, fallback=pool)
    elif pack_id == "legendary_reward":
        picks = [
            _safe_pick(rng, legendary_pool, rare_pool),
            _safe_pick(rng, rare_pool, uncommon_pool),
            _safe_pick(rng, uncommon_pool, common_pool),
        ]
        picks = [p for p in picks if p is not None]
    elif pack_id == "ritual_reward_pack":
        picks = _pick_unique(rng, ritual_pool, 3, fallback=pool)
    else:
        picks = _pick_unique(rng, common_pool + uncommon_pool, 3, fallback=pool)

    return {
        "type": "choose1of3",
        "cards": [_card_instance(c) for c in picks if c],
        "pack_category": pack_id,
        "pack_title": profile["title"],
        "pack_lore": profile["lore"],
    }


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
    return {
        "type": "boss_pack",
        "cards": cards,
        "relic": relic,
        "pack_category": "legendary_reward",
        "pack_title": "Trofeo del Umbral",
        "pack_lore": "Botin mayor: poder, memoria y reliquia.",
    }


def build_reward_guide(event_id, rng, card_pool, player_state) -> dict:
    _ = event_id
    pool = list(card_pool or [])
    atk_pool = [c for c in pool if "attack" in (c.get("tags") or [])] or pool
    ritual_pool = [c for c in pool if "ritual" in (c.get("tags") or [])] or pool
    rare_pool = [c for c in pool if c.get("rarity") in {"rare", "uncommon", "legendary"}] or pool

    strike_a = (rng.choice(atk_pool).get("id", "strike") if atk_pool else "strike")
    strike_b = (rng.choice(atk_pool).get("id", "strike") if atk_pool else "strike")
    ritual_a = (rng.choice(ritual_pool).get("id", "defend") if ritual_pool else "defend")
    bonus_c = (rng.choice(rare_pool).get("id", "defend") if rare_pool else "defend")

    templates = [
        {
            "title": "Senda Solar",
            "identity": "Equilibrio brillante",
            "lore": "El guia abre un patron de armonia sostenida.",
            "effect_label": "+1 armonia max / umbral -1",
            "effects": [
                {"type": "gain_harmony_perm", "amount": 1},
                {"type": "tune_ritual_threshold", "delta": -1},
            ],
        },
        {
            "title": "Senda del Jaguar",
            "identity": "Presion ofensiva",
            "lore": "La ruta pide agresion y cierre temprano.",
            "effect_label": "+2 cartas ataque / +20 oro",
            "effects": [
                {"type": "gain_cards", "cards": [strike_a, strike_b]},
                {"type": "gain_gold", "amount": 20},
            ],
        },
        {
            "title": "Senda de Ceniza",
            "identity": "Recuperacion tactica",
            "lore": "El costo del combate se transmuta en fortaleza.",
            "effect_label": "cura 30% / +8 max HP",
            "effects": [
                {"type": "heal_percent", "amount": 0.30},
                {"type": "gain_max_hp", "amount": 8},
            ],
        },
        {
            "title": "Senda del Umbral",
            "identity": "Ritual y control",
            "lore": "Los ecos obedecen a una geometria precisa.",
            "effect_label": "+2 cartas ritual / +1 armonia",
            "effects": [
                {"type": "gain_cards", "cards": [ritual_a, bonus_c]},
                {"type": "gain_harmony_perm", "amount": 1},
            ],
        },
        {
            "title": "Senda de Prosperidad",
            "identity": "Economia de run",
            "lore": "El guia bendice el trayecto con abundancia.",
            "effect_label": "+45 oro / cura 20%",
            "effects": [
                {"type": "gain_gold", "amount": 45},
                {"type": "heal_percent", "amount": 0.20},
            ],
        },
    ]

    picks = _pick_unique(rng, templates, 3, fallback=templates)
    options = [
        {
            "title": opt.get("title", "Senda"),
            "lore": opt.get("lore", ""),
            "identity": opt.get("identity", ""),
            "effect_label": opt.get("effect_label", ""),
            "effects": list(opt.get("effects", [])),
        }
        for opt in picks
    ]
    return {"type": "guide_choice", "options": options}
