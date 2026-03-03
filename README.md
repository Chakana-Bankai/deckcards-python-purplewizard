# CHAKANA: Mago Morado (MVP)

Deckbuilder por turnos en Python + Pygame con arquitectura separada (motor/UI), contenido data-driven y localización desde día 1.

## Requisitos

- Python 3.12
- Windows PowerShell (recomendado)

## Ejecutar (Windows, comando oficial)

```powershell
py -3.12 -m venv game\.venv
game\.venv\Scripts\python.exe -m pip install -U pip
game\.venv\Scripts\python.exe -m pip install -r requirements.txt
game\.venv\Scripts\python.exe -m game.main
```

También puedes usar:

```powershell
.\run.ps1
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

## Robustez implementada

- Paths absolutos con `pathlib` (independiente del cwd).
- Carga JSON segura con fallback (`safe_io.load_json`).
- Defaults mínimos si faltan data files (cartas base, enemigo dummy, eventos vacíos).
- Manejo de excepciones con traceback completo.
