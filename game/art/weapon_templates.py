from __future__ import annotations

from game.art.style_lock import symbolic_style_active

WEAPON_TEMPLATES = {
    "staff": {"weapon_id": "staff", "family": "staff", "length": 0.52, "thickness": 0.076},
    "spear": {"weapon_id": "spear", "family": "spear", "length": 0.60, "thickness": 0.104},
    "sword": {"weapon_id": "sword", "family": "sword", "length": 0.46, "thickness": 0.086},
    "orb": {"weapon_id": "orb", "family": "orb", "length": 0.20, "thickness": 0.104},
}


def resolve_weapon_template(semantic: dict, template: dict[str, object]) -> dict[str, object]:
    text = ' '.join([str(semantic.get('object_kind', '') or ''), str(semantic.get('object', '') or ''), str(semantic.get('secondary_object', '') or '')]).lower()
    if 'spear' in text:
        weapon = dict(WEAPON_TEMPLATES['spear'])
    elif 'sword' in text or 'blade' in text:
        weapon = dict(WEAPON_TEMPLATES['sword'])
    elif 'orb' in text and 'staff' not in text:
        weapon = dict(WEAPON_TEMPLATES['orb'])
    elif 'staff' in text or 'ritual_staff' in text or 'baston' in text:
        weapon = dict(WEAPON_TEMPLATES['staff'])
    else:
        weapon = dict(WEAPON_TEMPLATES[str(template.get('default_weapon', 'staff'))])
    weapon['style_lock_active'] = symbolic_style_active()
    return weapon
