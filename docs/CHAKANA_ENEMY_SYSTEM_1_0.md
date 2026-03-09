# CHAKANA Enemy System 1.0

Estado: Fase 3 integrada (mini-mazos + IA simple segura)

## Tipos
- criatura
- guardian
- arconte

## Modelo de intenciones
- `pattern`: fallback 100% compatible
- `intent_deck`: mini-mazo opcional por enemigo
- ciclo interno:
  - intent_draw_pile
  - intent_discard_pile
  - reshuffle

## IA simple basada en mazo
- Seleccion de intencion por score sobre ventana de robo (lookahead)
- Ajustes por:
  - hp actual
  - block actual
  - perfil de IA (`aggro`, `control`, `bulwark`)
- Jefes priorizan control/ritmo cuando corresponde

## Integracion de contenido
- si un enemigo no trae `intent_deck`, se construye uno base desde `pattern`
- se etiqueta `enemy_type` e `ai_profile` en carga
- sin romper IDs, save/load ni flujo de combate

## Compatibilidad
- fallback automatico a `pattern` cuando no hay mini-mazo
- no se rediseña logica central de combate
