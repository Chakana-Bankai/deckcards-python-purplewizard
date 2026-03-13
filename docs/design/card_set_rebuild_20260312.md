# Ticket: Rebuild de sets de cartas

## Alcance
- Reorganizar el pool jugable en 40 cartas por arquetipo de jugador.
- Mantener IDs, arte y compatibilidad con runtime.
- Rehacer nombres, lore, taxonomía y textos de efecto.
- Curar el set enemigo Arconte a 40 cartas con identidad propia.
- Ajustar la tabla de combate para que las runs roten antes y muestren identidad real.

## Decisión de estructura
- `cards.json` conserva 20 cartas base por arquetipo.
- `cards_hiperboria.json` pasa a ser la segunda mitad de cada set de 40.
- Resultado efectivo: `Cosmic Warrior`, `Harmony Guardian` y `Oracle of Fate` quedan en 40/40/40 cartas.
- `cards_arconte.json` queda en 40 cartas curadas para el set enemigo.

## Composición por set
- Cosmic Warrior: criaturas 10, sujetos 10, objetos 10, lugares 10.
- Harmony Guardian: criaturas 10, sujetos 10, objetos 10, lugares 10.
- Oracle of Fate: criaturas 10, sujetos 10, objetos 10, lugares 10.
- Arconte: criaturas 10, sujetos 10, objetos 10, lugares 10.

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
