from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class EnvironmentPreset:
    preset_id: str
    horizon_ratio: float
    sky_treatment: str
    ground_treatment: str
    lighting_direction: str
    atmospheric_color: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


ENVIRONMENT_PRESETS: dict[str, EnvironmentPreset] = {
    "gaia_mountains": EnvironmentPreset(
        preset_id="gaia_mountains",
        horizon_ratio=0.66,
        sky_treatment="gold_violet_gradient",
        ground_treatment="mountain_plateau",
        lighting_direction="top_left",
        atmospheric_color="violet_mist",
    ),
    "sacred_forest": EnvironmentPreset(
        preset_id="sacred_forest",
        horizon_ratio=0.64,
        sky_treatment="turquoise_dawn",
        ground_treatment="forest_floor",
        lighting_direction="top_left",
        atmospheric_color="emerald_mist",
    ),
    "hyperborea_temple": EnvironmentPreset(
        preset_id="hyperborea_temple",
        horizon_ratio=0.63,
        sky_treatment="ice_sky",
        ground_treatment="frozen_temple_steps",
        lighting_direction="top_left",
        atmospheric_color="silver_haze",
    ),
    "archon_cathedral": EnvironmentPreset(
        preset_id="archon_cathedral",
        horizon_ratio=0.67,
        sky_treatment="void_crimson_sky",
        ground_treatment="obsidian_floor",
        lighting_direction="back_top",
        atmospheric_color="corruption_fog",
    ),
    "void_realm": EnvironmentPreset(
        preset_id="void_realm",
        horizon_ratio=0.68,
        sky_treatment="starless_void",
        ground_treatment="dark_ash_plain",
        lighting_direction="back_top",
        atmospheric_color="void_smoke",
    ),
    "ritual_altar": EnvironmentPreset(
        preset_id="ritual_altar",
        horizon_ratio=0.69,
        sky_treatment="ritual_dusk",
        ground_treatment="altar_platform",
        lighting_direction="top_left",
        atmospheric_color="sacred_haze",
    ),
    "astral_plateau": EnvironmentPreset(
        preset_id="astral_plateau",
        horizon_ratio=0.65,
        sky_treatment="astral_band",
        ground_treatment="plateau_lines",
        lighting_direction="top_left",
        atmospheric_color="cosmic_dust",
    ),
}


def resolve_environment_preset(scene_type: str, environment_kind: str, environment_text: str) -> EnvironmentPreset:
    scene = str(scene_type or "").lower()
    kind = str(environment_kind or "").lower()
    env = str(environment_text or "").lower()

    if "hyperborea" in scene or "citadel" in kind or "polar" in env:
        return ENVIRONMENT_PRESETS["hyperborea_temple"]
    if "archon" in scene or "throne" in kind or "void" in env:
        if "cathedral" in env or "throne" in env:
            return ENVIRONMENT_PRESETS["archon_cathedral"]
        return ENVIRONMENT_PRESETS["void_realm"]
    if "beast" in scene or "forest" in env or "jungle" in env or "selva" in env:
        return ENVIRONMENT_PRESETS["sacred_forest"]
    if "ritual_duel" in scene or "altar" in env:
        return ENVIRONMENT_PRESETS["ritual_altar"]
    if "astral" in env or "plateau" in env:
        return ENVIRONMENT_PRESETS["astral_plateau"]
    return ENVIRONMENT_PRESETS["gaia_mountains"]
