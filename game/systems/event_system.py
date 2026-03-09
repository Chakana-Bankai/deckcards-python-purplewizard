from __future__ import annotations

from typing import Any


EVENT_TYPE_DEFAULT = "lore"

EVENT_TYPE_BY_ID: dict[str, str] = {
    "apacheta_offer": "guide",
    "ayni_pact": "risk",
    "condor_vision": "lore",
    "puma_trial": "risk",
    "serpent_shed": "corruption",
    "chakana_crossroads": "sanctuary",
}

EVENT_TAGS_BY_TYPE: dict[str, list[str]] = {
    "guide": ["guide", "lore"],
    "risk": ["risk", "economy"],
    "lore": ["lore"],
    "corruption": ["corruption", "archon", "risk"],
    "sanctuary": ["healing", "lore"],
}

SPEAKER_BY_TYPE: dict[str, tuple[str, str, str]] = {
    "guide": ("GUIA", "angel", "guide"),
    "risk": ("ORACULO", "shaman", "oracle"),
    "lore": ("CHAKANA", "chakana_mage_portrait", "oracle"),
    "corruption": ("ARCONTE", "demon", "archon"),
    "sanctuary": ("ANGEL", "angel", "guardian"),
}


def classify_event(event_id: str | None, event_data: dict[str, Any] | None = None) -> str:
    eid = str(event_id or "").strip().lower()
    if event_data and isinstance(event_data.get("type"), str) and event_data.get("type"):
        return str(event_data.get("type")).strip().lower()
    return EVENT_TYPE_BY_ID.get(eid, EVENT_TYPE_DEFAULT)


def event_tags(event_type: str, extra: list[str] | None = None) -> list[str]:
    tags = list(EVENT_TAGS_BY_TYPE.get(str(event_type or "").lower(), ["lore"]))
    for tag in list(extra or []):
        t = str(tag or "").strip().lower()
        if t and t not in tags:
            tags.append(t)
    return tags


def speaker_profile(event_type: str) -> tuple[str, str, str]:
    et = str(event_type or "").strip().lower()
    return SPEAKER_BY_TYPE.get(et, ("CHAKANA", "chakana_mage_portrait", "oracle"))


def enrich_event_payload(event: dict[str, Any] | None, loc) -> dict[str, Any]:
    base = dict(event or {})
    etype = classify_event(base.get("id"), base)
    tags = event_tags(etype, base.get("tags") if isinstance(base.get("tags"), list) else None)
    speaker_label, portrait_key, alignment = speaker_profile(etype)

    title = str(loc.t(base.get("title_key", "event_title")) if loc else base.get("title_key", "Evento"))
    body = str(loc.t(base.get("body_key", "event_continue")) if loc else base.get("body_key", "La Trama se mueve."))

    base["event_type"] = etype
    base["tags"] = tags
    base["speaker_label"] = str(base.get("speaker_label") or speaker_label)
    base["portrait_key"] = str(base.get("portrait_key") or portrait_key)
    base["alignment"] = str(base.get("alignment") or alignment)
    base["dialogue"] = str(base.get("dialogue") or body)
    base["lore_line"] = str(base.get("lore_line") or title)
    return base


def apply_event_state_flags(run_state: dict[str, Any] | None, effect: dict[str, Any] | None) -> bool:
    if not isinstance(run_state, dict) or not isinstance(effect, dict):
        return False
    effect_type = str(effect.get("type") or "").strip().lower()
    if not effect_type:
        return False

    flags = run_state.setdefault("event_flags", {})
    if not isinstance(flags, dict):
        flags = {}
        run_state["event_flags"] = flags

    if effect_type == "set_next_combat_bonus":
        flags["next_combat_bonus"] = int(effect.get("amount", 1) or 1)
        return True
    if effect_type == "set_next_shop_discount":
        flags["next_shop_discount"] = max(0, int(effect.get("amount", 10) or 10))
        return True
    if effect_type == "set_temp_curse":
        flags["temp_curse"] = str(effect.get("curse", "shadow_mark") or "shadow_mark")
        return True
    if effect_type == "unlock_hiperborea_entry":
        flags["unlock_hiperborea_entry"] = True
        discovered = run_state.setdefault("discovered_sets", [])
        if isinstance(discovered, list):
            for name in ("hiperboria", "hiperborea"):
                if name not in discovered:
                    discovered.append(name)
        return True
    if effect_type == "guarantee_next_elite_relic":
        flags["guarantee_next_elite_relic"] = True
        return True
    if effect_type == "set_next_shop_pack_reveal":
        flags["next_shop_pack_reveal"] = str(effect.get("pack", "mystery_pack") or "mystery_pack")
        return True
    return False
