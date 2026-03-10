# Chakana Audio Engine — Target Structure (Phase 2)

Fecha: 2026-03-09
Estado: scaffold creado, migracion pendiente (safe)

## Objetivo
Definir una arquitectura de audio extensible sin romper el runtime actual (`game/audio/*`).

## Estructura objetivo implementada

- `engine/audio/core/`
  - `contracts.py`
- `engine/audio/music/`
  - `music_state_machine.py`
  - `music_layer_controller.py`
  - `music_transition_manager.py`
  - `music_manifest.py`
- `engine/audio/stingers/`
  - `stinger_player.py`
  - `stinger_manifest.py`
- `engine/audio/ambient/`
  - `ambient_player.py`
  - `ambient_manifest.py`
- `engine/audio/mixer/`
  - `audio_bus_manager.py`
  - `ducking_controller.py`
  - `volume_profiles.py`
- `engine/audio/sfx/`
- `engine/audio/manifests/`
- `engine/audio/utils/`

## Principios de integracion segura
1. No reemplazar de golpe `game/audio/audio_engine.py`.
2. Mantener wrappers actuales (`MusicManager`, `SFXManager`) durante migracion.
3. Enrutar por fases: estado musical -> capas -> transiciones -> stingers -> ambient -> mixer.
4. Conservar compatibilidad con manifests actuales mientras se normalizan rutas.

## Mapeo inicial (legacy -> target)
- `game/audio/audio_engine.py` -> orquestador temporal durante migracion.
- `game/data/bgm_manifest.json` -> `engine/audio/music/music_manifest.py` (adapter).
- `game/audio/audio_manifest.json` -> fuentes de `stinger_manifest` / `ambient_manifest` / SFX manifest normalizado.
- controles de volumen de `settings` -> `engine/audio/mixer/audio_bus_manager.py`.

## Riesgos detectados para siguientes fases
- `bgm_manifest.json` usa rutas absolutas (portabilidad baja).
- conviven rutas SFX generadas y fallback legacy (`game/assets/sfx`).

## Entregable fase 2
Arquitectura base creada sin cambiar flujo de reproduccion actual.
