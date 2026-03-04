# CHAKANA: Mago Morado (MVP)

## Ejecutar (Windows)

```powershell
py -3.12 -m venv game\.venv
game\.venv\Scripts\python.exe -m pip install -U pip
game\.venv\Scripts\python.exe -m pip install -r requirements.txt
game\.venv\Scripts\python.exe -m game.main
```

## Compatibilidad sin binarios versionados

Para evitar errores de plataformas que no aceptan archivos binarios en el repo/parches:

- Los `.png`, `.wav` y `.ttf` dentro de `game/assets/` se generan/copian localmente al iniciar.
- El modo por defecto de arte es `autogen_art_mode = "missing_only"` en `game/data/settings.json`.
- Con ese modo, solo se genera arte si falta o si se detecta placeholder uniforme.

## Arte de cartas y prompts

- Arte procedural: `game/assets/sprites/cards/{card_id}.png`
- Arte enemigo: `game/assets/sprites/enemies/{enemy_id}.png`
- Prompts exportados: `game/data/card_prompts.json`

## Música

Tracks esperados (WAV/OGG):

- `game/assets/music/menu.*`
- `game/assets/music/map.*`
- `game/assets/music/combat.*`
- `game/assets/music/event.*`
- `game/assets/music/boss.*`
- `game/assets/music/ending.*`

Si faltan, se crean placeholders WAV locales para que no crashee.

## Regeneración de datos y reinicio seguro

- La opción de **Reset Run Data** marca una regeneración diferida para el próximo arranque mediante `game/data/regen_on_boot.flag`.
- Este flujo evita fallos por bloqueos de archivos en Windows cuando el juego aún tiene recursos cargados.
- Si querés forzar regeneración de assets, podés usar `autogen_art_mode = "force"` en `game/data/settings.json`.
