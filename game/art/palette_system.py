from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class CivilizationPalette:
    palette_id: str
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    accent: tuple[int, int, int]
    shadow: tuple[int, int, int]
    glow: tuple[int, int, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


CIVILIZATION_PALETTES: dict[str, CivilizationPalette] = {
    "chakana": CivilizationPalette(
        palette_id="chakana",
        primary=(112, 78, 156),
        secondary=(54, 116, 124),
        accent=(226, 196, 110),
        shadow=(24, 18, 34),
        glow=(244, 224, 152),
    ),
    "hyperborea": CivilizationPalette(
        palette_id="hyperborea",
        primary=(188, 218, 246),
        secondary=(114, 146, 188),
        accent=(244, 244, 252),
        shadow=(26, 34, 56),
        glow=(224, 244, 255),
    ),
    "archon": CivilizationPalette(
        palette_id="archon",
        primary=(118, 24, 46),
        secondary=(42, 178, 104),
        accent=(210, 78, 102),
        shadow=(12, 8, 18),
        glow=(110, 255, 178),
    ),
}


def _detect_civilization(semantic: dict) -> str:
    scene = str(semantic.get("scene_type", "") or "").lower()
    subject_kind = str(semantic.get("subject_kind", "") or "").lower()
    environment_kind = str(semantic.get("environment_kind", "") or "").lower()
    palette = str(semantic.get("palette", "") or "").lower()
    environment = str(semantic.get("environment", "") or "").lower()

    if any(k in scene for k in ("archon", "void")) or any(k in subject_kind for k in ("archon",)) or any(k in environment_kind for k in ("throne",)) or any(k in palette for k in ("crimson", "toxic green", "black")) or "void" in environment:
        return "archon"
    if any(k in scene for k in ("hyperborea",)) or any(k in subject_kind for k in ("hyperborean",)) or any(k in environment_kind for k in ("citadel",)) or any(k in palette for k in ("ice blue", "silver", "white")) or any(k in environment for k in ("polar", "glacial", "citadel")):
        return "hyperborea"
    return "chakana"


def resolve_civilization_palette(semantic: dict) -> CivilizationPalette:
    return CIVILIZATION_PALETTES[_detect_civilization(semantic)]


def palette_system_summary() -> dict[str, object]:
    return {
        "preset_count": len(CIVILIZATION_PALETTES),
        "palettes": {key: value.to_dict() for key, value in CIVILIZATION_PALETTES.items()},
    }
