from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StageContract:
    stage_id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    rule: str
    loop_policy: str


@dataclass(frozen=True, slots=True)
class LayerContract:
    layer_id: str
    purpose: str
    occludes_subject: bool
    max_alpha: float
    notes: str


STAGE_CONTRACTS = (
    StageContract(
        stage_id='semantic_parse',
        inputs=('prompt', 'tags', 'lore_tokens'),
        outputs=('semantic_payload',),
        rule='Resolve archetype, pose family, weapon family, symbol family, environment family, aura family before rendering.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='reference_selection',
        inputs=('semantic_payload', 'art_reference_catalog'),
        outputs=('reference_bundle',),
        rule='Collect only the references needed for background/environment/symbol support and template matching.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='sector_layout',
        inputs=('semantic_payload',),
        outputs=('sector_map',),
        rule='Freeze background, environment, subject, object, symbol, fx_back and fx_front sectors at composition resolution.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='figure_skeleton',
        inputs=('semantic_payload', 'sector_map', 'character_template'),
        outputs=('figure_skeleton',),
        rule='Build joints and anchors from archetype + pose preset; do not generate random body topology.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='body_volumes',
        inputs=('figure_skeleton',),
        outputs=('body_volumes',),
        rule='Convert skeleton into stylized readable masses with overlap and weapon-side bias.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='silhouette_merge',
        inputs=('body_volumes',),
        outputs=('subject_silhouette', 'silhouette_metrics'),
        rule='Unify the figure into one readable silhouette before internal detail rendering.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='subject_detail',
        inputs=('subject_silhouette', 'figure_skeleton', 'palette'),
        outputs=('subject_detail_layer',),
        rule='Apply costume/armor/robe motifs without breaking silhouette readability.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='object_attach',
        inputs=('figure_skeleton', 'weapon_template', 'palette'),
        outputs=('object_layer',),
        rule='Attach object to a valid anchor only; floating objects are invalid.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='background_environment',
        inputs=('reference_bundle', 'sector_map', 'palette'),
        outputs=('background_layer', 'environment_layer'),
        rule='Environment supports the subject and never replaces the subject silhouette.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='symbol_and_fx',
        inputs=('semantic_payload', 'figure_skeleton', 'sector_map'),
        outputs=('symbol_layer', 'fx_back_layer', 'fx_front_layer'),
        rule='Symbols stay behind or above the torso core; front FX must stay under occlusion limits.',
        loop_policy='single_pass',
    ),
    StageContract(
        stage_id='validation_retry',
        inputs=('all_layers', 'silhouette_metrics'),
        outputs=('final_metrics',),
        rule='Validate occupancy, readability, attachment and visibility; allow exactly one controlled retry.',
        loop_policy='retry_once',
    ),
)


LAYER_CONTRACTS = (
    LayerContract('background', 'Atmospheric base support only.', False, 1.00, 'No subject replacement.'),
    LayerContract('environment', 'World and architecture context.', False, 0.90, 'Keep luminance around the subject controlled.'),
    LayerContract('subject_mask', 'Primary silhouette mass.', False, 1.00, 'Main readability source.'),
    LayerContract('subject_detail', 'Internal costume and material design.', False, 0.95, 'Cannot destroy silhouette edges.'),
    LayerContract('object', 'Weapon or support object.', False, 1.00, 'Must touch hand or valid anchor.'),
    LayerContract('symbol', 'Lore symbol behind or above subject.', False, 0.24, 'Cannot cover torso core.'),
    LayerContract('fx_back', 'Aura and back support energy.', False, 0.28, 'Behind silhouette or outside the core.'),
    LayerContract('fx_front', 'Minor front particles only.', True, 0.18, 'Must remain under subject occlusion limits.'),
)
