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
        return f"Refuerza Guardián ({int(amount)})"
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

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def current_intent(self) -> dict:
        it = dict(self.pattern[self.intent_index % len(self.pattern)])
        it.setdefault("label", _intent_phrase(it))
        return it

    def advance_intent(self):
        self.intent_index = (self.intent_index + 1) % len(self.pattern)
