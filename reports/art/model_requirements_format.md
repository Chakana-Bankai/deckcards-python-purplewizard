# Model Requirements Format

Use this format to identify which visual models or references are still missing before scaling the pipeline.

## Card Family Request
- `card_id`:
- `archetype`:
- `pose_family`:
- `weapon_family`:
- `symbol_family`:
- `environment_family`:
- `lighting_family`:
- `aura_family`:

## Required Model Slots
- `silhouette_model_primary`:
  - Purpose: defines the readable outer figure.
  - Needed qualities: archetype-specific proportions, head/torso/pelvis/leg relationship, clear stance.
  - Source type: concept art / sprite sheet / silhouette sheet / photo reference.
- `costume_model_secondary`:
  - Purpose: robe, armor, mantle, shoulder language.
  - Needed qualities: readable at low resolution, non-photoreal detail breakup.
- `weapon_model_primary`:
  - Purpose: establish object identity and attachment.
  - Needed qualities: clear hand grip, tip shape, diagonal or vertical readability.
- `symbol_model_support`:
  - Purpose: sacred/lore reinforcement behind or above subject.
  - Needed qualities: low-occlusion geometry, iconic silhouette.
- `environment_model_support`:
  - Purpose: reinforce world without replacing subject.
  - Needed qualities: horizon structure, architecture rhythm, depth planes.

## Acceptance Checklist
- `silhouette_clear_at_25_percent_scale`:
- `weapon_attached_visually`:
- `head_torso_pelvis_readable`:
- `subject_still_reads_without_symbol`:
- `environment_supportive_not_dominant`:
- `front_fx_not_required_for_readability`:

## Search Notes
- `search_query_terms`:
- `reference_pack_path`:
- `gaps_found`:
- `replacement_priority`:
