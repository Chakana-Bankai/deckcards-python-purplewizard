from __future__ import annotations

from game.art.style_lock import symbolic_style_active

OBJECT_GLYPH_GRAMMARS = {
    'staff': {
        'glyph_id': 'staff_cathedral_glyph',
        'head_scale': 2.35,
        'wing_scale': 1.75,
        'plate_scale': 1.28,
        'satellite_scale': 0.52,
        'edge_hardness': 0.94,
    },
    'orb': {
        'glyph_id': 'orb_sacred_glyph',
        'head_scale': 2.10,
        'wing_scale': 1.62,
        'plate_scale': 1.20,
        'satellite_scale': 0.42,
        'edge_hardness': 0.90,
    },
    'spear': {
        'glyph_id': 'spear_heroic_glyph',
        'head_scale': 2.36,
        'wing_scale': 1.82,
        'plate_scale': 1.18,
        'satellite_scale': 0.0,
        'edge_hardness': 0.96,
    },
    'sword': {
        'glyph_id': 'sword_guard_glyph',
        'head_scale': 1.56,
        'wing_scale': 1.06,
        'plate_scale': 0.92,
        'satellite_scale': 0.0,
        'edge_hardness': 0.96,
    },
}


def resolve_object_glyph_grammar(family: str) -> dict[str, float | str]:
    glyph = dict(OBJECT_GLYPH_GRAMMARS.get(str(family), OBJECT_GLYPH_GRAMMARS['staff']))
    glyph['style_lock_active'] = symbolic_style_active()
    return glyph
