from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecondaryObjectPreset:
    object_id: str
    family: str
    frame_ratio: float
    lore_tags: tuple[str, ...]
    palette_bias: str


SECONDARY_OBJECT_PRESETS: dict[str, SecondaryObjectPreset] = {
    "chakana_symbol": SecondaryObjectPreset("chakana_symbol", "symbol", 0.18, ("chakana", "order", "ritual"), "chakana"),
    "ritual_staff": SecondaryObjectPreset("ritual_staff", "weapon", 0.22, ("staff", "oracle", "ritual"), "chakana"),
    "spear": SecondaryObjectPreset("spear", "weapon", 0.22, ("spear", "warrior", "guardian"), "chakana"),
    "sword": SecondaryObjectPreset("sword", "weapon", 0.24, ("sword", "warrior", "hero"), "chakana"),
    "orb": SecondaryObjectPreset("orb", "focus", 0.18, ("orb", "vision", "oracle"), "chakana"),
    "relic": SecondaryObjectPreset("relic", "relic", 0.22, ("relic", "altar", "seal"), "chakana"),
    "altar": SecondaryObjectPreset("altar", "relic", 0.25, ("altar", "ritual", "ceremonial"), "chakana"),
    "banner": SecondaryObjectPreset("banner", "symbol", 0.19, ("banner", "standard", "faction"), "archon"),
    "crystal": SecondaryObjectPreset("crystal", "focus", 0.20, ("crystal", "hyperborea", "solar"), "hyperborea"),
    "greatsword": SecondaryObjectPreset("greatsword", "weapon", 0.26, ("greatsword", "warrior", "hero"), "chakana"),
    "solar_axe": SecondaryObjectPreset("solar_axe", "weapon", 0.26, ("axe", "solar", "hyperborea"), "hyperborea"),
    "seal_tablet": SecondaryObjectPreset("seal_tablet", "relic", 0.24, ("seal", "tablet", "archon"), "archon"),
    "codex": SecondaryObjectPreset("codex", "relic", 0.22, ("codex", "oracle", "divination"), "chakana"),
    "shield": SecondaryObjectPreset("shield", "relic", 0.23, ("shield", "guardian", "ward"), "chakana"),
    "crown": SecondaryObjectPreset("crown", "symbol", 0.18, ("crown", "throne", "archon"), "archon"),
}


OBJECT_KIND_TO_PRESET_ID: dict[str, str] = {
    "weapon": "sword",
    "spear": "spear",
    "staff": "ritual_staff",
    "ritual_staff": "ritual_staff",
    "greatsword": "greatsword",
    "solar_axe": "solar_axe",
    "codex": "codex",
    "altar": "altar",
    "seal": "relic",
    "seal_tablet": "seal_tablet",
    "crown": "crown",
    "shield": "shield",
    "orb": "orb",
    "orb_focus": "orb",
}


def resolve_secondary_object(kind: str, text: str = "") -> SecondaryObjectPreset:
    key = str(kind or "").lower().replace(" ", "_")
    text_low = str(text or "").lower()
    preset_id = OBJECT_KIND_TO_PRESET_ID.get(key, "")
    if not preset_id:
        if any(tok in text_low for tok in ("spear", "lanza")):
            preset_id = "spear"
        elif any(tok in text_low for tok in ("staff", "baston", "vara")):
            preset_id = "ritual_staff"
        elif any(tok in text_low for tok in ("banner", "standard")):
            preset_id = "banner"
        elif any(tok in text_low for tok in ("crystal", "cristal")):
            preset_id = "crystal"
        elif any(tok in text_low for tok in ("orb", "sphere", "esfera")):
            preset_id = "orb"
        elif any(tok in text_low for tok in ("altar", "brazier", "relic", "seal")):
            preset_id = "altar"
        else:
            preset_id = "relic"
    return SECONDARY_OBJECT_PRESETS[preset_id]


def secondary_object_library_summary() -> dict[str, dict]:
    return {
        "preset_count": len(SECONDARY_OBJECT_PRESETS),
        "presets": {
            key: {
                "family": preset.family,
                "frame_ratio": preset.frame_ratio,
                "lore_tags": preset.lore_tags,
                "palette_bias": preset.palette_bias,
            }
            for key, preset in SECONDARY_OBJECT_PRESETS.items()
        },
    }
