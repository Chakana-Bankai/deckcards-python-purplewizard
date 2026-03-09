from __future__ import annotations

from dataclasses import dataclass

import pygame


CARD_SIZE_NORMAL = (320, 460)
CARD_SIZE_PREVIEW = (520, 720)
CARD_SIZE_MODAL = (640, 900)
CARD_ASPECT = CARD_SIZE_NORMAL[0] / float(CARD_SIZE_NORMAL[1])


@dataclass(frozen=True)
class CardFrameworkModel:
    id: str
    name: str
    archetype: str
    cost: int
    role: str
    rarity: str
    artwork: str
    effect_text: str
    lore_text: str
    kpi: dict[str, int]
    tags: list[str]
    author: str
    order: str


def _as_dict(card) -> dict:
    if card is None:
        return {}
    if isinstance(card, dict):
        return card
    definition = getattr(card, "definition", None)
    if definition is None:
        return {}
    return {
        "id": getattr(definition, "id", "card"),
        "name_key": getattr(definition, "name_key", getattr(definition, "id", "card")),
        "text_key": getattr(definition, "text_key", ""),
        "rarity": getattr(definition, "rarity", "common"),
        "cost": getattr(card, "cost", getattr(definition, "cost", 0)),
        "tags": list(getattr(definition, "tags", []) or []),
        "effects": list(getattr(definition, "effects", []) or []),
        "role": str(getattr(definition, "role", "") or ""),
        "family": str(getattr(definition, "family", "") or ""),
        "author": str(getattr(definition, "author", "") or ""),
        "order": str(getattr(definition, "order", (getattr(definition, "metadata", {}) or {}).get("order", "")) or ""),
    }


def to_card_framework_model(card, summary: dict | None = None, app=None) -> CardFrameworkModel:
    raw = _as_dict(card)
    cid = str(raw.get("id", "card"))
    name = str(raw.get("name", raw.get("name_key", cid)))
    text_key = str(raw.get("effect_text", raw.get("text_key", "")) or "")
    lore = str(raw.get("lore_text", raw.get("lore", "")) or "")

    if app is not None:
        try:
            name = app.loc.t(name)
        except Exception:
            pass
        try:
            text_key = app.loc.t(text_key)
        except Exception:
            pass
        try:
            if lore:
                lore = app.loc.t(lore)
        except Exception:
            pass

    kpi = {}
    if isinstance(summary, dict):
        stats = summary.get("stats", {}) if isinstance(summary.get("stats", {}), dict) else {}
        for k, v in stats.items():
            try:
                kpi[str(k)] = int(v or 0)
            except Exception:
                kpi[str(k)] = 0

    if (not text_key.strip()) and isinstance(summary, dict):
        text_key = str(summary.get("header", "") or "")

    return CardFrameworkModel(
        id=cid,
        name=str(name),
        archetype=str(raw.get("archetype", raw.get("family", "core")) or "core"),
        cost=int(raw.get("cost", 0) or 0),
        role=str(raw.get("role", "") or ""),
        rarity=str(raw.get("rarity", "common") or "common"),
        artwork=str(raw.get("artwork", cid) or cid),
        effect_text=str(text_key),
        lore_text=str(lore or "Sin lore ritual."),
        kpi=kpi,
        tags=[str(t) for t in (raw.get("tags", []) or [])],
        author=str(raw.get("author", "") or "Mauricio"),
        order=str(raw.get("order", "") or "Chakana"),
    )


def fit_card_rect(container: pygame.Rect, target_size: tuple[int, int]) -> pygame.Rect:
    tw, th = max(1, int(target_size[0])), max(1, int(target_size[1]))
    scale = min(container.w / float(tw), container.h / float(th))
    fw, fh = max(90, int(tw * scale)), max(120, int(th * scale))
    out = pygame.Rect(0, 0, fw, fh)
    out.center = container.center
    return out


