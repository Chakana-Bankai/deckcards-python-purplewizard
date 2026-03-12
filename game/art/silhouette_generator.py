from __future__ import annotations

import pygame

from game.art.body_volume_builder import build_body_volumes
from game.art.figure_skeleton_builder import build_figure_skeleton
from game.art.material_tone_system import build_material_tones
from game.art.shape_language_profile import resolve_shape_language
from game.art.silhouette_merger import merge_body_volumes


def generate_silhouette_spec(surface_size: tuple[int, int], semantic: dict, palette) -> dict[str, object]:
    skeleton = build_figure_skeleton(surface_size, semantic)
    skeleton['shape_profile'] = resolve_shape_language(str(skeleton['archetype']))
    tones = build_material_tones(palette, str(skeleton['archetype']), skeleton['shape_profile'])
    volumes = build_body_volumes(skeleton)
    silhouette, metrics = merge_body_volumes(surface_size, volumes, str(skeleton['archetype']), (*tones['cloth'][:3], 255))
    surface = pygame.Surface(surface_size, pygame.SRCALPHA)
    surface.blit(silhouette, (0, 0))
    return {
        'surface': surface,
        'skeleton': skeleton,
        'tones': tones,
        'metrics': metrics,
    }
