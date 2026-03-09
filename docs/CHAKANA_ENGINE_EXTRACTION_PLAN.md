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

## 2026-03-09 - Fase 1-2 Integration Update

- Added engine-candidate gameplay rules module: `game/systems/gameplay_rules.py`.
- Combat now reads normalized baseline rules from `game/data/balance/combat.json`.
- Deck flow lock:
  - starting hand 5
  - draw per turn 5
  - hand max 10
  - overdraw redirected to discard.
- Added safe prep for enemy intent mini-decks (`intent_deck`) with fallback to existing pattern.
- No ID migrations, no destructive content cleanup.

## 2026-03-09 - Fase 3 Enemy Deck System

- Added enemy intent-deck builder: `game/systems/enemy_intent_deck.py`.
- Enemy content load now enriches each enemy with:
  - `enemy_type`
  - `intent_deck`
  - `ai_profile`
- `Enemy` now supports:
  - intent deck draw/discard/reshuffle
  - simple scoring AI for intent choice
  - safe fallback to legacy pattern.

## 2026-03-09 - Fase 4 Hiperborea Unlock + Codex Integration

- Added safe set unlock gate after 3 tutorial combats.
- Added runtime reward/shop/pack card pool gating by discovered sets.
- Added separate Hiperborea card catalog loader (cards_hiperboria.json).
- Codex now loads Hiperborea entries from codex_cards_hiperboria.json and reveals the tab when unlocked.

## 2026-03-09 - Fase 5 Relic Slots Consolidation

- Added reusable relic inventory helpers in runtime (_relic_slot_limit, _add_relics_to_inventory).
- Enforced non-breaking relic slot cap (8) across rewards/shop.
- Map/combat HUD now surface relic occupancy (x/slots) for clarity.
