# AGENTS.md — Chakana Purple Wizard

## 1) Roles y responsabilidades
- **ChatGPT:** diseño funcional, definición de tickets, criterios de aceptación y validación conceptual.
- **Codex:** implementación técnica acotada al ticket, validaciones locales y preparación del commit.
- **VS Code / runner local:** ejecución, pruebas manuales, smoke tests y cierre de commit.

## 2) Loop estándar de trabajo (obligatorio)
1. Reproducir bug o necesidad.
2. Escribir ticket concreto (alcance + DoD).
3. Aplicar cambios mínimos por archivo.
4. Ejecutar validaciones/smokes.
5. Commit único del ticket.

## 3) Comandos estándar
- **Run:** `./run.ps1`
- **Doctor:** `python -m tools.doctor`
- **Clean autogen:** `python -m tools.clean_autogen --all`
- **Mark only (safe lock mode):** `python -m tools.clean_autogen --mark_only`
- **Regen missing only:** `python -m tools.regen_assets --missing_only`
- **Regen force:** `python -m tools.regen_assets --force`

## 4) Reglas operativas de autogeneración
- No regenerar assets en boot normal, salvo que el usuario habilite explícitamente **force regen**.
- No tocar outputs autogenerados si el ticket no lo pide explícitamente.
- Limpieza y regeneración deben ser explícitas, trazables y deterministas.

## 5) Reglas de Git
- **1 ticket = 1 commit**.
- Si hay conflictos de merge o árbol sucio no relacionado, **detener** y resolver antes de continuar.
- Evitar churn en JSON autogenerados; usar herramientas de clean/regen en lugar de edición manual.

## 6) Guardrails de proyecto (NO romper)
1. Resolución base 1920x1080.
2. No degradar legibilidad ni flujos críticos de combate/UI.
3. No romper carga de assets, voces, selección de cartas o botón de fin de turno.
4. No editar manualmente artefactos deterministas si existe fuente.

## 7) Fuentes de verdad
Prioridad de conflicto:
1) `docs/vision/carta_sagrada_diseno.md`
2) `docs/design/game_design_document.md`
3) lore/manifiestos en `game/data/lore/*`
4) JSON de contenido en `game/data/*.json`

## 8) Cierre mínimo por ticket
- Lista de comandos ejecutados.
- Resultado de cada comando.
- Al menos 3 smoke tests documentados.
