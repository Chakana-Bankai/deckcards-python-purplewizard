from __future__ import annotations

OBJECT_GLYPH_GRAMMARS = {
    'staff': {
        'glyph_id': 'staff_cathedral_glyph',
        'head_scale': 2.8,
        'wing_scale': 2.2,
        'plate_scale': 1.6,
        'satellite_scale': 0.9,
    },
    'orb': {
        'glyph_id': 'orb_sacred_glyph',
        'head_scale': 2.5,
        'wing_scale': 2.0,
        'plate_scale': 1.4,
        'satellite_scale': 0.82,
    },
    'spear': {
        'glyph_id': 'spear_heroic_glyph',
        'head_scale': 2.2,
        'wing_scale': 1.6,
        'plate_scale': 1.1,
        'satellite_scale': 0.0,
    },
    'sword': {
        'glyph_id': 'sword_guard_glyph',
        'head_scale': 1.8,
        'wing_scale': 1.2,
        'plate_scale': 1.0,
        'satellite_scale': 0.0,
    },
}


def resolve_object_glyph_grammar(family: str) -> dict[str, float | str]:
    return dict(OBJECT_GLYPH_GRAMMARS.get(str(family), OBJECT_GLYPH_GRAMMARS['staff']))
