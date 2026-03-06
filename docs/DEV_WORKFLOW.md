# DEV WORKFLOW — Chakana Purple Wizard (Windows + VS Code)

## Reglas base
- Antes de usar Codex, correr `git status` y confirmar árbol limpio.
- **1 ticket = 1 branch** + 1 commit atómico.
- Usar Codex en modo **Apply changes only**.
- **Nunca** usar Codex para **Create PR** en este flujo local.

## Tareas VS Code
Usar `.vscode/tasks.json`:
- **Run Game** → `.\run.ps1`
- **QA Smoke** → `game\.venv\Scripts\python.exe -m game.qa.runner --smoke`
- **Git Status** → `git status`
- **Find Conflict Markers** → `git grep -n "<<<<<<<\|=======\|>>>>>>>" -- game`

## Flujo recomendado
1. `git status`
2. Ejecutar tarea **QA Smoke**
3. Aplicar cambios mínimos
4. Ejecutar **Run Game** y cerrar
5. Ejecutar **Git Status** y validar limpio (excepto ignorados locales)
6. Commit local

## Si hay conflictos
```bash
git merge --abort
git rebase --abort
```

Si necesitas volver a estado limpio:
```bash
git reset --hard origin/main
git clean -fd
```

## Escaneo de marcadores de conflicto
```bash
git grep -n "<<<<<<<\|=======\|>>>>>>>" -- game
```

## Nota sobre settings y autogen
- `game/data/settings.default.json` es el baseline versionado.
- `game/data/settings.json` es local e ignorado.
- No regenerar manifests/prompts/assets en boot normal; sólo por acción explícita de regeneración.
