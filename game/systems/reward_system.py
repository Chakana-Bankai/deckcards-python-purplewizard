from __future__ import annotations

from game.combat.card import CardDef, CardInstance

PACK_ECONOMY = {
    "base_pack": {
        "title": "Sobre del Origen",
        "lore": "Fundamentos estables para escalar la run.",
        "expected_value": {
            "cards_total": 5,
            "rarity_focus": "base_consistency",
            "gold_hint": [20, 35],
            "strategy": "consistencia",
        },
    },
    "hiperborea_pack": {
        "title": "Sobre de Hiperborea",
        "lore": "Tecnicas polares y lectura ancestral.",
        "expected_value": {
            "cards_total": 5,
            "rarity_focus": "hiperborea_identity",
            "gold_hint": [28, 46],
            "strategy": "expansion_synergy",
        },
    },
    "mystery_pack": {
        "title": "Sobre del Velo",
        "lore": "Apuesta tactica con mezcla incierta.",
        "expected_value": {
            "cards_total": 5,
            "rarity_focus": "mixed_surprise",
            "gold_hint": [30, 50],
            "strategy": "high_variance",
        },
    },
    "normal_pack": {
        "title": "Pack Normal",
        "lore": "Base estable para sostener la run.",
        "expected_value": {
            "cards_total": 3,
            "rarity_focus": "common_uncommon",
            "gold_hint": [20, 35],
            "strategy": "consistencia",
        },
    },
    "rare_choice_pack": {
        "title": "Eleccion Rara",
        "lore": "Tres bifurcaciones de alto impacto tactico.",
        "expected_value": {
            "cards_total": 3,
            "rarity_focus": "rare_uncommon",
            "gold_hint": [28, 42],
            "strategy": "power_spike",
        },
    },
    "ritual_reward_pack": {
        "title": "Pack Ritual",
        "lore": "Mecanicas de rito y lectura de flujo.",
        "expected_value": {
            "cards_total": 3,
            "rarity_focus": "ritual_control",
            "gold_hint": [24, 38],
            "strategy": "harmony_scaling",
        },
    },
    "legendary_reward": {
        "title": "Recompensa Legendaria",
        "lore": "La Trama abre una opcion excepcional.",
        "expected_value": {
            "cards_total": 3,
            "rarity_focus": "legendary_rare_mix",
            "gold_hint": [35, 55],
            "strategy": "run_defining",
        },
    },
}


LEGACY_PACK_ALIAS = {
    "normal_pack": "base_pack",
    "rare_choice_pack": "mystery_pack",
    "ritual_reward_pack": "mystery_pack",
}


def normalize_pack_id(pack_id: str) -> str:
    key = str(pack_id or "").strip().lower()
    return LEGACY_PACK_ALIAS.get(key, key)
def _card_instance(card_dict):
    c = dict(card_dict or {})
    payload = {
        "id": c.get("id"),
        "name_key": c.get("name_key", c.get("id", "card")),
        "text_key": c.get("text_key", ""),
        "rarity": c.get("rarity", "common"),
        "cost": int(c.get("cost", 0) or 0),
        "target": c.get("target", "enemy"),
        "tags": list(c.get("tags", []) or []),
        "effects": list(c.get("effects", []) or []),
        "role": c.get("role", "combo"),
        "family": c.get("family", "attack"),
        "direction": c.get("direction", "ESTE"),
    }
    return CardInstance(CardDef.from_dict(payload))


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


def _weighted_pack_roll(rng, table: list[tuple[str, float]]) -> str:
    roll = rng.random()
    acc = 0.0
    for pack_id, weight in table:
        acc += float(weight)
        if roll <= acc:
            return pack_id
    return table[-1][0]


def _pack_profile_for_state(rng, player_state) -> dict:
    level = int((player_state or {}).get("level", 1) or 1)
    if level <= 1:
        table = [
            ("base_pack", 0.60),
            ("mystery_pack", 0.28),
            ("hiperborea_pack", 0.12),
        ]
    elif level <= 4:
        table = [
            ("base_pack", 0.36),
            ("mystery_pack", 0.36),
            ("hiperborea_pack", 0.20),
            ("legendary_reward", 0.08),
        ]
    else:
        table = [
            ("base_pack", 0.24),
            ("mystery_pack", 0.34),
            ("hiperborea_pack", 0.24),
            ("legendary_reward", 0.18),
        ]
    pack_id = normalize_pack_id(_weighted_pack_roll(rng, table))
    meta = PACK_ECONOMY.get(pack_id, PACK_ECONOMY["base_pack"])
    return {"id": pack_id, "title": meta["title"], "lore": meta["lore"], "expected_value": dict(meta["expected_value"])}


def build_reward_normal(rng, card_pool, player_state) -> dict:
    pool = list(card_pool or [])
    if not pool:
        return {
            "type": "choose1of3",
            "cards": [],
            "pack_category": "base_pack",
            "pack_title": PACK_ECONOMY["base_pack"]["title"],
            "pack_lore": "Sin cartas disponibles.",
            "pack_expected_value": dict(PACK_ECONOMY["base_pack"]["expected_value"]),
            "reward_categories": ["single_card_reward", "gold_reward"],
        }

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
    pack_id = normalize_pack_id(profile["id"])

    if pack_id == "mystery_pack":
        picks = _pick_unique(rng, rare_pool + uncommon_pool, 3, fallback=pool)
    elif pack_id == "legendary_reward":
        picks = [
            _safe_pick(rng, legendary_pool, rare_pool),
            _safe_pick(rng, rare_pool, uncommon_pool),
            _safe_pick(rng, uncommon_pool, common_pool),
        ]
        picks = [p for p in picks if p is not None]
    elif pack_id == "hiperborea_pack":
        picks = _pick_unique(rng, rare_pool + ritual_pool, 3, fallback=pool)
    else:
        picks = _pick_unique(rng, common_pool + uncommon_pool, 3, fallback=pool)

    return {
        "type": "choose1of3",
        "cards": [_card_instance(c) for c in picks if c],
        "pack_category": pack_id,
        "pack_title": profile["title"],
        "pack_lore": profile["lore"],
        "pack_expected_value": dict(profile.get("expected_value", {})),
        "reward_categories": ["single_card_reward", "gold_reward"],
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
        "pack_expected_value": {
            "cards_total": 5,
            "rarity_focus": "boss_mixed_high_tier",
            "gold_hint": [120, 180],
            "strategy": "build_capstone",
        },
        "reward_categories": ["full_pack_reward", "relic_reward", "gold_reward"],
    }


def build_reward_guide(event_id, rng, card_pool, player_state) -> dict:
    _ = event_id
    _ = player_state
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
            "effect_label": "+2 cartas ataque / +24 oro",
            "effects": [
                {"type": "gain_cards", "cards": [strike_a, strike_b]},
                {"type": "gain_gold", "amount": 24},
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
            "effect_label": "+2 cartas ritual/control / +1 armonia",
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
        {
            "title": "Senda del Condor",
            "identity": "Vision estrategica",
            "lore": "La altura revela rutas mas limpias de recursos.",
            "effect_label": "+1 carta rara / +18 XP",
            "effects": [
                {"type": "gain_cards", "cards": [bonus_c]},
                {"type": "gain_xp", "amount": 18},
            ],
        },
        {
            "title": "Senda de la Reliquia",
            "identity": "Bendicion mayor",
            "lore": "El guia entrega un sello material de poder.",
            "effect_label": "Reliquia rara aleatoria / -1 carta mazo",
            "effects": [
                {"type": "gain_relic_random", "rarity": "rare"},
                {"type": "lose_random_deck_card"},
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
    return {
        "type": "guide_choice",
        "options": options,
        "reward_categories": ["guide_blessing", "single_card_reward", "healing_reward", "gold_reward", "relic_reward"],
    }



