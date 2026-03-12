from __future__ import annotations

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
        'detail_density': 0.58,
        'torso_split': 0.78,
        'core_bridge': 1.20,
        'lane_offset': 0.08,
        'weapon_length_scale': 0.84,
        'weapon_thickness_scale': 0.88,
        'icon_scale': 0.82,
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
        'detail_density': 0.54,
        'torso_split': 0.92,
        'core_bridge': 1.10,
        'lane_offset': 0.09,
        'weapon_length_scale': 0.92,
        'weapon_thickness_scale': 0.94,
        'icon_scale': 0.92,
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
        'detail_density': 0.62,
        'torso_split': 0.82,
        'core_bridge': 1.24,
        'lane_offset': 0.07,
        'weapon_length_scale': 0.80,
        'weapon_thickness_scale': 0.86,
        'icon_scale': 0.78,
    },
}


def resolve_shape_language(archetype: str) -> dict[str, float | str]:
    return dict(SHAPE_LANGUAGE_PROFILES.get(str(archetype), SHAPE_LANGUAGE_PROFILES['solar_warrior']))
