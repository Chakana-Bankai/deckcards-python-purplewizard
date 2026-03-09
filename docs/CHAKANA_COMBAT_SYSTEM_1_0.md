# CHAKANA Combat System 1.0

Estado: Consolidado base (Fase 2)

## Loop de combate
- draw_pile -> hand -> discard_pile -> reshuffle
- Cuando draw_pile vacia, mezcla discard_pile en draw_pile
- Integridad de piles auditada con `audit_and_repair_deck_piles`

## Reglas base activas
- `starting_hand = 5`
- `draw_per_turn = 5`
- `hand_limit = 10`
- Overdraw seguro: `draw_overflow_to_discard`

## Compatibilidad
- No se altera logica de efectos de cartas
- No se altera balance de cartas/ids
- No se altera FSM de pantallas

## Preparacion Enemy Deck
- Enemigos pueden definir `intent_deck`
- Si existe, usan mini-ciclo draw/discard/reshuffle de intenciones
- Fallback total al `pattern` actual
