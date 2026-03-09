"""Non-destructive procedural content supervision rules."""

from __future__ import annotations

ART_DIRECTOR_RULES = {
    "diversity_by_class": {
        "cards": 0.70,
        "avatars": 0.75,
        "enemies": 0.72,
        "biomes": 0.78,
        "holograms": 0.68,
        "symbols": 0.66,
    },
    "seed_variation_min": 3,
    "palette_diversity_threshold": 0.55,
    "motif_variation_min": 4,
    "allow_near_duplicates": False,
}

BIOME_VARIATION_RULES = {
    "ukhu": {"motif_family": "fracture_void", "temperature": "cold_dark", "depth": "low_fog"},
    "kaypacha": {"motif_family": "ritual_balance", "temperature": "neutral_mystic", "depth": "mid_layers"},
    "hanan": {"motif_family": "celestial_geometry", "temperature": "bright_cold", "depth": "high_sky"},
    "fractura_chakana": {"motif_family": "broken_reality", "temperature": "contrast_extreme", "depth": "rift_layers"},
}

AUDIO_DIRECTOR_RULES = {
    "menu": {"tempo": "slow", "rhythm": "sparse", "tonal_center": "D", "intensity": "low"},
    "map": {"tempo": "mid", "rhythm": "ambient_pulse", "tonal_center": "A", "intensity": "medium_low"},
    "shop": {"tempo": "slow", "rhythm": "ritual", "tonal_center": "F", "intensity": "low"},
    "combat": {"tempo": "mid_fast", "rhythm": "driven", "tonal_center": "E", "intensity": "high"},
    "boss": {"tempo": "fast", "rhythm": "ceremonial_hard", "tonal_center": "C", "intensity": "very_high"},
    "reward": {"tempo": "slow_mid", "rhythm": "stinger", "tonal_center": "G", "intensity": "medium"},
    "scene": {"tempo": "adaptive", "rhythm": "free", "tonal_center": "context", "intensity": "adaptive"},
}

AUDIO_VARIATION_RULES = {
    "min_rhythm_templates": 3,
    "min_instrument_combos": 3,
    "min_progression_profiles": 3,
    "block_dominant_whistle": True,
    "detect_near_identical_signature": True,
}
