from __future__ import annotations

WEAPON_TEMPLATES = {
    "staff": {"weapon_id": "staff", "family": "staff", "length": 0.58, "thickness": 0.068},
    "spear": {"weapon_id": "spear", "family": "spear", "length": 0.60, "thickness": 0.078},
    "sword": {"weapon_id": "sword", "family": "sword", "length": 0.54, "thickness": 0.078},
    "orb": {"weapon_id": "orb", "family": "orb", "length": 0.22, "thickness": 0.095},
}


def resolve_weapon_template(semantic: dict, template: dict[str, object]) -> dict[str, object]:
    text = ' '.join([str(semantic.get('object_kind', '') or ''), str(semantic.get('object', '') or ''), str(semantic.get('secondary_object', '') or '')]).lower()
    if 'spear' in text:
        return dict(WEAPON_TEMPLATES['spear'])
    if 'sword' in text or 'blade' in text:
        return dict(WEAPON_TEMPLATES['sword'])
    if 'orb' in text and 'staff' not in text:
        return dict(WEAPON_TEMPLATES['orb'])
    if 'staff' in text or 'ritual_staff' in text or 'baston' in text:
        return dict(WEAPON_TEMPLATES['staff'])
    return dict(WEAPON_TEMPLATES[str(template.get('default_weapon', 'staff'))])
