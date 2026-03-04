# AGENTS.md — Chakana Purple Wizard

## [1] Propósito y tono
- **Proyecto:** Chakana Purple Wizard.
- **Identidad:** mago morado Chakana (usuario), cosmovisión andina, iniciación y moralejas tácticas.
- **Meta de cada cambio:** mejorar claridad táctica, estabilidad y coherencia estética sin romper el loop base.

## [2] Reglas duras (NO romper)
1. Resolución objetivo **1920x1080** (no bajar base interna).
2. No degradar legibilidad: contraste, tamaño de texto y jerarquía visual.
3. No romper flujos críticos:
   - botón de acción / fin de turno,
   - selección y deselección de cartas,
   - panel de detalle,
   - voces/diálogos,
   - carga de assets.
4. No regenerar arte/música en cada arranque:
   - usar `missing_only`, o
   - regeneración explícita por botón con confirmación + pantalla de carga.
5. No editar a mano outputs autogenerados si existe fuente determinista.

## [3] Fuentes de verdad (biblias) y prioridad
**Leer antes de cambios grandes (mecánicas, UI principal, narrativa o pipelines):**
- Carta Sagrada: `docs/vision/carta_sagrada_diseno.md`
- GDD base producción: `docs/design/game_design_document.md`
- Lore biblia: `docs/vision/lore_biblia_chakana.md`
- GDD histórico/base: `game/data/design/gdd_chakana_purple_wizard.txt`
- Lore y manifiestos:
  - `game/data/lore/chakana_lore.txt`
  - `game/data/lore/world.txt`
  - `game/data/lore/biomes_lore.json`
  - `game/data/lore/map_narration.json`
  - `game/data/lore/dialogues_combat.json`
  - `game/data/lore/dialogues_events.json`
- Contenido JSON (cartas/enemigos/eventos/reliquias):
  - `game/data/cards.json`, `game/data/enemies.json`, `game/data/events.json`, `game/data/relics.json`

**Prioridad de conflicto:**
1) Carta Sagrada de Diseño
2) GDD Base de Producción
3) Lore Master / Manifiestos
4) JSON de contenido

## [4] Flujo de trabajo para tickets (obligatorio)
1. Leer biblias aplicables.
2. Definir DoD del ticket.
3. Plan por archivos (qué se toca y por qué).
4. Implementar cambios mínimos.
5. Ejecutar comandos.
6. QA smoke mínimo.
7. Commit.

**Cada ticket debe cerrar con:**
- comandos ejecutados,
- resultado,
- 3 smoke tests documentados.

## [5] Comandos estándar
### Windows PowerShell
- `./run.ps1`
- `python -m game.main` (en venv, si aplica)

### Validación útil
- `python tools/validate_prompts.py`
- `python -m game.qa.runner`

### Autogeneración (política)
- Priorizar generación por flujo de app/settings.
- Si se usa script/código de regeneración, debe ser explícito, confirmado y trazable en logs.

## [6] QA / Smoke tests mínimos (siempre)
1. Boot hasta **menú → mapa → combate**.
2. Jugar 1 carta, terminar turno, verificar intención enemiga y volver a interactuar.
3. Abrir panel detalle de carta (combate y mazo, si existe).
4. Abrir settings, cambiar volumen, volver sin crash.
5. Probar “Reset Autogen Total” (si existe) evitando `PermissionError`:
   - parar audio,
   - soltar handles,
   - recién luego limpiar/regenerar.

## [7] Estándares de código
- Alta cohesión, bajo acoplamiento.
- Separar responsabilidades: game loop, UI, carga de contenido, asset pipeline, audio.
- Logging con prefijos: `[boot]` `[load]` `[ui]` `[audio]` `[art]`.
- Errores: mensaje claro para usuario + log útil para desarrollo + fallback seguro.

## [8] Política Git / merges (muy importante)
- Minimizar conflictos en JSON.
- Si un artefacto es autogenerado, preferir determinismo o excluirlo del commit según política del ticket.
- Nunca dejar marcadores de conflicto (`<<<<`, `====`, `>>>>`).
- Regeneración debe ser estable: misma entrada → misma salida.
- **Mensaje de commit para este ticket:** `chore: add/update AGENTS guidance`.
