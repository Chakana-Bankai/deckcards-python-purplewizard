# UI System Audit Report (v1)

## Scope
Technical audit of current UI architecture and integration status. No gameplay rebalance, asset regeneration, or visual redesign applied.

## A) What Exists

### New centralized UI system
- `game/ui/system/brand.py`
- `game/ui/system/colors.py`
- `game/ui/system/fonts.py`
- `game/ui/system/layout.py`
- `game/ui/system/layers.py`
- `game/ui/system/effects.py`
- `game/ui/system/components.py`
- `game/ui/system/modals.py`
- `game/ui/system/icons.py`
- `game/ui/system/widgets.py`

### Legacy/parallel UI layers still present
- `game/ui/theme.py` (compatibility bridge)
- screen-level direct `pygame.draw.*` rendering
- old helpers: `game/ui/widgets.py` (deprecated marker added)
- duplicate combat layout module: `game/ui/layouts/combat_layout.py` (deprecated marker added)

## B) What Is Really Used

### UI system file usage status
| File | Status | Evidence |
|---|---|---|
| `brand.py` | Partially used | Imported by `theme.py`, `menu.py` |
| `colors.py` | Partially used | Imported by `theme.py`, `combat.py`, `map.py`, `menu.py`, `reward.py` |
| `fonts.py` | Partially used | Imported by `menu.py`, `components/modal_confirm.py` |
| `layout.py` | Partially used | Imported by `map.py`; used inside `system/modals.py` |
| `layers.py` | Partially used | Imported by `combat.py` (layer annotations) |
| `effects.py` | Unused | No runtime imports found |
| `components.py` | Used | Imported by `combat/map/menu/event/reward/path_select` |
| `modals.py` | Partially used | Used via `components/modal_confirm.py` wrapper |
| `icons.py` | Unused | No runtime imports found |
| `widgets.py` | Unused | No runtime imports found |

### Core screen adoption snapshot
| Screen | UI system integration | Notes |
|---|---|---|
| `menu.py` | Yes | Uses `UIPanel`, `UIButton`, `fonts`, `colors` |
| `combat.py` | Yes | Uses `UIPanel`, `UITooltip`, `colors`, layer annotations |
| `map.py` | Yes | Uses `UIPanel`, `safe_area`, `colors` |
| `reward.py` | Yes (partial) | Uses `UIPanel`, `UIButton` |
| `event.py` | Yes (partial) | Uses `UIPanel`, `UIButton` |
| `path_select.py` | Yes (partial) | Uses `UIPanel`, `UIButton` |
| `shop.py` | No | Legacy direct draw + hardcoded tuples |
| `deck.py` | No | Legacy direct draw + duplicated card/list draw |
| `studio_intro.py` | No | Direct draw, local `SysFont("arial")` |
| `loading.py` | No | Direct draw, local gradient/particles |

## C) What Is Duplicated

### Theme/color duplication
- Central semantic palette exists (`system/colors.py`) but multiple screens still draw with inline tuples.
- `theme.py` is a bridge, but hardcoded tuples still bypass semantics in several screens.

### Layout duplication
- Manual `pygame.Rect` math repeated across combat, map, reward, deck, shop.
- Two combat layout modules exist:
  - Active: `game/ui/layout/combat_layout.py`
  - Legacy duplicate: `game/ui/layouts/combat_layout.py` (now marked deprecated)

### Modal duplication
- Central modal base exists (`system/modals.py`) but only confirm modal is routed through it.
- Other modal-like flows remain independent:
  - `ModalCardPicker` (`components/modal_card_picker.py`)
  - reward/guide selection layouts in `reward.py`
  - archetype selection in `path_select.py`

### Card rendering duplication
Current card render paths are split:
- Combat hand/hover: `combat.py` (`_draw_card_background`, `_draw_card`)
- Reward cards: `reward.py` (`_draw_cards_mode`)
- Deck list + preview: `deck.py` + `CardPreviewPanel`
- Pack opening cards: `pack_opening.py`
- Modal picker cards: `modal_card_picker.py`
- Archetype featured legendary + banners: `path_select.py`

Single source of truth is not established yet.

## D) What Should Be Removed (or fully deprecated)

1. `game/ui/layouts/combat_layout.py`
- Unused duplicate of combat layout logic.
- Safe to remove after one cycle of validation.

2. `game/ui/widgets.py` (legacy `Button`)
- No active imports found.
- Replaced conceptually by `system/components.UIButton`.

3. Unused system modules (currently inert)
- `system/effects.py`, `system/icons.py`, `system/widgets.py`
- Keep for roadmap, but mark as "not yet adopted" to avoid confusion.

## E) What Should Be Refactored

### 1) Modal unification
Target: route all modal-like flows through `ModalBase` family.
- `ModalCardPicker` -> `CardGridModal`
- Reward/guide selection panels -> `ChoiceModal` / `CardGridModal`
- Event/guide lore overlays -> `LoreModal`
- Keep wrappers for compatibility during transition.

### 2) Card renderer unification
Target: one canonical card surface renderer.
- Extract from `combat.py` (most complete visual state today) into shared renderer module.
- Reuse in reward/deck/pack/modal/archetype contexts with scale presets.

### 3) Layout helper adoption
Target: reduce manual x/y blocks.
- Use `system/layout.py` helpers in shop, deck, loading, studio intro next.
- Convert panel splits and button anchoring first (low risk).

### 4) Semantic color pass
Target: remove direct RGB tuples from core screens.
- Prioritize `combat.py` (highest tuple density), then `deck.py`, `shop.py`.

### 5) Font pipeline alignment
Target: central font accessor everywhere.
- Replace direct `pygame.font.SysFont(...)` in `studio_intro.py` and any remaining local constructors.

## F) Proposed Refactor Order (Safe)

1. **Phase 1: Safety/infra (no visual intent changes)**
- Keep bridge `theme.py`
- Finish modal wrappers
- Consolidate deprecated files removal behind feature flag or one release cycle

2. **Phase 2: Cards + modals (highest duplication payoff)**
- Create shared card renderer API
- Migrate reward/deck/pack/modal picker/path-select

3. **Phase 3: Layout standardization**
- Migrate shop/deck/loading/studio intro to `system/layout`
- Normalize safe-area usage and bottom controls

4. **Phase 4: Semantic colors/effects**
- Replace hardcoded tuples with `UColors`
- Adopt `effects.py` helpers where equivalent animations already exist

5. **Phase 5: Final cleanup**
- Remove deprecated legacy modules after verification
- Update docs with final "source of truth" map

---

## Combat UI Structure Audit (current)

Logical blocks identified:
- Enemy panel (top strip)
- Dialogue panel (`voices_rect`)
- Mechanical feed/detail panel (`card_detail`)
- Hand area
- Chakana status block
- Action button block
- Hover card overlay + tooltip

Observed issues:
- Still high amount of manual draw/layout code in one file.
- Some color literals remain inline despite semantic palette being available.
- Grouping improved, but widget extraction is pending.

## Map UI Structure Audit (current)

Logical blocks identified:
- Top bar/chips/deck button
- Left lore panel
- Center graph + stage rail
- Right status panel
- Bottom lore strip

Observed issues:
- Better spacing guards now exist, but layout remains hand-authored.
- Node label control improved; still not fully componentized.

## Modal Inventory

- `ModalConfirm` -> routed through `ModalBase` wrapper.
- `ModalCardPicker` -> standalone custom modal (not yet unified).
- Reward/guide selection -> screen-level pseudo-modal behavior.
- Path/archetype selection -> standalone screen modal-like layout.
- Tooltips in combat -> now uses `UITooltip`, but no global tooltip manager.

## Acceptance Check
- Game compile check: passed.
- Gameplay rules untouched.
- Report file created: `docs/UI_AUDIT_REPORT.md`.
- Refactor path documented with low-risk sequencing.
