# CHAKANA Meta Engine Design 1.0

Estado: blueprint integrado sin migracion destructiva

## Directores
- Progression Director
- Content Director
- Difficulty Director
- Variety Director

## Reglas de meta
- pools ponderados por etapa
- anti-repeticion de ofertas/eventos
- unlocks por hitos de run
- hooks para direccion de arte/audio procedural

## Integracion gradual
- No migracion total en una sola fase
- Wrappers/import shims para mover modulos a futuro
- Guardrails de compatibilidad con save/load y run flow

## Fase 6 (integrada segura)
- MetaDirector liviano agregado para progresion/contenido/variedad sin tocar combate.
- Anti-repeticion aplicada en seleccion de enemigos y eventos.
- Hooks de direccion visual/audio por biome/contexto en estado de run (meta_director).
- Umbral de unlock de Hiperborea centralizado en director (3 combates tutorial).

