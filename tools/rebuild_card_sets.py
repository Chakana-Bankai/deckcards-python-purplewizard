from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game" / "data"
DOCS = ROOT / "docs" / "design"


ARCHETYPE_META = {
    "cosmic_warrior": {
        "label": "Cosmic Warrior",
        "base_set": "Orden Solar",
        "expansion_set": "Ascenso Boreal",
        "palette": "crimson-magenta",
        "energy": "burst_arcs",
        "symbol": "blade_sigil",
        "motif": "solar_beasts",
        "order": "Chakana",
        "author": "Chakana Studio",
        "directions": {"creature": "ESTE", "subject": "SUR", "object": "OESTE", "place": "NORTE"},
        "base_names": {
            "creature": [
                "Jaguar del Umbral Solar",
                "Condor de las Brasas Altas",
                "Puma de la Lluvia Roja",
                "Serpiente del Arco Helico",
                "Venado del Filo Dorado",
            ],
            "subject": [
                "Duelista de los Dos Cielos",
                "Lancero del Hanan Vivo",
                "Centinela del Disco Solar",
                "Peregrino de la Chispa Firme",
                "Forjadora del Cenit Carmesi",
            ],
            "object": [
                "Lanza del Cenit",
                "Mandoble de Estrella Hueca",
                "Broquel de Meteorito",
                "Espuelas del Relampago Quieto",
                "Estandarte del Sol Partido",
            ],
            "place": [
                "Terraza del Eclipse",
                "Puente del Cobre Celeste",
                "Arena de las Siete Chispas",
                "Foso del Sol Guardado",
                "Muralla del Trueno Alto",
            ],
        },
        "expansion_names": {
            "creature": [
                "Halcon del Septimo Sol",
                "Llama de Guerra Celeste",
                "Toro de Meteorito Vivo",
                "Zorro del Alba Cortante",
                "Leon del Cielo Roto",
            ],
            "subject": [
                "Guarda del Horizonte Rojo",
                "Navegante de Cometas",
                "Capitan del Pulso Boreal",
                "Portadora de la Corona de Fuego",
                "Maestro de la Fractura Serena",
            ],
            "object": [
                "Cinturon de Runa Roja",
                "Tambor del Impacto Astral",
                "Arnes del Jaguar Solar",
                "Casco de Obsidiana Viva",
                "Brasa del Condor Antiguo",
            ],
            "place": [
                "Camino del Primer Relampago",
                "Mirador del Jaguar Espejo",
                "Plaza de la Aurora Belica",
                "Santuario del Filo Resonante",
                "Forja del Ultimo Cometa",
            ],
        },
        "lore": {
            "base": {
                "creature": "Las bestias del Hanan aprenden a pelear sin romper el pulso de la Chakana.",
                "subject": "Los sujetos del set solar convierten disciplina en agresion calculada.",
                "object": "Las armas y talismanes del set solar recompensan presion y ruptura.",
                "place": "Los lugares del set solar empujan tempo, cierre y posicion tactica.",
            },
            "expansion": {
                "creature": "Hiperborea graba al guerrero en hielo vivo: cada criatura exige un remate.",
                "subject": "Los campeones boreales giran la ventaja hacia secuencias de burst mas limpias.",
                "object": "Los objetos polares aceleran energia, ruptura y castigo sobre enemigos abiertos.",
                "place": "Los escenarios boreales fuerzan lineas ofensivas distintas en cada run.",
            },
        },
        "strategy": {
            "attack": ("Abrir defensa enemiga y cerrar antes del reshuffle.", "Pierde valor si la run no capitaliza ruptura."),
            "combo": ("Encadenar cartas cortas para convertir una ventana en letal.", "Depende del orden de mano y castiga manos pasivas."),
            "energy": ("Acelerar el siguiente turno para sostener presion.", "No renta si no hay payoff en mano."),
        },
    },
    "harmony_guardian": {
        "label": "Harmony Guardian",
        "base_set": "Custodios del Kay",
        "expansion_set": "Santuario Blanco",
        "palette": "teal-gold",
        "energy": "stable_rings",
        "symbol": "shield_mandala",
        "motif": "sacred_forms",
        "order": "Chakana",
        "author": "Chakana Studio",
        "directions": {"creature": "SUR", "subject": "OESTE", "object": "ESTE", "place": "NORTE"},
        "base_names": {
            "creature": [
                "Condor del Velo Sereno",
                "Llama del Patio Quieto",
                "Vicuna del Canto Claro",
                "Puma del Resguardo Dorado",
                "Colibri de la Guardia Baja",
            ],
            "subject": [
                "Custodio del Patio de Piedra",
                "Sanadora de los Tres Pulsos",
                "Cantor del Kay Vivo",
                "Veladora del Umbral Manso",
                "Portador de la Campana Clara",
            ],
            "object": [
                "Sello del Rio Paciente",
                "Manto de la Columna Viva",
                "Bastion de Sal Ritual",
                "Rosario del Aire Terso",
                "Brazal de la Huella Serena",
            ],
            "place": [
                "Atrio del Segundo Respiro",
                "Camino de la Piedra Tibia",
                "Huerto del Eco Quieto",
                "Plaza del Juramento Calmo",
                "Santuario del Vaso Lento",
            ],
        },
        "expansion_names": {
            "creature": [
                "Venado del Manto Boreal",
                "Oso del Alba Blanca",
                "Serpiente del Hielo Manso",
                "Zorzal del Faro Niveo",
                "Alpaca del Circulo Polar",
            ],
            "subject": [
                "Priora del Santuario Blanco",
                "Centinela de la Aurora Quieta",
                "Tejedora del Nudo Frio",
                "Guarda del Velo Niveo",
                "Oficiante de la Runa Serena",
            ],
            "object": [
                "Campana de la Escarcha Pura",
                "Escudo del Ancla Boreal",
                "Maza del Hielo Paciente",
                "Anillo de Nieve Ritual",
                "Lazo del Santuario Polar",
            ],
            "place": [
                "Claustro de la Estrella Blanca",
                "Puerta del Humo Frio",
                "Refugio de la Aurora Tersa",
                "Jardin de las Nieves Lentas",
                "Muralla del Silencio Boreal",
            ],
        },
        "lore": {
            "base": {
                "creature": "Las criaturas guardianas sostienen el turno para que la run respire.",
                "subject": "Los sujetos del Kay convierten defensa en tempo y contraataque.",
                "object": "Los objetos guardianes son sellos, mantos y herramientas de permanencia.",
                "place": "Los lugares guardianes ofrecen valor estable y ventanas de recuperacion.",
            },
            "expansion": {
                "creature": "El Santuario Blanco enseña a bloquear sin caer en pasividad.",
                "subject": "Las voces boreales premian armonia lista, defensa activa y castigo medido.",
                "object": "Las reliquias blancas habilitan sellos con pago real y payoff defensivo.",
                "place": "Los espacios polares fuerzan rutas de run mas seguras pero no lentas.",
            },
        },
        "strategy": {
            "defense": ("Absorber el turno enemigo y devolver valor inmediato.", "Sufre si solo bloquea y nunca convierte."),
            "control": ("Preparar armonia, lectura y bloqueos con timing.", "Pierde ritmo ante manos sin payoff."),
            "ritual": ("Consumir armonia cuando el sello ya cambia la carrera.", "Castiga gastar armonia demasiado pronto."),
        },
    },
    "oracle_of_fate": {
        "label": "Oracle of Fate",
        "base_set": "Camino del Ukhu",
        "expansion_set": "Horizonte Boreal",
        "palette": "indigo-cyan",
        "energy": "spiral_streams",
        "symbol": "astral_eye",
        "motif": "cosmic_geometry",
        "order": "Chakana",
        "author": "Chakana Studio",
        "directions": {"creature": "NORTE", "subject": "OESTE", "object": "SUR", "place": "ESTE"},
        "base_names": {
            "creature": [
                "Lechuza del Pozo Claro",
                "Zorro del Eclipse Quieto",
                "Taruca del Eco Lunar",
                "Serpiente del Sueno Doble",
                "Mariposa del Umbral Violeta",
            ],
            "subject": [
                "Vidente del Cuenco Negro",
                "Cronista del Pulso Naciente",
                "Cartografa del Eco Profundo",
                "Adivino de la Tercera Puerta",
                "Custodia del Hilo Interno",
            ],
            "object": [
                "Astrolabio del Velo Bajo",
                "Tabla de las Tres Sombras",
                "Espejo del Condor Inverso",
                "Lampara de Ceniza Azul",
                "Cuenco del Calculo Ritual",
            ],
            "place": [
                "Observatorio del Pozo Inmoto",
                "Cupula del Eco Tardio",
                "Biblioteca del Umbral Vivo",
                "Patio de la Noche Geometrica",
                "Puente del Destino Quieto",
            ],
        },
        "expansion_names": {
            "creature": [
                "Cuervo del Hielo Interior",
                "Liebre del Horizonte Niveo",
                "Lechuza de la Aurora Sumergida",
                "Pez del Lago Astral",
                "Lobo del Velo Boreal",
            ],
            "subject": [
                "Oraculo de la Cupula Helada",
                "Cronista de Nimrod",
                "Interprete del Norte Interior",
                "Tejedor del Segundo Horizonte",
                "Portadora del Mapa Blanco",
            ],
            "object": [
                "Astrolabio de la Estrella Polar",
                "Baston del Eco Frio",
                "Reloj de Escarcha Ritual",
                "Carta del Trono Boreal",
                "Ojo de la Cupula Blanca",
            ],
            "place": [
                "Galeria del Horizonte Boreal",
                "Sala de la Nieve Pensante",
                "Terraza del Astro Invertido",
                "Pozo de la Memoria Blanca",
                "Mirador del Tiempo Frio",
            ],
        },
        "lore": {
            "base": {
                "creature": "Las criaturas del Ukhu abren informacion antes que daño bruto.",
                "subject": "Los sujetos del oraculo convierten lectura en control tangible.",
                "object": "Los objetos del destino ajustan robo, prever y energia futura.",
                "place": "Los lugares del set oracular recompensan secuencias distintas en cada run.",
            },
            "expansion": {
                "creature": "El norte interior vuelve la lectura mas afilada y menos ornamental.",
                "subject": "Los videntes boreales empujan rituales que ya cierran partidas.",
                "object": "Los instrumentos polares mezclan prever, energia y sellos con payoff real.",
                "place": "Los escenarios de Hiperborea hacen que cada ruta de control juegue diferente.",
            },
        },
        "strategy": {
            "control": ("Manipular robo y ventanas antes de gastar recursos.", "Pierde impacto si no encuentra payoff."),
            "combo": ("Encadenar previsiones para habilitar turnos imposibles.", "Necesita secuencias limpias y buena lectura."),
            "energy": ("Aplazar energia y tempo al turno correcto.", "Es flojo si se juega solo por curva."),
            "ritual": ("Convertir armonia en daño/control una vez leida la mesa.", "La run castiga rituales vacios."),
        },
    },
    "archon_war": {
        "label": "Arconte",
        "base_set": "Liturgia Rota",
        "expansion_set": "Liturgia Rota",
        "palette": "void-red",
        "energy": "entropy_smoke",
        "symbol": "void_eye",
        "motif": "fractured_void",
        "order": "Arconte",
        "author": "Chakana Studio",
        "directions": {"creature": "NORTE", "subject": "ESTE", "object": "OESTE", "place": "SUR"},
        "base_names": {
            "creature": [
                "Sabueso de la Grieta Roja",
                "Larva del Credo Marchito",
                "Cuervo del Ojo Impuro",
                "Mantis del Vacio Liturgico",
                "Rata del Eco Profano",
                "Acaro de la Ceniza Ciega",
                "Anguila del Umbral Podrido",
                "Buitre del Sello Torcido",
                "Lobo de la Corona Hueca",
                "Avispa del Trono Negro",
            ],
            "subject": [
                "Prelado del Pulso Roto",
                "Vigia de la Cupula Negra",
                "Portador del Mandato Gris",
                "Acusadora de la Grieta",
                "Notario del Vacio Alto",
                "Custodio del Diente Rojo",
                "Verdugo del Eco Marchito",
                "Acolito del Trono Vacio",
                "Cantor del Mandato Frio",
                "Heraldo de la Liturgia Inversa",
            ],
            "object": [
                "Grillete del Credo Quebrado",
                "Monolito del Humo Rojo",
                "Anillo del Ojo Roto",
                "Aguja del Umbral Negro",
                "Caliz de la Sombra Hueca",
                "Mascara de la Noche Ritual",
                "Incensario del Vacio Ciego",
                "Corona del Silencio Impuro",
                "Lanza del Trono Marchito",
                "Tableta del Mandato Caido",
            ],
            "place": [
                "Foso de la Trama Rota",
                "Trono del Velo Marchito",
                "Galeria de los Sellos Muertos",
                "Pozo del Juramento Rojo",
                "Pasarela del Ojo Negro",
                "Basilica de la Voluntad Quebrada",
                "Camara del Eco Inverso",
                "Patio del Humo Torcido",
                "Puerta de la Noche Fisurada",
                "Santuario del Credo Podrido",
            ],
        },
        "lore": {
            "base": {
                "creature": "Las criaturas arcontes son hambre con forma ritual.",
                "subject": "Los sujetos arcontes rompen ritmo, mano y confianza del rival.",
                "object": "Los objetos arcontes convierten corrupcion en presion inmediata.",
                "place": "Los lugares arcontes deforman la mesa y fuerzan errores.",
            }
        },
    },
}


CW_TEMPLATES = {
    "attack": [
        ([{"type": "damage", "amount": 6}], ["attack"]),
        ([{"type": "damage", "amount": 4}, {"type": "apply_break", "amount": 1}], ["attack", "rupture"]),
        ([{"type": "damage", "amount": 5}, {"type": "gain_block", "amount": 2}], ["attack", "block"]),
        ([{"type": "damage", "amount": 4}, {"type": "draw_on_kill", "amount": 1}], ["attack", "draw"]),
        ([{"type": "damage", "amount": 4}, {"type": "discount_next_attack", "amount": 1}], ["attack", "tempo"]),
        ([{"type": "damage", "amount": 7}], ["attack"]),
    ],
    "combo": [
        ([{"type": "copy_last_played", "amount": 1}, {"type": "exhaust_self", "amount": 1}], ["combo", "copy", "exhaust"]),
        ([{"type": "damage", "amount": 3}, {"type": "damage_if_enemy_break", "amount": 4}], ["attack", "combo", "rupture"]),
        ([{"type": "damage_plus_rupture", "amount": 6, "base": 4, "per_rupture": 2}], ["attack", "combo", "rupture"]),
        ([{"type": "damage", "amount": 4}, {"type": "draw_if_enemy_break", "amount": 1}], ["attack", "combo", "draw"]),
        ([{"type": "retain", "amount": 1}, {"type": "damage", "amount": 5}], ["attack", "combo", "retain"]),
    ],
    "energy": [
        ([{"type": "gain_mana_next_turn", "amount": 1}, {"type": "damage", "amount": 4}], ["energy", "attack"]),
        ([{"type": "gain_mana", "amount": 1}, {"type": "damage", "amount": 3}, {"type": "apply_break", "amount": 1}], ["energy", "attack", "rupture"]),
        ([{"type": "gain_mana_if_enemy_attack_intent", "amount": 1}, {"type": "damage", "amount": 5}], ["energy", "attack", "tempo"]),
    ],
}

HG_TEMPLATES = {
    "defense": [
        ([{"type": "gain_block", "amount": 6}, {"type": "harmony_delta", "amount": 1}], ["block", "harmony"]),
        ([{"type": "gain_block", "amount": 5}, {"type": "heal", "amount": 2}], ["block", "heal"]),
        ([{"type": "gain_block", "amount": 4}, {"type": "weaken_enemy", "amount": 1}], ["block", "debuff"]),
        ([{"type": "gain_block", "amount": 4}, {"type": "damage", "amount": 2}], ["block", "attack"]),
        ([{"type": "gain_block_if_no_direction", "amount": 6}, {"type": "harmony_delta", "amount": 1}], ["block", "harmony", "tempo"]),
    ],
    "control": [
        ([{"type": "gain_block", "amount": 4}, {"type": "scry", "amount": 2}], ["block", "scry"]),
        ([{"type": "gain_block", "amount": 5}, {"type": "draw", "amount": 1}], ["block", "draw"]),
        ([{"type": "gain_block", "amount": 3}, {"type": "apply_break", "amount": 1}, {"type": "harmony_delta", "amount": 1}], ["block", "rupture", "harmony"]),
    ],
    "ritual": [
        ([{"type": "gain_block", "amount": 7}, {"type": "consume_harmony", "amount": 2}, {"type": "heal", "amount": 3}], ["block", "seal", "heal", "ritual"]),
        ([{"type": "gain_block", "amount": 6}, {"type": "consume_harmony", "amount": 1}, {"type": "damage", "amount": 4}], ["block", "seal", "attack", "ritual"]),
        ([{"type": "gain_block", "amount": 5}, {"type": "consume_harmony", "amount": 2}, {"type": "weaken_enemy", "amount": 2}], ["block", "seal", "debuff", "ritual"]),
    ],
}

OF_TEMPLATES = {
    "control": [
        ([{"type": "scry", "amount": 2}, {"type": "draw", "amount": 1}], ["scry", "draw", "control"]),
        ([{"type": "scry", "amount": 3}, {"type": "damage", "amount": 2}], ["scry", "attack", "control"]),
        ([{"type": "scry", "amount": 2}, {"type": "gain_mana_next_turn", "amount": 1}], ["scry", "energy", "control"]),
        ([{"type": "scry", "amount": 1}, {"type": "draw", "amount": 1}, {"type": "apply_break", "amount": 1}], ["scry", "draw", "rupture", "control"]),
    ],
    "combo": [
        ([{"type": "copy_next_played", "amount": 1}, {"type": "scry", "amount": 1}], ["combo", "copy", "scry"]),
        ([{"type": "scry", "amount": 2}, {"type": "draw_if_direction_played", "amount": 1, "direction": "NORTE"}], ["combo", "scry", "draw"]),
        ([{"type": "retain", "amount": 1}, {"type": "draw", "amount": 1}, {"type": "damage", "amount": 2}], ["combo", "retain", "draw", "attack"]),
    ],
    "energy": [
        ([{"type": "gain_mana_next_turn", "amount": 1}, {"type": "scry", "amount": 2}], ["energy", "scry"]),
        ([{"type": "gain_mana", "amount": 1}, {"type": "draw", "amount": 1}], ["energy", "draw"]),
        ([{"type": "gain_mana_next_turn", "amount": 1}, {"type": "damage", "amount": 2}, {"type": "scry", "amount": 1}], ["energy", "attack", "scry"]),
    ],
    "ritual": [
        ([{"type": "harmony_delta", "amount": 1}, {"type": "consume_harmony", "amount": 1}, {"type": "ritual_trama", "amount": 1}], ["ritual", "harmony", "seal"]),
        ([{"type": "harmony_delta", "amount": 2}, {"type": "consume_harmony", "amount": 2}, {"type": "draw", "amount": 1}], ["ritual", "harmony", "seal", "draw"]),
        ([{"type": "harmony_delta", "amount": 1}, {"type": "ritual_trama", "amount": 1}, {"type": "scry", "amount": 2}], ["ritual", "harmony", "scry"]),
    ],
}

ARCHON_TEMPLATES = {
    "attack": [
        ([{"type": "damage", "amount": 5}, {"type": "apply_break", "amount": 1}], ["attack", "rupture", "void"]),
        ([{"type": "damage", "amount": 4}, {"type": "vulnerable_enemy", "amount": 1}], ["attack", "debuff", "void"]),
        ([{"type": "damage", "amount": 4}, {"type": "draw_on_kill", "amount": 1}], ["attack", "draw", "void"]),
    ],
    "control": [
        ([{"type": "damage", "amount": 3}, {"type": "draw", "amount": 1}], ["control", "draw", "void"]),
        ([{"type": "apply_break", "amount": 1}, {"type": "gain_block", "amount": 4}], ["control", "block", "rupture"]),
        ([{"type": "vulnerable_enemy", "amount": 1}, {"type": "draw", "amount": 1}], ["control", "draw", "debuff"]),
    ],
    "ritual": [
        ([{"type": "damage", "amount": 4}, {"type": "apply_break", "amount": 2}, {"type": "draw", "amount": 1}], ["ritual", "attack", "rupture"]),
        ([{"type": "damage", "amount": 5}, {"type": "self_break", "amount": 1}], ["ritual", "attack", "void"]),
        ([{"type": "damage", "amount": 3}, {"type": "gain_mana", "amount": 1}, {"type": "apply_break", "amount": 1}], ["ritual", "energy", "rupture"]),
    ],
    "defense": [
        ([{"type": "gain_block", "amount": 5}, {"type": "weaken_enemy", "amount": 1}], ["block", "control", "void"]),
        ([{"type": "gain_block", "amount": 4}, {"type": "damage", "amount": 2}], ["block", "attack", "void"]),
        ([{"type": "gain_block", "amount": 4}, {"type": "apply_break", "amount": 1}], ["block", "rupture", "void"]),
    ],
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def effect_value(effect: dict) -> int:
    if effect.get("type") == "damage_plus_rupture":
        return int(effect.get("amount", effect.get("base", 0)) or 0)
    return int(effect.get("amount", 0) or 0)


def build_effect_text(effects: list[dict]) -> str:
    parts: list[str] = []
    for effect in effects:
        kind = str(effect.get("type", ""))
        amount = effect_value(effect)
        if kind == "damage":
            parts.append(f"Daño {amount}")
        elif kind in {"gain_block", "block"}:
            parts.append(f"Bloqueo {amount}")
        elif kind == "draw":
            parts.append(f"Roba {amount}")
        elif kind == "gain_mana":
            parts.append(f"Energía +{amount}")
        elif kind == "gain_mana_next_turn":
            parts.append(f"Energía sig. turno +{amount}")
        elif kind == "gain_mana_if_enemy_attack_intent":
            parts.append(f"Energía +{amount} si el enemigo ataca")
        elif kind == "apply_break":
            parts.append(f"Ruptura +{amount}")
        elif kind == "scry":
            parts.append(f"Prever {amount}")
        elif kind == "heal":
            parts.append(f"Cura {amount}")
        elif kind == "weaken_enemy":
            parts.append(f"Debilita {amount}")
        elif kind == "vulnerable_enemy":
            parts.append(f"Vulnerable {amount}")
        elif kind == "copy_last_played":
            parts.append("Copia la última carta")
        elif kind == "copy_next_played":
            parts.append("Duplica la siguiente carta")
        elif kind == "exhaust_self":
            parts.append("Se agota")
        elif kind == "damage_plus_rupture":
            parts.append(f"Daño {int(effect.get('base', 0))} +{int(effect.get('per_rupture', 0))} por Ruptura")
        elif kind == "draw_if_enemy_break":
            parts.append(f"Roba {amount} si hay Ruptura")
        elif kind == "damage_if_enemy_break":
            parts.append(f"Daño {amount} si hay Ruptura")
        elif kind == "draw_on_kill":
            parts.append(f"Roba {amount} al matar")
        elif kind == "gain_block_if_no_direction":
            parts.append(f"Bloqueo {amount} si no repetiste dirección")
        elif kind == "discount_next_attack":
            parts.append(f"Próx. ataque cuesta -{amount}")
        elif kind == "retain":
            parts.append("Retener")
        elif kind == "harmony_delta":
            parts.append(f"Armonía +{amount}")
        elif kind == "consume_harmony":
            parts.append(f"Consume Armonía {amount}")
        elif kind == "ritual_trama":
            parts.append("Ritual de la Trama")
        elif kind == "self_break":
            parts.append(f"Ruptura propia +{amount}")
    return ", ".join(parts[:4])


def build_kpi(effects: list[dict]) -> dict[str, int]:
    out = defaultdict(int)
    mapping = {
        "damage": "damage",
        "damage_plus_rupture": "damage",
        "gain_block": "block",
        "block": "block",
        "draw": "draw",
        "scry": "scry",
        "gain_mana": "energy",
        "gain_mana_next_turn": "energy",
        "gain_mana_if_enemy_attack_intent": "energy",
        "apply_break": "rupture",
        "heal": "support",
        "weaken_enemy": "support",
        "vulnerable_enemy": "support",
        "harmony_delta": "harmony",
        "consume_harmony": "seal",
        "ritual_trama": "ritual",
    }
    for effect in effects:
        key = mapping.get(str(effect.get("type", "")))
        if not key:
            continue
        out[key] += effect_value(effect) if effect_value(effect) > 0 else 1
    return dict(out)


def taxonomy_for(role: str, rarity: str) -> str:
    if rarity == "legendary":
        return "payoff"
    if role in {"ritual", "combo"}:
        return "bridge"
    if role in {"attack", "defense", "control", "energy"} and rarity == "uncommon":
        return "bridge"
    return "engine"


def pick_template(archetype: str, role: str, slot: int) -> tuple[list[dict], list[str]]:
    templates = {
        "cosmic_warrior": CW_TEMPLATES,
        "harmony_guardian": HG_TEMPLATES,
        "oracle_of_fate": OF_TEMPLATES,
        "archon_war": ARCHON_TEMPLATES,
    }[archetype][role]
    effects, tags = templates[slot % len(templates)]
    return [dict(item) for item in effects], list(tags)


def legendary_override(archetype: str, card_id: str) -> tuple[list[dict], list[str]] | None:
    lookup = {
        "BASE-SOLAR-SKILL-CHAKANA_DE_LUZ": (
            [
                {"type": "harmony_delta", "amount": 1},
                {"type": "damage", "amount": 10},
                {"type": "gain_block", "amount": 5},
                {"type": "gain_mana_next_turn", "amount": 1},
                {"type": "exhaust_self", "amount": 1},
            ],
            ["attack", "block", "energy", "combo", "ritual"],
        ),
        "BASE-GUIDE-GUARD-FUSION_ESPIRITUAL": (
            [
                {"type": "gain_block", "amount": 10},
                {"type": "heal", "amount": 4},
                {"type": "harmony_delta", "amount": 2},
                {"type": "consume_harmony", "amount": 2},
                {"type": "damage", "amount": 6},
            ],
            ["block", "heal", "seal", "harmony", "attack", "ritual"],
        ),
        "BASE-ORACLE-RITUAL-RITUAL_DE_LA_TRAMA": (
            [
                {"type": "harmony_delta", "amount": 2},
                {"type": "consume_harmony", "amount": 2},
                {"type": "ritual_trama", "amount": 1},
                {"type": "scry", "amount": 3},
            ],
            ["ritual", "harmony", "seal", "scry"],
        ),
        "BASE-ORACLE-RITUAL-PIEDRA_RITUAL": (
            [
                {"type": "harmony_delta", "amount": 1},
                {"type": "consume_harmony", "amount": 1},
                {"type": "draw", "amount": 1},
                {"type": "scry", "amount": 2},
            ],
            ["ritual", "harmony", "seal", "draw", "scry"],
        ),
        "HYP-SOLAR-SKILL-GUERRERO_ASTRAL_DE_HIPERBOREA_XX": (
            [
                {"type": "gain_mana", "amount": 1},
                {"type": "damage_plus_rupture", "amount": 8, "base": 6, "per_rupture": 2},
                {"type": "draw_if_enemy_break", "amount": 1},
            ],
            ["attack", "combo", "energy", "rupture", "hiperboria"],
        ),
        "HYP-GUIDE-RITUAL-GUARDIAN_DEL_VELO_POLAR_XX": (
            [
                {"type": "gain_block", "amount": 11},
                {"type": "consume_harmony", "amount": 2},
                {"type": "heal", "amount": 5},
                {"type": "weaken_enemy", "amount": 2},
            ],
            ["block", "seal", "heal", "debuff", "ritual", "hiperboria"],
        ),
        "HYP-ORACLE-RITUAL-ORACULO_DEL_HORIZONTE_BOREAL_XX": (
            [
                {"type": "harmony_delta", "amount": 2},
                {"type": "consume_harmony", "amount": 2},
                {"type": "ritual_trama", "amount": 1},
                {"type": "draw", "amount": 2},
            ],
            ["ritual", "seal", "draw", "harmony", "hiperboria"],
        ),
        "BASE-ORACLE-RITUAL-PIEDRA_RITUAL_NOVA": (
            [
                {"type": "harmony_delta", "amount": 1},
                {"type": "ritual_trama", "amount": 1},
                {"type": "draw", "amount": 1},
            ],
            ["ritual", "harmony", "draw"],
        ),
        "ARC-ARCHON-GUARD-ARCANO_DEL_VACIO_40": (
            [
                {"type": "gain_block", "amount": 8},
                {"type": "damage", "amount": 6},
                {"type": "apply_break", "amount": 2},
            ],
            ["block", "attack", "rupture", "void"],
        ),
    }
    return lookup.get(card_id)


def names_for(archetype: str, segment: str) -> list[tuple[str, str]]:
    meta = ARCHETYPE_META[archetype]
    source = meta["base_names"] if segment == "base" else meta["expansion_names"]
    ordered = []
    for category in ("creature", "subject", "object", "place"):
        for name in source[category]:
            ordered.append((name, category))
    return ordered


def archon_names() -> list[tuple[str, str]]:
    meta = ARCHETYPE_META["archon_war"]["base_names"]
    out = []
    for category in ("creature", "subject", "object", "place"):
        for name in meta[category]:
            out.append((name, category))
    return out


def build_card(row: dict, archetype: str, name: str, category: str, segment: str, slot: int) -> dict:
    meta = ARCHETYPE_META[archetype]
    rarity = str(row.get("rarity", "common")).lower().replace("rare", "uncommon")
    role = str(row.get("role", "attack")).lower()
    card_id = str(row["id"])
    override = legendary_override(archetype, card_id)
    if override is None:
        effects, extra_tags = pick_template(archetype, role, slot)
    else:
        effects, extra_tags = override

    taxonomy = taxonomy_for(role, rarity)
    set_key = "base" if segment == "base" else "hiperboria"
    lore_bucket = "base" if segment == "base" else "expansion"
    lore_text = f"{name}: {meta['lore'][lore_bucket][category]}"
    best_use, weakness = meta.get("strategy", {}).get(role, ("Generar una ventana util.", "Cae si no aparece soporte."))
    effect_text = build_effect_text(effects)
    tags = sorted({category, role, *extra_tags})
    if "consume_harmony" in {str(effect.get("type", "")) for effect in effects}:
        tags = sorted(set(tags) | {"seal"})
    strategy = {
        "best_use": best_use,
        "synergy_cards": [],
        "weakness": weakness,
    }
    return {
        "archetype": archetype,
        "artwork": row.get("artwork", card_id),
        "author": meta["author"],
        "cost": int(row.get("cost", 1) or 1),
        "direction": meta["directions"][category],
        "effect_text": effect_text,
        "effects": effects,
        "family": category,
        "id": card_id,
        "kpi": build_kpi(effects),
        "lore_text": lore_text,
        "name": name,
        "name_es": name,
        "name_key": name,
        "rarity": rarity,
        "role": role,
        "strategy": strategy,
        "tags": tags,
        "target": row.get("target", "enemy"),
        "taxonomy": taxonomy,
        "text_es": effect_text,
        "text_key": effect_text,
        "legacy_id": row.get("legacy_id", card_id),
        "canonical_id": row.get("canonical_id", card_id),
        "legacy_artwork": row.get("legacy_artwork", row.get("artwork", card_id)),
        "motif": meta["motif"],
        "palette": meta["palette"],
        "energy": meta["energy"],
        "symbol": meta["symbol"],
        "order": meta["order"],
        "set": set_key,
    }


def build_codex_payload(set_id: str, set_name: str, cards: list[dict], counts: dict[str, int]) -> dict:
    return {
        "set_id": set_id,
        "set_name": set_name,
        "total_cards": len(cards),
        "archetypes": [
            {"id": arch, "name": ARCHETYPE_META[arch]["label"], "count": counts[arch]}
            for arch in counts
        ],
        "cards": [
            {
                "id": card["id"],
                "name": card["name"],
                "archetype": card["archetype"],
                "role": card["role"],
                "rarity": card["rarity"],
                "gameplay_text": card["effect_text"],
                "lore_text": card["lore_text"],
                "tags": card["tags"],
                "set": card["set"],
                "legacy_id": card["legacy_id"],
                "canonical_id": card["canonical_id"],
            }
            for card in cards
        ],
    }


def write_design_doc(base_cards: list[dict], expansion_cards: list[dict], archon_cards: list[dict]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    counts = Counter(card["archetype"] for card in base_cards + expansion_cards)
    categories = defaultdict(Counter)
    for card in base_cards + expansion_cards + archon_cards:
        for token in ("creature", "subject", "object", "place"):
            if token in card["tags"]:
                categories[card["archetype"]][token] += 1
                break

    text = f"""# Ticket: Rebuild de sets de cartas

## Alcance
- Reorganizar el pool jugable en 40 cartas por arquetipo de jugador.
- Mantener IDs, arte y compatibilidad con runtime.
- Rehacer nombres, lore, taxonomía y textos de efecto.
- Curar el set enemigo Arconte a 40 cartas con identidad propia.
- Ajustar la tabla de combate para que las runs roten antes y muestren identidad real.

## Decisión de estructura
- `cards.json` conserva 20 cartas base por arquetipo.
- `cards_hiperboria.json` pasa a ser la segunda mitad de cada set de 40.
- Resultado efectivo: `Cosmic Warrior`, `Harmony Guardian` y `Oracle of Fate` quedan en {counts['cosmic_warrior']}/{counts['harmony_guardian']}/{counts['oracle_of_fate']} cartas.
- `cards_arconte.json` queda en 40 cartas curadas para el set enemigo.

## Composición por set
- Cosmic Warrior: criaturas {categories['cosmic_warrior']['creature']}, sujetos {categories['cosmic_warrior']['subject']}, objetos {categories['cosmic_warrior']['object']}, lugares {categories['cosmic_warrior']['place']}.
- Harmony Guardian: criaturas {categories['harmony_guardian']['creature']}, sujetos {categories['harmony_guardian']['subject']}, objetos {categories['harmony_guardian']['object']}, lugares {categories['harmony_guardian']['place']}.
- Oracle of Fate: criaturas {categories['oracle_of_fate']['creature']}, sujetos {categories['oracle_of_fate']['subject']}, objetos {categories['oracle_of_fate']['object']}, lugares {categories['oracle_of_fate']['place']}.
- Arconte: criaturas {categories['archon_war']['creature']}, sujetos {categories['archon_war']['subject']}, objetos {categories['archon_war']['object']}, lugares {categories['archon_war']['place']}.

## Auditoría de reglas, efectos y condiciones
- Efectos priorizados: `damage`, `gain_block`, `apply_break`, `draw`, `scry`, `gain_mana`, `gain_mana_next_turn`, `harmony_delta`, `consume_harmony`, `ritual_trama`.
- Efectos condicionales activos para variedad y lectura de mesa: `draw_if_enemy_break`, `damage_if_enemy_break`, `draw_on_kill`, `gain_block_if_no_direction`, `gain_mana_if_enemy_attack_intent`.
- Efectos evitados para este rebuild: nuevos sistemas no soportados por runtime y estados ambiguos no legibles.
- Resultado de diseño:
  - Cosmic Warrior gana burst, ruptura y aceleración puntual.
  - Harmony Guardian deja de ser puro muro y convierte defensa en daño, sello o tempo.
  - Oracle of Fate gana payoff real en robo/prever/ritual para dejar de sentirse fallido.
  - Arconte abandona la serialización vacía y pasa a presionar con corrupción y fractura.

## KPIs de diseño
- Meta de identidad:
  - Cosmic Warrior: daño alto, ruptura estable, cierres antes del segundo reshuffle.
  - Harmony Guardian: bloqueo alto con conversión real a valor en el mismo turno.
  - Oracle of Fate: ventaja de mano y selección superiores al resto, con cierre ritual real.
- Meta de legibilidad:
  - Sin nombres serializados.
  - Cada carta pertenece a criatura, sujeto, objeto o lugar.
  - Texto visible limitado a 4 fragmentos para no romper UI.

## Ajuste de tabla de juego
- `player_combat_deck_size` recomendado: 24.
- Motivo: reducir padding sobre mazos iniciales de 20 cartas y permitir que la identidad del mazo aparezca antes.

## Definition of Done
- Cartas regeneradas en fuentes canónicas y códex.
- Arconte reducido a 40 entradas con nombre/lore propios.
- Documentación de propuesta y balance actualizada.
- Validaciones locales ejecutadas con smokes documentados.
"""
    (DOCS / "card_set_rebuild_20260312.md").write_text(text, encoding="utf-8")


def main() -> None:
    base_rows = load_json(DATA / "cards.json")
    expansion_payload = load_json(DATA / "cards_hiperboria.json")
    archon_payload = load_json(DATA / "cards_arconte.json")

    base_cards: list[dict] = []
    base_counts: dict[str, int] = {}
    for archetype in ("cosmic_warrior", "harmony_guardian", "oracle_of_fate"):
        rows = [row for row in base_rows if str(row.get("archetype", "")) == archetype]
        names = names_for(archetype, "base")
        out = []
        for idx, row in enumerate(rows):
            name, category = names[idx]
            out.append(build_card(row, archetype, name, category, "base", idx))
        base_cards.extend(out)
        base_counts[archetype] = len(out)

    expansion_rows = list(expansion_payload.get("cards", []))
    expansion_cards: list[dict] = []
    expansion_counts: dict[str, int] = {}
    for archetype in ("cosmic_warrior", "harmony_guardian", "oracle_of_fate"):
        rows = [row for row in expansion_rows if str(row.get("archetype", "")) == archetype]
        names = names_for(archetype, "expansion")
        out = []
        for idx, row in enumerate(rows):
            name, category = names[idx]
            out.append(build_card(row, archetype, name, category, "expansion", idx + 20))
        expansion_cards.extend(out)
        expansion_counts[archetype] = len(out)

    archon_rows = list(archon_payload.get("cards", []))[:40]
    archon_names_list = archon_names()
    archon_cards = []
    for idx, row in enumerate(archon_rows):
        name, category = archon_names_list[idx]
        card = build_card(row, "archon_war", name, category, "base", idx)
        if idx == 39:
            card["rarity"] = "legendary"
            card["taxonomy"] = "payoff"
        elif idx >= 24:
            card["rarity"] = "uncommon"
            card["taxonomy"] = "bridge"
        else:
            card["rarity"] = "common"
            card["taxonomy"] = "engine"
        card["set"] = "arconte"
        card["order"] = "Arconte"
        archon_cards.append(card)

    save_json(DATA / "cards.json", base_cards)
    save_json(
        DATA / "cards_hiperboria.json",
        {
            "set_id": "hiperboria",
            "set_name": "HIPERBOREA",
            "total_cards": len(expansion_cards),
            "archetypes": [
                {"id": arch, "name": ARCHETYPE_META[arch]["label"], "count": expansion_counts[arch]}
                for arch in ("cosmic_warrior", "harmony_guardian", "oracle_of_fate")
            ],
            "cards": expansion_cards,
        },
    )
    save_json(DATA / "cards_arconte.json", {"set": "arconte", "cards": archon_cards})

    save_json(DATA / "codex_cards_lore_set1.json", build_codex_payload("lore_set_1", "Lore Set 1", base_cards, base_counts))
    save_json(DATA / "codex_cards_hiperboria.json", build_codex_payload("hiperboria", "HIPERBOREA", expansion_cards, expansion_counts))
    save_json(
        DATA / "codex_cards_arconte.json",
        {
            "set_id": "arconte",
            "set_name": "Arconte",
            "total_cards": len(archon_cards),
            "cards": [
                {
                    "id": card["id"],
                    "name": card["name"],
                    "set": "arconte",
                    "archetype": card["archetype"],
                    "rarity": card["rarity"],
                    "role": card["role"],
                    "gameplay_text": card["effect_text"],
                    "lore_text": card["lore_text"],
                    "tags": card["tags"],
                    "legacy_id": card["legacy_id"],
                    "canonical_id": card["canonical_id"],
                }
                for card in archon_cards
            ],
        },
    )

    write_design_doc(base_cards, expansion_cards, archon_cards)

    print(f"base_cards={len(base_cards)}")
    print(f"expansion_cards={len(expansion_cards)}")
    print(f"archon_cards={len(archon_cards)}")


if __name__ == "__main__":
    main()
