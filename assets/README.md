# Assets de soporte del workspace

Este arbol `assets/` NO es la raiz runtime principal del juego.

## Uso
- `assets/art_reference/`: biblioteca de referencia para direccion artistica y Creative Director.
- `assets/_archive/`: historico archivado, fuera del runtime activo.

## Runtime real
El juego carga activos principalmente desde:
- `game/assets/`
- `game/visual/generated/`
- `game/audio/generated/`

## Regla
No mezclar runtime activo con archivo historico.
