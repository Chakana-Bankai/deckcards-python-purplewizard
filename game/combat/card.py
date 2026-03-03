from dataclasses import dataclass, field


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


@dataclass
class CardInstance:
    definition: CardDef
    temp_cost: int | None = None
    upgraded: bool = False
    uuid: int = field(default_factory=id)

    @property
    def cost(self) -> int:
        return self.temp_cost if self.temp_cost is not None else self.definition.cost
