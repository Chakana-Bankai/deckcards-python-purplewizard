# CHAKANA Gameplay System 1.0

Estado: Integrado (Fase 1-2 segura)

## Objetivo
Estabilizar el loop de run sin romper QA existente, separando reglas engine-candidate de contenido game-specific.

## Reglas base (v1.0)
- HP inicial jugador: 60
- Energia por turno: 3
- Mazo de combate objetivo: 30 cartas (normalizado desde mazo de run)
- Mano inicial: 5
- Robo por turno: 5
- Limite de mano: 10
- Si roba con mano llena: carta va a descarte (sin soft-lock)

## Flujo de run (actual + preparado)
1. Inicio de run
2. Progresion por nodos
3. Combate / evento / tienda / recompensas
4. Boss del plano
5. Continuacion de plano

## Gate de contenido
- Hiperborea: permanece como unlock dirigido por progresion (Fase 4)
- No se fuerza desbloqueo en Fase 2 para evitar regresion de flujo

## Clasificacion
- engine_candidate: reglas de mano/robo/descarte, normalizacion de mazo
- game_specific: narrativa de planos, textos, eventos de lore

## Fase 4 (integrada)
- Unlock Hiperborea tras 3 combates tutorial (`tutorial_combats_won`).
- Se dispara escena de descubrimiento al desbloquear.
- Recompensas/tienda/sobres consumen pool por set desbloqueado.
- Save/continue sincroniza estado de sets desbloqueados de forma segura.
