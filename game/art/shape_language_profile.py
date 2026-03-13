from __future__ import annotations

from game.art.style_lock import symbolic_style_active

SHAPE_LANGUAGE_PROFILES = {
    'archon': {
        'profile_id': 'archon_cathedral',
        'angularity': 0.82,
        'curve_bias': 0.26,
        'shoulder_scale': 1.08,
        'arm_taper': 0.84,
        'robe_spread': 1.02,
        'head_roundness': 0.86,
        'weapon_mass_bias': 0.82,
        'detail_density': 0.62,
        'torso_split': 0.84,
        'core_bridge': 1.24,
        'lane_offset': 0.07,
        'weapon_length_scale': 0.80,
        'weapon_thickness_scale': 0.98,
        'icon_scale': 0.96,
        'plane_break_strength': 0.92,
        'surface_simplification': 0.58,
    },
    'solar_warrior': {
        'profile_id': 'solar_heroic',
        'angularity': 0.68,
        'curve_bias': 0.34,
        'shoulder_scale': 1.14,
        'arm_taper': 0.96,
        'robe_spread': 0.90,
        'head_roundness': 0.92,
        'weapon_mass_bias': 0.94,
        'detail_density': 0.68,
        'torso_split': 0.94,
        'core_bridge': 1.14,
        'lane_offset': 0.08,
        'weapon_length_scale': 0.88,
        'weapon_thickness_scale': 0.96,
        'icon_scale': 0.94,
        'plane_break_strength': 0.90,
        'surface_simplification': 0.52,
    },
    'guide_mage': {
        'profile_id': 'guide_sacred_soft',
        'angularity': 0.42,
        'curve_bias': 0.72,
        'shoulder_scale': 0.96,
        'arm_taper': 0.78,
        'robe_spread': 1.06,
        'head_roundness': 1.04,
        'weapon_mass_bias': 0.80,
        'detail_density': 0.64,
        'torso_split': 0.84,
        'core_bridge': 1.28,
        'lane_offset': 0.06,
        'weapon_length_scale': 0.78,
        'weapon_thickness_scale': 0.96,
        'icon_scale': 0.92,
        'plane_break_strength': 0.86,
        'surface_simplification': 0.56,
    },
}


def resolve_shape_language(archetype: str) -> dict[str, float | str]:
    profile = dict(SHAPE_LANGUAGE_PROFILES.get(str(archetype), SHAPE_LANGUAGE_PROFILES['solar_warrior']))
    profile['style_lock_active'] = symbolic_style_active()
    if symbolic_style_active():
        profile['detail_density'] = round(float(profile['detail_density']) * 0.9, 4)
        profile['surface_simplification'] = round(min(1.0, float(profile['surface_simplification']) * 1.08), 4)
    else:
        profile['detail_density'] = round(float(profile['detail_density']) * 1.08, 4)
        profile['surface_simplification'] = round(max(0.35, float(profile['surface_simplification']) * 0.88), 4)
    return profile
