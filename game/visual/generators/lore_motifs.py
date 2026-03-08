from __future__ import annotations

"""Lore motif catalog shared by visual generators and prompt builders."""

MOTIF_LIBRARY: dict[str, dict[str, tuple[str, ...] | str]] = {
    "chakana": {
        "shapes": ("stepped_cross", "four_gate_frame", "axis_lines"),
        "symbols": ("chakana", "solar_knot", "ritual_nodes"),
        "energy": ("violet_arc", "cyan_trace"),
        "tone": "sacred_balance",
    },
    "mountains": {
        "shapes": ("tri_ridge", "andes_horizon"),
        "symbols": ("condor_path", "stone_marks"),
        "energy": ("wind_threads",),
        "tone": "earth_ritual",
    },
    "cosmic_geometry": {
        "shapes": ("orbital_rings", "constellation_grid", "hex_rosette"),
        "symbols": ("astral_eye", "star_points"),
        "energy": ("aurora_stream", "void_spark"),
        "tone": "astral_focus",
    },
    "angels": {
        "shapes": ("halo_arcs", "wing_rays"),
        "symbols": ("seraphic_seal", "luminous_feather"),
        "energy": ("golden_radiance",),
        "tone": "celestial_guard",
    },
    "demons": {
        "shapes": ("horn_spike", "fractured_ring"),
        "symbols": ("abyss_glyph", "ember_teeth"),
        "energy": ("crimson_smoke", "void_flare"),
        "tone": "corrupt_drive",
    },
    "archons": {
        "shapes": ("oracle_mask", "broken_halo"),
        "symbols": ("archon_sigil", "rift_mark"),
        "energy": ("red_interference", "dark_pulse"),
        "tone": "prophetic_threat",
    },
    "ritual_symbols": {
        "shapes": ("altar_circle", "step_nodes"),
        "symbols": ("glyph_chain", "seal_lock"),
        "energy": ("chant_wave",),
        "tone": "ceremonial_charge",
    },
    "sacred_forms": {
        "shapes": ("diamond_frame", "mandala_core"),
        "symbols": ("sacred_ratio", "axis_lock"),
        "energy": ("quiet_glow",),
        "tone": "mystic_order",
    },
}

ARCHETYPE_TO_MOTIFS: dict[str, tuple[str, ...]] = {
    "cosmic_warrior": ("chakana", "demons", "cosmic_geometry"),
    "harmony_guardian": ("chakana", "angels", "sacred_forms"),
    "oracle_of_fate": ("archons", "cosmic_geometry", "ritual_symbols"),
}


def motifs_for_archetype(archetype: str) -> tuple[str, ...]:
    key = str(archetype or "").lower().strip()
    return ARCHETYPE_TO_MOTIFS.get(key, ("chakana", "cosmic_geometry"))
