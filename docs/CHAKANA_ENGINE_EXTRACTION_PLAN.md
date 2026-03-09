# CHAKANA Engine Extraction Plan

## Scope
This document defines a safe extraction path from the current game codebase into reusable Chakana Engine modules without breaking Purple Wizard runtime.

## Current Principles
- Non-destructive migration.
- Keep gameplay stability first.
- Use compatibility shims during file moves.
- Separate reusable runtime systems from Purple Wizard content.

## Target Engine Domains
- `core`: loop/state/config/randomness/safe IO.
- `combat`: turn model, action queue, deterministic resolution.
- `ui`: reusable primitives, layout helpers, typography/icon services.
- `visual`: generators, cache, portrait pipeline.
- `audio`: runtime mixer, context selection, cache/manifest.
- `narrative`: dialogue scene presenter and timeline hooks.
- `content`: only schema loaders and validators (not game lore itself).
- `tools`: QA/validation/build utilities.

## Recommended Phases
1. Baseline QA lock and reports.
2. Extract utility-first modules (`ui/system`, `core` helpers).
3. Extract visual/audio runtime + cache modules.
4. Extract combat internals after integration tests.
5. Keep Purple Wizard content in game-specific layer.

## Shim Strategy
- Old imports must remain valid during migration.
- Old module path re-exports new location.
- Remove shims only after a full release-cycle verification.

## Asset Ownership Strategy
- Curated assets: source of truth.
- Generated assets: cache products.
- Fallback assets: runtime-safe defaults.
- No broad regeneration on boot.

## Risk Controls
- No move without smoke + QA run.
- No gameplay logic changes inside extraction-only tickets.
- Keep deterministic loaders for cards/relics/enemies.

## Exit Criteria for Engine Extraction Start
- Stable QA reports.
- Canonical card renderer ownership documented.
- Canonical portrait pipeline documented.
- Audio cache ownership documented.
- Import shim policy accepted.
