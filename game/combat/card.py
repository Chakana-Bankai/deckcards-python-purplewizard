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
    role: str = "combo"
    family: str = "attack"
    direction: str = "ESTE"
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict | None):
        """Build CardDef safely from content payloads with extra metadata fields.

        Unknown fields are preserved in ``metadata`` instead of raising TypeError.
        """
        raw = dict(data or {})
        cid = str(raw.get("id") or "card_unknown")
        name = raw.get("name_key") or raw.get("name_es") or cid
        text = raw.get("text_key") or raw.get("text_es") or ""

        payload = {
            "id": cid,
            "name_key": str(name),
            "text_key": str(text),
            "rarity": str(raw.get("rarity", "common") or "common"),
            "cost": int(raw.get("cost", 0) or 0),
            "target": str(raw.get("target", "enemy") or "enemy"),
            "tags": list(raw.get("tags", []) or []),
            "effects": list(raw.get("effects", []) or []),
            "role": str(raw.get("role", "combo") or "combo"),
            "family": str(raw.get("family", raw.get("direction", "attack")) or "attack"),
            "direction": str(raw.get("direction", "ESTE") or "ESTE"),
        }

        known = {
            "id",
            "name_key",
            "name_es",
            "text_key",
            "text_es",
            "rarity",
            "cost",
            "target",
            "tags",
            "effects",
            "role",
            "family",
            "direction",
            "metadata",
        }
        extra = dict(raw.get("metadata") or {})
        for k, v in raw.items():
            if k not in known:
                extra[k] = v

        return cls(**payload, metadata=extra)


@dataclass
class CardInstance:
    definition: CardDef
    temp_cost: int | None = None
    upgraded: bool = False
    instance_id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def cost(self) -> int:
        return self.temp_cost if self.temp_cost is not None else self.definition.cost
