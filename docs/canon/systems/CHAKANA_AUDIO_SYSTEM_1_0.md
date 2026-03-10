# CHAKANA AUDIO SYSTEM 1.0

## Objetivo
Definir la arquitectura can?nica de audio para Chakana: Purple Wizard.

## Capas
- Music state machine
- Layered music
- Stingers
- Ambient soundscapes
- Mixer / buses / ducking
- Manifest-driven loading

## Estados principales
- menu
- map
- combat
- boss
- shop
- reward
- dialogue
- defeat
- victory
- credits

## Fuente de verdad
- Direcci?n musical: `docs/canon/direction/MUSIC_DIRECTION.md`
- Manual maestro: `docs/canon/manual/CHAKANA_MANUAL_1_0.md`
- Referencia de sistemas: `docs/canon/reference/GAME_SYSTEMS_REFERENCE.md`

## Runtime
- Motor: `game/audio/audio_engine.py`
- Arquitectura engine: `engine/audio/`
- Manifest can?nico: `game/data/audio_manifest.json`

## Regla operativa
La carga activa debe priorizar:
1. curated
2. generated validado
3. fallback
