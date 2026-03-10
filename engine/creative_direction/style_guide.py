from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtStyleSpec:
    set_id: str
    palette: tuple[str, ...]
    composition: tuple[str, str, str, str]
    motifs: tuple[str, ...]
    tone: str


@dataclass(frozen=True)
class MusicStyleSpec:
    context: str
    tempo: str
    harmony: str
    rhythm: str
    ambient: str


class CreativeStyleGuide:
    """Canonical style rules used by the creative director loops."""

    ART_SET_STYLES: dict[str, ArtStyleSpec] = {
        "base": ArtStyleSpec(
            set_id="base",
            palette=("gold", "violet", "cosmic_blue"),
            composition=("subject", "object", "environment", "effects"),
            motifs=("chakana", "sacred_geometry", "ritual_sigils"),
            tone="mystic_geometry",
        ),
        "hiperborea": ArtStyleSpec(
            set_id="hiperborea",
            palette=("ice_blue", "marble_white", "ancient_gold"),
            composition=("subject", "object", "environment", "effects"),
            motifs=("crystals", "polar_temple", "aurora_geometry"),
            tone="ancient_advanced_civilization",
        ),
        "archon": ArtStyleSpec(
            set_id="archon",
            palette=("deep_red", "black", "corrupted_violet"),
            composition=("subject", "object", "environment", "effects"),
            motifs=("void_runes", "distorted_mandala", "corruption_spikes"),
            tone="dark_corruption",
        ),
    }

    MUSIC_CONTEXT_STYLES: dict[str, MusicStyleSpec] = {
        "menu": MusicStyleSpec("menu", "slow", "modal_ritual", "sparse_pulse", "mystical_pad"),
        "map": MusicStyleSpec("map", "mid", "evolving_minor", "travel_pulse", "atmospheric_wind"),
        "shop": MusicStyleSpec("shop", "slow", "warm_modal", "ceremonial_ticks", "intimate_air"),
        "combat": MusicStyleSpec("combat", "mid_fast", "tense_minor", "driven_pattern", "arcane_noise"),
        "boss": MusicStyleSpec("boss", "fast", "ceremonial_dark", "heavy_ritual", "cathedral_low_end"),
        "reward": MusicStyleSpec("reward", "slow_mid", "uplift_mode", "short_phrase", "sparkle_bed"),
    }

    LORE_KEYS_BY_SET: dict[str, tuple[str, ...]] = {
        "base": ("chakana", "balance", "ritual_order"),
        "hiperborea": ("forgotten_knowledge", "crystalline_civilization", "polar_light"),
        "archon": ("rupture", "corruption", "void_pressure"),
    }

    def resolve_set_style(self, set_id: str) -> ArtStyleSpec:
        key = str(set_id or "base").strip().lower()
        return self.ART_SET_STYLES.get(key, self.ART_SET_STYLES["base"])

    def resolve_music_style(self, context: str) -> MusicStyleSpec:
        key = str(context or "menu").strip().lower()
        if key.startswith("map"):
            key = "map"
        elif key.startswith("combat"):
            key = "combat"
        elif key.startswith("boss"):
            key = "boss"
        return self.MUSIC_CONTEXT_STYLES.get(key, self.MUSIC_CONTEXT_STYLES["menu"])

    def lore_keys_for_set(self, set_id: str) -> tuple[str, ...]:
        key = str(set_id or "base").strip().lower()
        return self.LORE_KEYS_BY_SET.get(key, self.LORE_KEYS_BY_SET["base"])
