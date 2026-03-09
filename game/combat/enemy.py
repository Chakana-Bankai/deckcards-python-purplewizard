from dataclasses import dataclass, field


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

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def set_intent_deck(self, intent_deck: list[dict], rng=None):
        self.intent_draw_pile = [dict(x) for x in list(intent_deck or []) if isinstance(x, dict)]
        self.intent_discard_pile = []
        self.active_intent = None
        if rng is not None and len(self.intent_draw_pile) > 1:
            rng.shuffle(self.intent_draw_pile)

    def _intent_score(self, intent: dict, rng=None) -> float:
        kind = str(intent.get("intent", "attack")).lower()
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

        if rng is not None:
            score += float(rng.random()) * 0.25
        return score

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
            score = self._intent_score(cand, rng)
            if score > best_score:
                best_score = score
                best_idx = i
        picked = dict(self.intent_draw_pile.pop(best_idx))
        return picked

    def current_intent(self, rng=None) -> dict:
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

    def advance_intent(self, rng=None):
        if self.intent_draw_pile or self.intent_discard_pile or self.active_intent is not None:
            if isinstance(self.active_intent, dict):
                self.intent_discard_pile.append(dict(self.active_intent))
            self.active_intent = None
            return
        self.intent_index = (self.intent_index + 1) % len(self.pattern)
