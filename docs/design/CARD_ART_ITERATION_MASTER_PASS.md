# Card Art Iteration Master Pass

## Objetivo
Llevar el generador de cartas desde "escena abstracta con geometria" hacia "escena ilustrada legible" usando iteraciones cortas, medibles y sin romper el runtime.

## Regla principal
No regenerar las 180 cartas a ciegas en cada pasada.

Primero:
1. probar sobre 3 cartas ancla
2. validar visualmente
3. ampliar a 10-15
4. luego subir al pool completo

## Cartas ancla
1. `cw_lore_10`
2. `hip_cosmic_warrior_20`
3. `arc_060`

## Estructura obligatoria por arte
1. Background
2. Scene support
3. Primary silhouette
4. Secondary object
5. Magical effect
6. Final integration
7. Frame

El frame siempre va separado del arte interior.

## Fase 1: Subject Dominance
Meta:
- que el sujeto ocupe 80% del alto util
- que se lea a simple vista a 1x

Tareas:
- simplificar anatomia de sujeto
- hacer cabeza, torso y hombros claramente visibles
- eliminar masas ambiguas
- usar siluetas distintas por familia:
  - warrior
  - guardian
  - oracle
  - archon
  - beast

DoD:
- el sujeto se distingue del fondo en 3 cartas ancla

## Fase 2: Focus Object Dominance
Meta:
- que el objeto se identifique sin adivinar

Tareas:
- aumentar tamano del objeto a 35-45% del ancho util
- separarlo del cuerpo con contraste
- limitar el numero de objetos secundarios
- usar objetos fuertes:
  - espada
  - hacha
  - sello
  - codex
  - altar
  - corona

DoD:
- cada carta ancla tiene 1 objeto claramente reconocible

## Fase 3: Scene Support
Meta:
- que el fondo apoye y no compita

Tareas:
- reducir arquitectura central
- dejar horizonte, ciudadela o trono detras del sujeto
- crear una lectura de 3 planos:
  - fondo lejano
  - medio
  - primer plano

DoD:
- el fondo se entiende pero no tapa sujeto u objeto

## Fase 4: Effect Restraint
Meta:
- que la magia acompane, no destruya lectura

Tareas:
- limitar efectos a menos del 15% del frame
- eliminar grandes elipses, rejillas o espirales dominantes
- permitir solo:
  - glow
  - particulas
  - streaks cortos
  - runas leves

DoD:
- la carta se ve limpia y no ruidosa

## Fase 5: Set Differentiation
Meta:
- que Base, Hiperborea y Arconte no parezcan el mismo arte con otro color

Base:
- santuario Chakana
- Gaia
- dorado, violeta, turquesa
- heroe ritual

Hiperborea:
- ciudadela polar
- observatorio
- marmol, hielo, blanco, azul
- campeon luminoso

Arconte:
- trono maligno
- monolito
- negro, carmesi, verde toxico
- entidad opresiva

DoD:
- las 3 cartas ancla se distinguen por set incluso en miniatura

## Fase 6: Reference Routing
Meta:
- que cada carta use referencias correctas

Tareas:
- primero usar `subject_ref`, `object_ref`, `environment_ref`
- despues referencias secundarias del set
- evitar mezcla absurda entre:
  - condor
  - arconte
  - guardian
  - mago

DoD:
- el reporte de pipeline muestra refs ancla correctas al inicio

## Fase 7: Escalado
Solo cuando Fases 1-6 pasen en las 3 cartas ancla:

1. regenerar 10 cartas
2. revisar shortlist
3. regenerar 30
4. luego el pool completo

## Checklist visual
Cada carta debe responder:
1. Donde ocurre la escena
2. Quien domina la escena
3. Que objeto manda
4. Que energia o accion ocurre

Si falla una, no pasa la iteracion.

## Criterio de rechazo
Rechazar cualquier arte si:
- parece solo un castillo o bloque
- parece solo una mancha
- el sujeto no se distingue
- el objeto no se distingue
- el FX tapa el foco
- la geometria sagrada domina el centro

## Comandos sugeridos
Prueba corta:
`python -m tools.assets.regenerate_premium_card_batch --ids cw_lore_10 hip_cosmic_warrior_20 arc_060`

Prueba pipeline:
`python -m tools.assets.test_layered_scene_pipeline`

QA de estabilidad:
`python -m tools.qa.check_beta_run_flow`
