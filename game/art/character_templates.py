from __future__ import annotations

CHARACTER_TEMPLATES = {
    "archon_base": {
        "template_id": "archon_base",
        "archetype": "archon",
        "width_ratio": 0.68,
        "height_ratio": 0.72,
        "head_scale": (0.08, 0.13),
        "shoulder_width": 0.28,
        "hip_width": 0.18,
        "robe_width": 0.38,
        "stance": "tall",
        "default_weapon": "staff",
        "default_symbol": "seal",
    },
    "solar_warrior_base": {
        "template_id": "solar_warrior_base",
        "archetype": "solar_warrior",
        "width_ratio": 0.72,
        "height_ratio": 0.74,
        "head_scale": (0.10, 0.14),
        "shoulder_width": 0.36,
        "hip_width": 0.20,
        "robe_width": 0.26,
        "stance": "heroic",
        "default_weapon": "spear",
        "default_symbol": "solar",
    },
    "guide_mage_base": {
        "template_id": "guide_mage_base",
        "archetype": "guide_mage",
        "width_ratio": 0.74,
        "height_ratio": 0.80,
        "head_scale": (0.10, 0.14),
        "shoulder_width": 0.24,
        "hip_width": 0.18,
        "robe_width": 0.34,
        "stance": "calm",
        "default_weapon": "staff",
        "default_symbol": "chakana",
    },
}


def resolve_character_template(semantic: dict) -> dict[str, object]:
    subject_kind = str(semantic.get("subject_kind", "") or "").lower()
    subject = str(semantic.get("subject", "") or "").lower()
    if "archon" in subject_kind or "archon" in subject or "arconte" in subject:
        return dict(CHARACTER_TEMPLATES["archon_base"])
    if any(tok in subject_kind for tok in ("oracle", "mage", "guide")) or any(tok in subject for tok in ("oracle", "mage", "guide")):
        return dict(CHARACTER_TEMPLATES["guide_mage_base"])
    return dict(CHARACTER_TEMPLATES["solar_warrior_base"])
