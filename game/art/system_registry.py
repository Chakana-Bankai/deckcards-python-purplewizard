from __future__ import annotations

CANONICAL_MODULES = {
    'shape_dna': 'game.art.shape_dna',
    'silhouette_generator': 'game.art.silhouette_generator',
    'symbol_overlay': 'game.art.symbol_overlay',
    'scene_background': 'game.art.scene_background',
    'frame_renderer': 'game.render.frame_renderer',
    'identity_lock': 'game.art.identity_lock',
    'geometric_ritual_engine': 'game.art.geometric_ritual_engine',
}

LEGACY_MODULES = {
    'old_scene_composers': [
        'game.art.gen_art32',
        'game.art.gen_card_art32',
        'game.art.gen_card_art_advanced',
        'game.art.scene_test_generator_v1',
        'game.art.scene_test_generator_v2',
        'game.art.scene_test_generator_v3',
        'game.art.scene_test_generator_v4',
        'game.art.scene_test_generator_v5',
        'game.art.scene_test_generator_v_final',
    ],
    'legacy_frame_generators': [
        'game.art.frame_engine',
    ],
    'redundant_overlay_engines': [
        'game.art.finish_render_system',
        'game.art.surface_style_pass',
        'game.art.symbolic_crisp_pass',
        'game.art.heroic_warrior_pass',
    ],
    'experimental_art_systems': [
        'game.art.silhouette_builder',
        'game.art.silhouette_resolver',
        'game.art.scene_test_generator_symbolic_crisp',
        'game.art.scene_test_generator_solar_heroic',
    ],
}


def canonical_pipeline_order() -> list[str]:
    return ['card_dna', 'silhouette', 'pose', 'weapon', 'energy', 'background', 'frame', 'identity_lock']


def is_legacy_module(module_path: str) -> bool:
    return any(module_path in group for group in LEGACY_MODULES.values())
