# CHAKANA Enemy System 1.0

Estado: Compatible + soporte deck-intent preparado

## Tipos
- criatura
- guardian
- arconte

## Modelo actual
- `pattern` como comportamiento base

## Extension segura (Fase 2)
- `intent_deck` opcional por enemigo
- mini-ciclo interno de intenciones:
  - intent_draw_pile
  - intent_discard_pile
  - reshuffle al vaciar
- fallback automático a `pattern`

## Objetivo
Escalar dificultad por calidad/sinergia de acciones, no solo HP.
