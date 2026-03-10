from dataclasses import dataclass, field

from game.systems.enemy_deck_system import lore_enemy_card_name


def _intent_phrase(intent: dict) -> str:
    kind = intent.get("intent", "attack")
    if kind == "attack":
        value = intent.get("value", [0, 0])
        amount = value[1] if isinstance(value, list) and len(value) > 1 else (value[0] if isinstance(value, list) and value else int(value or 0))
        return f"Canaliza Ruptura ({int(amount)})"
    if kind == "defend":
        value = intent.get("value", [0, 0])
        amount = value[1] if isinstance(value, list) and len(value) > 1 else (value[0] if isinstance(value, list) and value else int(value or 0))
        return f"Refuerza Guardian ({int(amount)})"
    if kind == "debuff":
        return f"Maldice {intent.get('status', 'sombra').title()} ({int(intent.get('stacks', 1))})"
    if kind == "buff":
        return f"Invoca Velo {intent.get('status', 'astral').title()} ({int(intent.get('stacks', 1))})"
    return "Teje Presagio"


@dataclass
class Enemy:
    id: str
    name_key: str
    hp: int
    max_hp: int
    pattern: list[dict]
    statuses: dict[str, int] = field(default_factory=dict)
    block: int = 0
    intent_index: int = 0
    last_action_name: str = "-"
    intent_draw_pile: list[dict] = field(default_factory=list)
    intent_discard_pile: list[dict] = field(default_factory=list)
    active_intent: dict | None = None
    ai_profile: str = "balanced"
    enemy_type: str = "criatura"

    # Phase: enemy deck system
    combat_draw_pile: list[dict] = field(default_factory=list)
    combat_discard_pile: list[dict] = field(default_factory=list)
    combat_hand: list[dict] = field(default_factory=list)
    current_enemy_card: dict | None = None
    next_enemy_card: dict | None = None

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def _normalize_enemy_card(self, card: dict) -> dict:
        c = dict(card or {})
        c.setdefault("intent", "attack")
        c.setdefault("id", str(c.get("name", "enemy_card")).lower().replace(" ", "_"))
        c["name"] = lore_enemy_card_name(str(c.get("name", c.get("id", "enemy_card"))))
        if c.get("intent") in {"attack", "defend"} and not isinstance(c.get("value"), list):
            v = int(c.get("value", 6) or 6)
            c["value"] = [v, v]
        c.setdefault("label", _intent_phrase(c))
        return c

    def set_combat_deck(self, deck_cards: list[dict], rng=None):
        self.combat_draw_pile = [self._normalize_enemy_card(x) for x in list(deck_cards or []) if isinstance(x, dict)]
        self.combat_discard_pile = []
        self.combat_hand = []
        self.current_enemy_card = None
        self.next_enemy_card = None
        if rng is not None and len(self.combat_draw_pile) > 1:
            rng.shuffle(self.combat_draw_pile)

    def _reshuffle_combat(self, rng=None):
        if self.combat_draw_pile or not self.combat_discard_pile:
            return
        self.combat_draw_pile = list(self.combat_discard_pile)
        self.combat_discard_pile = []
        if rng is not None and len(self.combat_draw_pile) > 1:
            rng.shuffle(self.combat_draw_pile)

    def _draw_combat_cards(self, n: int, rng=None):
        need = max(0, int(n or 0))
        for _ in range(need):
            if not self.combat_draw_pile:
                self._reshuffle_combat(rng)
            if not self.combat_draw_pile:
                break
            self.combat_hand.append(self.combat_draw_pile.pop())

    def _card_score(self, card: dict, rng=None) -> float:
        kind = str(card.get("intent", "attack")).lower()
        score = {
            "attack": 2.0,
            "break": 1.9,
            "defend": 1.5,
            "debuff": 1.4,
            "buff": 1.2,
            "channel": 1.0,
            "heal": 1.2,
        }.get(kind, 1.0)

        hp_ratio = (float(self.hp) / float(max(1, self.max_hp))) if int(self.max_hp or 0) > 0 else 1.0
        if hp_ratio <= 0.40:
            if kind in {"defend", "buff", "heal"}:
                score += 1.7
            if kind in {"attack", "break"}:
                score -= 0.3

        if int(self.block or 0) >= 8 and kind == "defend":
            score -= 0.6
        if int(self.block or 0) >= 8 and kind in {"attack", "break"}:
            score += 0.2

        profile = str(self.ai_profile or "balanced").lower()
        if profile == "aggro":
            if kind in {"attack", "break"}:
                score += 0.8
            if kind == "defend":
                score -= 0.4
        elif profile == "control":
            if kind in {"debuff", "buff", "channel"}:
                score += 0.7
        elif profile == "bulwark":
            if kind == "defend":
                score += 0.8
            if kind in {"attack", "break"}:
                score -= 0.2

        # Boss pacing: keep threat, but reduce streaky double-attack pressure
        # and favor mixed turns so the fight feels tactical instead of spiky.
        if str(self.enemy_type or "").lower() == "arconte":
            if kind in {"attack", "break"}:
                score -= 0.22
            if kind in {"defend", "buff", "debuff", "channel"}:
                score += 0.18
            if int(self.block or 0) <= 4 and kind == "defend":
                score += 0.24
            if hp_ratio <= 0.45 and kind == "heal":
                score += 0.28

        if rng is not None:
            score += float(rng.random()) * 0.25
        return score

    def draw_playable_cards(self, rng=None, draw_n: int = 5) -> list[dict]:
        if not self.combat_draw_pile and not self.combat_discard_pile and not self.combat_hand:
            return []
        self._draw_combat_cards(draw_n, rng)
        if not self.combat_hand:
            self.current_enemy_card = None
            self.next_enemy_card = None
            return []

        hand = list(self.combat_hand)
        hand.sort(key=lambda c: self._card_score(c, rng), reverse=True)
        max_play = 2 if str(self.enemy_type or "").lower() in {"guardian", "arconte"} else 1
        picks = hand[:max_play]

        if str(self.enemy_type or "").lower() == "arconte" and len(picks) > 1:
            first_kind = str(picks[0].get("intent", "")).lower()
            second_kind = str(picks[1].get("intent", "")).lower()
            if first_kind in {"attack", "break"} and second_kind in {"attack", "break"}:
                alt = next(
                    (c for c in hand[2:] if str(c.get("intent", "")).lower() not in {"attack", "break"}),
                    None,
                )
                if alt is not None:
                    picks[1] = alt

        picked_ids = {id(x) for x in picks}
        self.combat_hand = [c for c in self.combat_hand if id(c) not in picked_ids]

        self.current_enemy_card = dict(picks[0]) if picks else None
        self.next_enemy_card = dict(picks[1]) if len(picks) > 1 else (dict(self.combat_hand[0]) if self.combat_hand else None)
        return [dict(x) for x in picks]

    def end_enemy_turn_cards(self, played_cards: list[dict] | None = None, rng=None):
        for c in list(played_cards or []):
            self.combat_discard_pile.append(self._normalize_enemy_card(c))
        for c in list(self.combat_hand or []):
            self.combat_discard_pile.append(self._normalize_enemy_card(c))
        self.combat_hand = []
        self._reshuffle_combat(rng)

    def set_intent_deck(self, intent_deck: list[dict], rng=None):
        self.intent_draw_pile = [dict(x) for x in list(intent_deck or []) if isinstance(x, dict)]
        self.intent_discard_pile = []
        self.active_intent = None
        if rng is not None and len(self.intent_draw_pile) > 1:
            rng.shuffle(self.intent_draw_pile)

    def _draw_intent_from_deck(self, rng=None) -> dict | None:
        if not self.intent_draw_pile and self.intent_discard_pile:
            self.intent_draw_pile = self.intent_discard_pile
            self.intent_discard_pile = []
            if rng is not None and len(self.intent_draw_pile) > 1:
                rng.shuffle(self.intent_draw_pile)
        if not self.intent_draw_pile:
            return None

        lookahead = min(3, len(self.intent_draw_pile))
        start = len(self.intent_draw_pile) - lookahead
        best_idx = start
        best_score = -9999.0
        for i in range(start, len(self.intent_draw_pile)):
            cand = self.intent_draw_pile[i]
            score = self._card_score(cand, rng)
            if score > best_score:
                best_score = score
                best_idx = i
        picked = dict(self.intent_draw_pile.pop(best_idx))
        return picked

    def current_intent(self, rng=None) -> dict:
        # Enemy deck system takes precedence for HUD visibility.
        if isinstance(self.current_enemy_card, dict):
            it = dict(self.current_enemy_card)
            it.setdefault("label", _intent_phrase(it))
            return it

        if self.intent_draw_pile or self.intent_discard_pile or self.active_intent is not None:
            if self.active_intent is None:
                self.active_intent = self._draw_intent_from_deck(rng)
            if isinstance(self.active_intent, dict):
                it = dict(self.active_intent)
                it.setdefault("label", _intent_phrase(it))
                return it

        it = dict(self.pattern[self.intent_index % len(self.pattern)])
        it.setdefault("label", _intent_phrase(it))
        return it

    def next_intent_preview(self, rng=None) -> dict:
        if isinstance(self.next_enemy_card, dict):
            it = dict(self.next_enemy_card)
            it.setdefault("label", _intent_phrase(it))
            return it
        if self.intent_draw_pile:
            it = dict(self.intent_draw_pile[-1])
            it.setdefault("label", _intent_phrase(it))
            return it
        return self.current_intent(rng)

    def advance_intent(self, rng=None):
        if self.intent_draw_pile or self.intent_discard_pile or self.active_intent is not None:
            if isinstance(self.active_intent, dict):
                self.intent_discard_pile.append(dict(self.active_intent))
            self.active_intent = None
            return
        self.intent_index = (self.intent_index + 1) % len(self.pattern)
