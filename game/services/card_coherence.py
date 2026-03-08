from __future__ import annotations

import re
from dataclasses import dataclass

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.components.card_framework import to_card_framework_model


VALID_ROLES = {"attack", "defense", "energy", "control", "ritual", "combo"}


REQUIRED_MODEL_FIELDS = ("id", "name", "archetype", "cost", "role", "rarity", "artwork", "effect_text", "lore_text", "kpi", "tags", "author")


@dataclass
class CardCoherenceIssue:
    card_id: str
    severity: str
    code: str
    message: str


def _effect_stats(card: dict) -> dict[str, int]:
    summary = summarize_card_effect(card, card_instance=None, ctx=None)
    stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
    out = {}
    for k, v in stats.items():
        try:
            out[str(k)] = int(v or 0)
        except Exception:
            out[str(k)] = 0
    return out


def _text_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(text or ""))]


def validate_cards_coherence(cards: list[dict]) -> dict:
    issues: list[CardCoherenceIssue] = []
    checked = 0
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        checked += 1
        model = to_card_framework_model(card, summary=summarize_card_effect(card, card_instance=None, ctx=None), app=None)
        cid = str(model.id or card.get("id") or "unknown")
        role = str(model.role or card.get("role") or "").strip().lower()
        inferred = infer_card_role(card)
        stats = _effect_stats(card)
        text_key = str(model.effect_text or card.get("text_key") or "")

        for field in REQUIRED_MODEL_FIELDS:
            value = getattr(model, field, None)
            if field == "cost" and value is None:
                issues.append(CardCoherenceIssue(cid, "warn", "model_field_missing", f"Campo requerido ausente: {field}"))
            elif field in {"kpi", "tags"} and not isinstance(value, (dict, list)):
                issues.append(CardCoherenceIssue(cid, "warn", "model_field_invalid", f"Campo invalido: {field}"))
            elif field not in {"kpi", "tags", "cost"} and (value is None or str(value).strip() == ""):
                issues.append(CardCoherenceIssue(cid, "warn", "model_field_missing", f"Campo requerido ausente: {field}"))

        if role and role not in VALID_ROLES:
            issues.append(CardCoherenceIssue(cid, "warn", "role_invalid", f"Rol no valido: {role}"))

        if role and role in VALID_ROLES and role != inferred:
            issues.append(CardCoherenceIssue(cid, "warn", "role_mismatch", f"role={role} inferred={inferred}"))

        if card.get("effects") and sum(abs(int(v or 0)) for v in stats.values()) == 0:
            issues.append(CardCoherenceIssue(cid, "warn", "empty_stats", "Efectos sin KPI numerico visible"))

        text_nums = _text_numbers(text_key)
        stat_candidates = [
            int(stats.get("damage", 0) or 0),
            int(stats.get("block", 0) or 0),
            int(stats.get("draw", 0) or 0),
            int(stats.get("scry", 0) or 0),
            abs(int(stats.get("energy_delta", 0) or 0)),
            abs(int(stats.get("harmony_delta", 0) or 0)),
            int(stats.get("rupture", 0) or 0),
            int(stats.get("consume_harmony", 0) or 0),
        ]
        stat_candidates = [x for x in stat_candidates if x > 0]
        if text_nums and stat_candidates:
            if not any(n in stat_candidates for n in text_nums):
                issues.append(CardCoherenceIssue(cid, "warn", "text_vs_kpi", f"text_nums={text_nums} kpi={stat_candidates}"))

    return {
        "checked": checked,
        "issues": [
            {
                "card_id": i.card_id,
                "severity": i.severity,
                "code": i.code,
                "message": i.message,
            }
            for i in issues
        ],
        "errors": sum(1 for i in issues if i.severity == "error"),
        "warnings": sum(1 for i in issues if i.severity == "warn"),
        "ok": not issues,
    }

