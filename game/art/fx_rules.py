from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FxRule:
    effect_id: str
    family: str
    max_frame_ratio: float
    particle_count: int
    palette_bias: str
    avoid_subject_core: bool = True
    alpha_min: int = 72
    alpha_max: int = 132


FX_RULES: dict[str, FxRule] = {
    "aura_glow": FxRule("aura_glow", "aura_glow", 0.12, 6, "chakana", alpha_min=58, alpha_max=108),
    "sacred_wind": FxRule("sacred_wind", "sacred_wind", 0.10, 7, "chakana", alpha_min=64, alpha_max=112),
    "rune_particles": FxRule("rune_particles", "rune_particles", 0.10, 10, "chakana", alpha_min=84, alpha_max=138),
    "corruption_smoke": FxRule("corruption_smoke", "corruption_smoke", 0.14, 6, "archon", alpha_min=56, alpha_max=96),
    "solar_light": FxRule("solar_light", "solar_light", 0.12, 5, "hyperborea", alpha_min=86, alpha_max=146),
    "void_sparks": FxRule("void_sparks", "void_sparks", 0.10, 8, "archon", alpha_min=86, alpha_max=144),
}


def resolve_fx_rule(semantic: dict) -> FxRule:
    text = " ".join(
        [
            str(semantic.get("effects", "") or ""),
            str(semantic.get("effects_desc", "") or ""),
            str(semantic.get("energy", "") or ""),
            str(semantic.get("mood", "") or ""),
            str(semantic.get("scene_type", "") or ""),
            str(semantic.get("environment_kind", "") or ""),
        ]
    ).lower()
    subject_kind = str(semantic.get("subject_kind", "") or "").lower()

    if any(k in text for k in ("corruption", "malign", "decree", "void", "archon")) or "archon" in subject_kind:
        if "smoke" in text or "corrupt" in text:
            return FX_RULES["corruption_smoke"]
        return FX_RULES["void_sparks"]
    if any(k in text for k in ("solar", "polar", "hyperborea", "aurora", "ice")):
        return FX_RULES["solar_light"]
    if any(k in text for k in ("wind", "ward", "harmonic", "resonance", "sacred wind")):
        return FX_RULES["sacred_wind"]
    if any(k in text for k in ("rune", "oracle", "prophetic", "glyph", "particle")):
        return FX_RULES["rune_particles"]
    if any(k in text for k in ("aura", "glow", "halo")):
        return FX_RULES["aura_glow"]
    return FX_RULES["rune_particles"]


def fx_rules_summary() -> dict:
    return {
        "preset_count": len(FX_RULES),
        "rules": {key: asdict(rule) for key, rule in FX_RULES.items()},
    }
