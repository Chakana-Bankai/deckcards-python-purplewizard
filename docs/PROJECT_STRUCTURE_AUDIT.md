# Project Structure Audit

- Generated: `2026-03-09T08:15:31-03:00`
- Root: `C:\Users\mxpri\PurpleWizard\deckcards-python-purplewizard`

## Domain Snapshot
- `core`: present
- `combat`: present
- `ui`: present
- `visual`: present
- `audio`: present
- `narrative`: present
- `content`: present
- `tools`: present

## Classification Counts
- `curated_asset`: 1
- `engine_candidate`: 230
- `game_specific`: 2341
- `generated_asset`: 225
- `legacy_or_deprecated`: 4

## Canonical Ownership
- Card renderer canonical path: `game/ui/components/card_renderer.py`
- Audio ownership: `game/audio/*` + `game/data/bgm_manifest.json`
- Portrait pipeline ownership: `game/visual/portrait_pipeline.py`
- Curated avatar root: `game/assets/curated/avatars/`

## Safe Import Shim Strategy
- Keep wrapper modules on old paths if files move in future extraction passes.
- Migrate low-risk utility modules first; defer gameplay-critical modules.

## Asset Structure Prep
- Current roots: `game/assets/curated`, `game/assets/generated`, `game/visual/generated`, `game/audio/generated`.
- Target extraction structure: `assets/curated`, `assets/generated`, `assets/fallback`, `assets/deprecated`.
- This pass is non-destructive: no broad asset moves or deletions.
