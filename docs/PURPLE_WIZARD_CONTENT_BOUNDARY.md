# Purple Wizard Content Boundary

## Goal
Define what remains Purple Wizard-specific and what should become reusable Engine code.

## Engine Candidate (Reusable)
- `game/core/*`
- `game/combat/*` (resolution logic, state transitions)
- `game/ui/system/*`
- `game/ui/layout/*`
- `game/visual/*`
- `game/audio/*`
- generic QA/validation helpers in `tools/*`

## Purple Wizard Specific Content
- `game/data/lore/*`
- `game/data/cards*.json`
- `game/data/relics.json`
- `game/data/enemies*.json`
- `game/data/events.json`
- localized strings and narrative copy
- biome names, archon names, civilization flavor text

## Generated vs Curated
- Curated assets (authoritative): `game/assets/curated/*`
- Generated cache assets: `game/assets/generated/*`, `game/visual/generated/*`, `game/audio/generated/*`
- Generated outputs must never silently replace curated source when curated exists.

## Deprecated / Legacy Policy
- Mark legacy paths first.
- Keep runtime compatibility wrappers while migration is active.
- Delete only after two stable QA cycles.

## Non-Negotiable Boundaries
- Do not hardcode Purple Wizard lore in reusable Engine helpers.
- Keep card/relic schema validation reusable.
- Keep screen-specific copy out of generic rendering components.

## Asset Loader Priority
1. Curated asset.
2. Generated asset/cache.
3. Fallback placeholder.

## Current Notes
- Curated master avatar structure is ready path-wise, but assets may still be incomplete.
- Card renderer is centralized and should remain canonical for all contexts.
- Audio context manifest is active and should remain single source for runtime mapping.
