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

    @property
    def alive(self) -> bool:
        return self.hp > 0

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
        return dict(self.intent_draw_pile.pop())

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
