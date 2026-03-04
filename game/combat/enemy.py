from dataclasses import dataclass, field


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
        return self.pattern[self.intent_index % len(self.pattern)]

    def advance_intent(self):
        self.intent_index = (self.intent_index + 1) % len(self.pattern)
