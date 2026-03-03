# CHAKANA: Mago Morado (MVP)

## Ejecutar (Windows)

```powershell
py -3.12 -m venv game\.venv
game\.venv\Scripts\python.exe -m pip install -U pip
game\.venv\Scripts\python.exe -m pip install -r requirements.txt
game\.venv\Scripts\python.exe -m game.main
```

## Arte de cartas

El juego autogenera arte procedural si falta un PNG de carta en:

- `assets/sprites/cards/{card_id}.png`

Para reemplazar arte, coloca PNG de **256x160** con el mismo `card_id`.

Además se exportan prompts opcionales a:

- `assets/sprites/cards/prompts_cards.txt`

## Música esperada (opcional)

- `assets/music/map.ogg`
- `assets/music/combat.ogg`
- `assets/music/event.ogg`
- `assets/music/boss.ogg`

Si faltan, el juego continúa sin crashear.
