# Pipeline Stage And Layer Coordination

## Stage Order
1. Parse semantic payload.
2. Resolve reference bundle.
3. Freeze sector map.
4. Build figure skeleton.
5. Build body volumes.
6. Merge silhouette.
7. Render subject detail.
8. Attach weapon/object.
9. Render background and environment.
10. Render symbol.
11. Render FX back.
12. Composite subject and object.
13. Render FX front.
14. Validate.
15. Retry once only if metrics fail.

## Loop Policy
- Allowed loop: one controlled retry after validation.
- Removed loop types:
  - repeated random pose rebuilding
  - repeated overlay accumulation
  - repeated subject redraw at output resolution
  - uncontrolled FX retries

## Layer Rules
- `background`: atmospheric base only.
- `environment`: spatial support only.
- `subject_mask`: source of silhouette readability.
- `subject_detail`: secondary internal information only.
- `object`: identity reinforcement tied to a body anchor.
- `symbol`: lore reinforcement behind subject.
- `fx_back`: aura and depth support behind silhouette.
- `fx_front`: minor support only, never the primary read.

## Failure Routing
- If `occ_subject` fails: increase subject mass or template width/height, not FX.
- If `occ_object` fails: enlarge or clarify weapon template, not symbol.
- If `contrast_score` fails: adjust figure-ground separation before adding more outline.
- If `subject_visible_ratio` fails: reduce front FX and symbol interference first.
- If `silhouette_integrity` fails: refine volumes and merge rules before tuning color.
- If `limb_connection_score` fails: correct skeleton continuity and overlap.
