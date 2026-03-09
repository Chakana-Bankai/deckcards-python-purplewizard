# Content Lock 1.0 Report

Date: 2026-03-08

## Scope Lock
- Cards: 60
- Relics: 12
- Enemies (regular roster): 31
- Bosses/Archons: 4
- Biomes: 4
- Events: 6
- Codex sections: 10
- Codex cards: 60
- Codex relics: 12
- Tutorial core steps: 7

## Validation Result
- Status: OK
- Issues: 0
- Warnings: 2

Warnings observed:
- `block_window:legendary:avg=3.50 expected~8-12`
- `enemy_hp_high:max=320`

## Notes
- Content scope is now locked by `game/data/content_lock_1_0.json`.
- Runtime boot checks now include content lock audit summary.
- No feature systems were added in this phase.
