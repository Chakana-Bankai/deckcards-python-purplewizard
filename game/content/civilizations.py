from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Civilization:
    id: str
    title: str
    description: str


CIVILIZATIONS: dict[str, Civilization] = {
    "base_world": Civilization("base_world", "Mundo Base", "Conocimiento ritual conocido."),
    "hiperborea": Civilization("hiperborea", "Hiperborea", "Conocimiento antiguo de la Chakana Polar."),
}


def civilization_for_progress(stage_index: int) -> str:
    """Progressive set discovery selector (safe, deterministic rule)."""
    if stage_index <= 0:
        return "base_world"
    if stage_index == 1:
        return "base_world"
    return "hiperborea"


def civilization_title(civ_id: str) -> str:
    return CIVILIZATIONS.get(str(civ_id or "base_world"), CIVILIZATIONS["base_world"]).title
