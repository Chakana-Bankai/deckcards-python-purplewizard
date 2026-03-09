# CHAKANA Card System 1.0

Estado: Base estable + preparado para expansion

## Sets
- BASE: 60
- HIPERBOREA: 60
- ARCONTE: reservado para contenido enemigo (fase posterior)

## Tipos
- ATAQUE
- DEFENSA
- CONTROL
- RITUAL
- INVOCACION
- CURSE

## Reglas de integracion
- No cambiar IDs existentes
- No romper mapeos de iconos ni render canónico
- Mantener codex por set/tab

## Boundary
- engine_candidate: renderer canónico + validadores
- game_specific: nombres, lore, textos, arte asociado

## Fase 4 (integrada)
- Catalogo de runtime extendido para incluir cards_hiperboria.json sin romper Base.
- Definiciones de combate usan catalogo base+hiperborea para evitar IDs huerfanos.
- Codex carga codex_cards_hiperboria.json y habilita pestaña Hiperborea solo tras unlock.
