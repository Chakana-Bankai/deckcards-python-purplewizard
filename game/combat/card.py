from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class CardDef:
    id: str
    name_key: str
    text_key: str
    rarity: str
    cost: int
    target: str
    tags: list[str]
    effects: list[dict]
    family: str = "attack"
    direction: str = "ESTE"


@dataclass
class CardInstance:
    definition: CardDef
    temp_cost: int | None = None
    upgraded: bool = False
    instance_id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def cost(self) -> int:
        return self.temp_cost if self.temp_cost is not None else self.definition.cost
