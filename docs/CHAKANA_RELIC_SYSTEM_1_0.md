# CHAKANA Relic System 1.0

Estado: funcional, consolidacion pendiente de slots (Fase 5)

## Alcance v1
- Pool activa
- Aplicacion de efectos
- Visualizacion en HUD/Map/Codex

## Objetivo de lock
- pool inicial objetivo: 30 reliquias
- tipos: pasivas, reactivas, combate, economia
- max equipadas: 8 (a consolidar en Fase 5)

## Boundary
- engine_candidate: evaluacion de triggers y applicator
- game_specific: lore, nombres, artes

## Fase 5 (integrada)
- Slots maximos de reliquias consolidados en `8` (`relic_slots_max`).
- Alta de reliquias centralizada con validacion de cupo y logs seguros.
- Tienda/recompensas respetan limite de slots sin romper flujo.
- HUD/Mapa muestran conteo actual `x/8` para legibilidad de run.
