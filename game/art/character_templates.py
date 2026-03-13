from __future__ import annotations

from game.art.style_lock import symbolic_style_active

CHARACTER_TEMPLATES = {
    "archon_base": {
        "template_id": "archon_base",
        "archetype": "archon",
        "width_ratio": 0.34,
        "height_ratio": 0.44,
        "dominant_shape": "circle",
        "style_family": "illustrated_mythic_archon",
        "render_binding": {
            "prop_lane_mode": "side_lane_short_grip",
            "costume_plane_mode": "cathedral_split_planes",
            "surface_mode": "matte_cloth_high_detail",
        },
        "head_scale": (0.08, 0.13),
        "head_size": {"ratio_range": (0.16, 0.17), "shape": "narrow_masked_oval"},
        "torso_mass": {"shape": "vertical_cathedral_core", "width_ratio": 0.68, "height_ratio": 0.72},
        "arm_length": {"ratio_range": (0.30, 0.34), "gesture": "ritual_forward_hold"},
        "weapon_anchor": {"primary": "right_hand_anchor", "secondary": "symbol_center_anchor"},
        "cape_or_ornament_areas": ["ritual_cloak_left", "ritual_cloak_right", "void_collar", "sigil_back_plane"],
        "silhouette_outline": {"profile": "tall_vertical_split_cloak", "dominant_angles": "severe_stepped", "negative_space": "torso_staff_gap"},
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
        "width_ratio": 0.35,
        "height_ratio": 0.45,
        "dominant_shape": "triangle",
        "style_family": "illustrated_mythic_solar",
        "render_binding": {
            "prop_lane_mode": "forward_diagonal_short_grip",
            "costume_plane_mode": "heroic_plate_planes",
            "surface_mode": "metal_cloth_high_detail",
        },
        "head_scale": (0.10, 0.14),
        "head_size": {"ratio_range": (0.16, 0.18), "shape": "helmeted_oval"},
        "torso_mass": {"shape": "heroic_triangle", "width_ratio": 0.72, "height_ratio": 0.74},
        "arm_length": {"ratio_range": (0.31, 0.35), "gesture": "forward_attack_ready"},
        "weapon_anchor": {"primary": "right_hand_anchor", "secondary": "back_anchor"},
        "cape_or_ornament_areas": ["shoulder_guard_left", "shoulder_guard_right", "waist_fauld", "solar_back_standard"],
        "silhouette_outline": {"profile": "broad_shoulders_narrow_waist_stable_legs", "dominant_angles": "angular", "negative_space": "open_weapon_side"},
        "shoulder_width": 0.36,
        "hip_width": 0.20,
        "robe_width": 0.26,
        "stance": "heroic",
        "default_weapon": "spear",
        "default_symbol": "solar",
    },
    "guardian_sentinel_base": {
        "template_id": "guardian_sentinel_base",
        "archetype": "solar_warrior",
        "width_ratio": 0.36,
        "height_ratio": 0.46,
        "dominant_shape": "shield",
        "style_family": "illustrated_mythic_guardian",
        "render_binding": {
            "prop_lane_mode": "guard_front_anchor",
            "costume_plane_mode": "bastion_plate_planes",
            "surface_mode": "temple_plate_mid_high_detail",
        },
        "head_scale": (0.10, 0.14),
        "head_size": {"ratio_range": (0.16, 0.18), "shape": "guard_helm_oval"},
        "torso_mass": {"shape": "shield_bastion_core", "width_ratio": 0.76, "height_ratio": 0.78},
        "arm_length": {"ratio_range": (0.30, 0.34), "gesture": "defensive_anchor_hold"},
        "weapon_anchor": {"primary": "left_hand_anchor", "secondary": "right_hand_anchor"},
        "cape_or_ornament_areas": ["mantle_left", "mantle_right", "chest_guard", "waist_talisman"],
        "silhouette_outline": {"profile": "fortified_shielded_stance", "dominant_angles": "bastion_stepped", "negative_space": "open_guard_lane"},
        "shoulder_width": 0.38,
        "hip_width": 0.22,
        "robe_width": 0.24,
        "stance": "anchored",
        "default_weapon": "sword",
        "default_symbol": "shield",
    },
    "guide_mage_base": {
        "template_id": "guide_mage_base",
        "archetype": "guide_mage",
        "width_ratio": 0.33,
        "height_ratio": 0.43,
        "dominant_shape": "rectangle",
        "style_family": "illustrated_mythic_guide",
        "render_binding": {
            "prop_lane_mode": "support_side_short_grip",
            "costume_plane_mode": "soft_robe_planes",
            "surface_mode": "soft_cloth_mid_high_detail",
        },
        "head_scale": (0.10, 0.14),
        "head_size": {"ratio_range": (0.16, 0.18), "shape": "soft_hooded_oval"},
        "torso_mass": {"shape": "calm_column_split_robe", "width_ratio": 0.74, "height_ratio": 0.80},
        "arm_length": {"ratio_range": (0.30, 0.34), "gesture": "support_focus_hold"},
        "weapon_anchor": {"primary": "left_hand_anchor", "secondary": "right_hand_anchor"},
        "cape_or_ornament_areas": ["hood_back", "chest_sash", "robe_split_left", "robe_split_right"],
        "silhouette_outline": {"profile": "soft_vertical_open_chest", "dominant_angles": "curved_ritual", "negative_space": "support_hand_symbol_gap"},
        "shoulder_width": 0.24,
        "hip_width": 0.18,
        "robe_width": 0.34,
        "stance": "calm",
        "default_weapon": "staff",
        "default_symbol": "chakana",
    },
    "oracle_seer_base": {
        "template_id": "oracle_seer_base",
        "archetype": "guide_mage",
        "width_ratio": 0.32,
        "height_ratio": 0.44,
        "dominant_shape": "lens",
        "style_family": "illustrated_mythic_oracle",
        "render_binding": {
            "prop_lane_mode": "focus_forward_float",
            "costume_plane_mode": "seer_layered_robe_planes",
            "surface_mode": "arcane_cloth_mid_high_detail",
        },
        "head_scale": (0.10, 0.14),
        "head_size": {"ratio_range": (0.16, 0.18), "shape": "seer_hooded_oval"},
        "torso_mass": {"shape": "divination_column_split_robe", "width_ratio": 0.70, "height_ratio": 0.82},
        "arm_length": {"ratio_range": (0.30, 0.35), "gesture": "oracle_focus_hold"},
        "weapon_anchor": {"primary": "right_hand_anchor", "secondary": "left_hand_anchor"},
        "cape_or_ornament_areas": ["hood_back", "oracle_sash", "seer_panel_left", "seer_panel_right"],
        "silhouette_outline": {"profile": "seer_vertical_open_focus", "dominant_angles": "curved_ritual", "negative_space": "floating_focus_gap"},
        "shoulder_width": 0.22,
        "hip_width": 0.17,
        "robe_width": 0.36,
        "stance": "oracular",
        "default_weapon": "orb",
        "default_symbol": "eye",
    },
}


def resolve_character_template(semantic: dict) -> dict[str, object]:
    subject_kind = str(semantic.get("subject_kind", "") or "").lower()
    subject = str(semantic.get("subject", "") or "").lower()
    if "archon" in subject_kind or "archon" in subject or "arconte" in subject:
        template = dict(CHARACTER_TEMPLATES["archon_base"])
    elif any(tok in subject_kind for tok in ("oracle", "seer", "totem")) or any(tok in subject for tok in ("oracle", "seer", "divination")):
        template = dict(CHARACTER_TEMPLATES["oracle_seer_base"])
    elif any(tok in subject_kind for tok in ("guardian", "bearer", "sentinel")) or any(tok in subject for tok in ("guardian", "sentinel", "shield")):
        template = dict(CHARACTER_TEMPLATES["guardian_sentinel_base"])
    elif any(tok in subject_kind for tok in ("mage", "guide")) or any(tok in subject for tok in ("mage", "guide")):
        template = dict(CHARACTER_TEMPLATES["guide_mage_base"])
    else:
        template = dict(CHARACTER_TEMPLATES["solar_warrior_base"])
    template["style_lock_active"] = symbolic_style_active()
    return template
