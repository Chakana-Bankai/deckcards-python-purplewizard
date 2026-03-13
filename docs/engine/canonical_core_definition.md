# Chakana Engine Canonical Core Definition

## Scope

This document defines the canonical beta core for Chakana Engine after the Phase 1 system audit.

The beta core is intentionally narrow.
Its purpose is to stabilize the project around the systems that most directly support:

1. combat
2. cards
3. lore

Everything else must either:
- support those three pillars
- remain clearly experimental
- or move toward archive status

## Beta Mission

Chakana Engine beta is not a broad sandbox.
It is a focused card-combat game foundation where:

- combat is the main playable loop
- cards are the main authored and balanced content layer
- lore gives identity, codex meaning, and world continuity

The beta is successful if:
- combat runs are stable and testable
- card content is canonical and validated
- lore is linked to cards, events, combat flavor, and codex
- support systems remain subordinate to the core loop

## Canonical Core Systems

### 1. Combat

Canonical combat core:
- `game/combat/*`
- `game/systems/enemy_deck_system.py`
- `game/systems/gameplay_rules.py`
- `game/ui/screens/combat.py`
- `game/services/combat_content_validator.py`
- `game/services/content_lock_validator.py`

Why canonical:
- This is the primary runtime loop for beta.
- It is the main area where player experience, balance, and simulation matter.
- It is the foundation for beta runs, QA, and progression tuning.

### 2. Cards

Canonical card core:
- `game/cards/card_canon_registry.py`
- `game/data/cards.json`
- `game/data/cards_hiperboria.json`
- `game/data/cards_arconte.json`
- `game/services/card_coherence.py`
- `game/services/deck_integrity.py`
- `tools/rebuild_card_sets.py`
- card rendering path:
  - `game/ui/components/card_renderer.py`
  - `game/render/frame_renderer.py`

Why canonical:
- Cards are the main authored gameplay unit.
- Cards define progression, archetypes, codex visibility, and combat options.
- Card validation and set rebuild flow must stay deterministic and testable.

### 3. Lore

Canonical lore core:
- `game/lore/lore_engine.py`
- `game/core/lore_service.py`
- `game/data/lore/*`
- `game/data/codex*.json`
- `game/ui/screens/codex.py`

Why canonical:
- Lore is not optional flavor for beta.
- It gives identity to cards, combat barks, codex, and map/event continuity.
- Lore must remain connected to runtime content, not isolated in documents only.

## Canonical Secondary Support Systems

These systems remain canonical for beta, but only as support for combat, cards, and lore.

### Codex
- `game/ui/screens/codex.py`
- `game/data/codex*.json`
- codex payload functions from `game/cards/card_canon_registry.py`

Role in beta:
- expose card and lore knowledge
- verify that content is visible and coherent

### Map
- `game/ui/screens/map.py`
- `game/systems/meta_director.py`
- `game/systems/event_system.py`

Role in beta:
- provide traversal between combat, event, and reward nodes
- stay lightweight and in service of runs

### Shop and Rewards
- `game/ui/screens/shop.py`
- `game/systems/reward_system.py`
- `game/relics/*`

Role in beta:
- support run structure and progression
- must not become a parallel design focus

### Art Representation
- runtime representation:
  - `game/ui/components/card_renderer.py`
  - `game/render/frame_renderer.py`
- card art generation stack:
  - `game/content/card_art_generator.py`
  - `game/art/gen_card_art_advanced.py`
  - `game/art/assembly_pipeline.py`

Role in beta:
- support readability, identity, and card clarity
- stay subordinate to gameplay and content correctness

### Contextual Audio
- `game/services/audio_pipeline.py`
- `tools/assets/build_curated_context_audio.py`
- generated/curated audio assets under `game/audio/` and `game/assets/curated/audio/`

Role in beta:
- reinforce combat, map, codex, and shop context
- not become a primary expansion vector right now

### QA and Simulations
- `game/qa/content_validator.py`
- `game/services/content_lock_validator.py`
- `tools/qa/check_beta_run_flow.py`
- simulation and smoke support currently spread in `tools/lib/*`

Role in beta:
- prove stability
- prove content coherence
- prove combat runs remain the center of testing

## Experimental Systems

These systems may stay in the repository, but they are not canonical beta centerpieces.

### Card DNA and auxiliary catalog layers
- `game/cards/card_dna_registry.py`
- `tools/build_card_dna_catalog.py`

Status:
- useful metadata and extension layer
- not the main canonical runtime source of cards

### Legacy and fallback art generators
- `game/art/gen_card_art32.py`
- `game/art/geometric_ritual_engine.py`

Status:
- useful as compatibility or fallback
- not the preferred beta-facing art path

### Tooling experiments and specialist passes
- several modules in `tools/lib/*`
- specialist art/audio passes
- balance and report helpers not directly wired into the canonical CLI surface yet

Status:
- useful, but should serve the master CLI and beta workflows
- should not define the engine identity by themselves

### Underdefined map/world placeholders
- `game/map/`
- `game/chakana_world/`

Status:
- conceptually relevant
- not yet mature enough to be treated as standalone canonical engine domains

## Archived Systems

These systems should be treated as historical, transitional, or archival rather than active beta foundation.

### Historical phase QA passes
- root `tools/qa_phase*.py`
- mirrored `tools/qa/qa_phase*.py`

Reason:
- useful execution history
- too phase-specific and overlapping for canonical daily beta operations

### Maintenance execution passes
- `tools/maintenance/*`

Reason:
- preserve institutional memory
- not canonical runtime or canonical beta command surface

### Art exploration variants
- `game/art/scene_test_generator_*`
- archived card-art pass outputs under `game/assets/sprites/cards/_archive_passes/*`

Reason:
- exploratory or historical
- not part of canonical beta production flow

## Systems That Should Move Toward Archive or Removal

These are not immediate deletion targets, but they should not remain part of the future canonical foundation.

### Top-level `qa/`

Current state:
- empty or functionally non-canonical

Decision:
- not part of canonical beta structure
- should be archived or removed in a sanitization pass

### `game/.venv/`

Current state:
- runtime tree contamination

Decision:
- not part of engine source
- should be excluded from canonical repository structure

## Beta Focus

During beta, the project should focus on:

### Primary focus
- combat stability
- card clarity and balance
- lore integration with codex and runtime

### Secondary focus
- codex consistency
- map flow reliability
- shop/reward support
- readable art representation
- contextual audio support
- reproducible QA and run simulations

### Non-focus areas for beta
- new broad world systems
- speculative engine extraction work as a primary task
- unlimited art experimentation without run impact
- side tooling that does not improve combat, cards, lore, or beta validation

## Canonical Operating Principle

For beta decisions:

- if a system directly improves combat, cards, or lore, it is favored
- if a system supports testing or visibility of those pillars, it is secondary canonical
- if a system duplicates another one, it should merge
- if a system mainly records old migration or old experimentation, it should archive

## Practical Canonical Foundation

The future beta-facing Chakana Engine should be understood as:

- runtime core in `game/`
- active authored content in `game/data/`
- canonical support tooling behind `tools/chakana_studio.py`
- documentation in `docs/engine/` and selected design/lore references

Not as:

- a loose collection of phase passes
- a broad experimental art sandbox
- a repository where every historical helper is equally active

## Immediate Conclusion

The canonical beta core is:

- combat
- cards
- lore

The canonical support layer is:

- codex
- map
- shop
- art representation
- contextual audio
- QA and simulations

The beta should now consolidate around that definition and resist scope drift.
