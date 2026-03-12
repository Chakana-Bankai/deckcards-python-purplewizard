# Figure Structure Format

Use this format to define the figure before any rendering pass.

## Figure Identity
- `template_id`:
- `archetype`:
- `pose_preset`:
- `shape_language`:
- `mood`:

## Skeleton Contract
- `head_anchor`:
- `neck_anchor`:
- `left_shoulder_anchor`:
- `right_shoulder_anchor`:
- `left_elbow_anchor`:
- `right_elbow_anchor`:
- `left_hand_anchor`:
- `right_hand_anchor`:
- `pelvis_anchor`:
- `left_knee_anchor`:
- `right_knee_anchor`:
- `left_foot_anchor`:
- `right_foot_anchor`:

## Primary Volumes
- `head_volume`: oval / circle
- `torso_volume`: trapezoid / triangle / robe mass
- `pelvis_volume`: compact block / plate
- `left_arm_upper_volume`:
- `left_arm_lower_volume`:
- `right_arm_upper_volume`:
- `right_arm_lower_volume`:
- `left_leg_upper_volume`:
- `left_leg_lower_volume`:
- `right_leg_upper_volume`:
- `right_leg_lower_volume`:
- `outer_volume`: cloak / mantle / armor shell

## Anchor Contract
- `weapon_origin_anchor`:
- `weapon_tip_anchor`:
- `back_anchor`:
- `symbol_center_anchor`:
- `halo_anchor`:
- `fx_spawn_anchor`:

## Silhouette Rules
- `subject_height_ratio_target`: 0.45-0.60
- `subject_center_x_target`: image_center +/- 15%
- `silhouette_integrity_min`: 0.70
- `limb_connection_score_min`: 0.72
- `torso_core_must_remain_visible`: true

## Detail Rules
- `detail_pass_cannot_break_outer_silhouette`: true
- `symbol_cannot_cover_torso_core`: true
- `front_fx_cannot_define_shape`: true
