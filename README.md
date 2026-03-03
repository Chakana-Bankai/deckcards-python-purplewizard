# CHAKANA: Mago Morado (MVP)

Deckbuilder por turnos en Python + Pygame con arquitectura separada (motor/UI), contenido data-driven y localización desde día 1.

## Requisitos

- Python 3.10+
- pygame

## Ejecutar

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install pygame
python game/main.py
```

## Controles

- Mouse: click carta, enemigo y botones.
- Teclado:
  - `1..0` jugar carta
  - `E` fin turno
  - `D` ver mazo
  - `R` ver descarte
  - `ESC` cancelar/volver
  - `SPACE` confirmar target por defecto
  - `F1` alternar ES/EN
  - `F11` fullscreen

## Estructura

- `game/core`: estado global, RNG, localización
- `game/combat`: motor de combate determinista + ActionQueue
- `game/ui`: render/input/pantallas
- `game/data`: cartas, enemigos, reliquias, eventos e idiomas JSON
