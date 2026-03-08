# System Cleanup Lock Report

Date: 2026-03-08

## Summary
This pass focused on stability and anti-bloat cleanup without changing gameplay systems.

## 1) Dead / Redundant Code
- Consolidated duplicate `ContentService` implementations.
- `game/core/content_service.py` is now a compatibility shim delegating to the source-of-truth service.
- Active source of truth remains `game/services/content_service.py`.

## 2) UI / Text Cleanup
- Fixed corrupted mojibake runtime strings in:
  - `game/main.py`
  - `game/combat/combat_state.py`
- This removes broken in-game text rendering and hidden encoding debt.

## 3) Asset Cleanup
- Removed stale non-runtime backup artifact:
  - `game/data/art_manifest.bak`
- Ran generated asset orphan check against manifests:
  - audio orphans: 0
  - visual orphans: 0

## 4) Log / Cache Cleanup
- Reduced repeated safe I/O warning churn by introducing one-shot logging in `game/core/safe_io.py`.
- Reduced visual runtime log noise by removing cache/cache-file info spam paths.

## 5) Pre-Engine Boundaries
Reusable engine candidates:
- `game/audio/*`
- `game/visual/*`
- `game/ui/system/*`
- `game/core/safe_io.py`
- `game/services/content_lock_validator.py`

Purple Wizard content-specific modules/data:
- `game/data/*` lore/content JSON
- `game/ui/screens/*` screen behavior and game-specific flows
- card/enemy/relic content and localization strings

## Result
- Less duplicate logic
- Cleaner runtime logs
- Cleaner text rendering paths
- No active-system removal
