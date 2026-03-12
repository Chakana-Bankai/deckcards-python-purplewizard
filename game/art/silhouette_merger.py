from __future__ import annotations

import pygame


def _pt(point):
    return (int(point[0]), int(point[1]))


def _draw_capsule(surface: pygame.Surface, a, b, width: int, color):
    pygame.draw.line(surface, color, _pt(a), _pt(b), max(1, int(width)))
    pygame.draw.circle(surface, color, _pt(a), max(1, int(width) // 2))
    pygame.draw.circle(surface, color, _pt(b), max(1, int(width) // 2))


def _draw_volume(surface: pygame.Surface, volume: dict[str, object], color):
    shape = str(volume['shape'])
    if shape == 'ellipse':
        cx, cy = volume['center']
        rx, ry = volume['radius']
        pygame.draw.ellipse(surface, color, pygame.Rect(int(cx - rx), int(cy - ry), int(rx * 2), int(ry * 2)))
    elif shape == 'polygon':
        pygame.draw.polygon(surface, color, [_pt(p) for p in volume['points']])
    elif shape == 'capsule':
        _draw_capsule(surface, volume['a'], volume['b'], int(volume['width']), color)


def _smooth(surface: pygame.Surface) -> pygame.Surface:
    w, h = surface.get_size()
    up = pygame.transform.smoothscale(surface, (w * 2, h * 2)).convert_alpha()
    down = pygame.transform.smoothscale(up, (w, h)).convert_alpha()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            if down.get_at((x, y)).a >= 18:
                out.set_at((x, y), (255, 255, 255, 255))
    return out


def _count_bridges(mask_surface: pygame.Surface) -> int:
    bounds = mask_surface.get_bounding_rect(min_alpha=12)
    if bounds.width <= 0 or bounds.height <= 0:
        return 0
    connected = 0
    for ratio in (0.24, 0.38, 0.52, 0.66, 0.80):
        y = bounds.top + int(bounds.height * ratio)
        run = 0
        max_run = 0
        for x in range(bounds.left, bounds.right):
            if mask_surface.get_at((x, y)).a > 12:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        if max_run >= max(6, bounds.width // 10):
            connected += 1
    return connected


def _frontal_block_score(mask_surface: pygame.Surface) -> float:
    bounds = mask_surface.get_bounding_rect(min_alpha=12)
    if bounds.width <= 0 or bounds.height <= 0:
        return 1.0
    center_band = pygame.Rect(bounds.centerx - max(3, bounds.width // 12), bounds.top + bounds.height // 8, max(6, bounds.width // 6), int(bounds.height * 0.58)).clip(mask_surface.get_rect())
    left_band = pygame.Rect(bounds.left + max(2, bounds.width // 14), center_band.top, max(4, bounds.width // 6), center_band.height).clip(mask_surface.get_rect())
    right_band = pygame.Rect(bounds.right - max(4, bounds.width // 6) - max(2, bounds.width // 14), center_band.top, max(4, bounds.width // 6), center_band.height).clip(mask_surface.get_rect())

    def fill(rect: pygame.Rect) -> float:
        total = max(1, rect.width * rect.height)
        count = 0
        for y in range(rect.top, rect.bottom):
            for x in range(rect.left, rect.right):
                if mask_surface.get_at((x, y)).a > 12:
                    count += 1
        return count / total

    center_fill = fill(center_band)
    side_fill = (fill(left_band) + fill(right_band)) / 2.0
    return round(max(0.0, min(1.0, 1.0 - max(0.0, center_fill - side_fill * 0.92))), 4)


def merge_body_volumes(size: tuple[int, int], volumes: list[dict[str, object]], archetype: str, color=(255, 255, 255, 255)) -> tuple[pygame.Surface, dict[str, float]]:
    layer = pygame.Surface(size, pygame.SRCALPHA)
    ordered = sorted(volumes, key=lambda item: 0 if item['kind'] in {'outer_left', 'outer_right'} else 1)
    for volume in ordered:
        _draw_volume(layer, volume, color)
    smooth = _smooth(layer)
    mask = pygame.mask.from_surface(smooth, 12)
    bounds = smooth.get_bounding_rect(min_alpha=12)
    bbox_area = max(1, bounds.width * bounds.height)
    fill_ratio = mask.count() / bbox_area
    silhouette_integrity = max(0.0, min(1.0, fill_ratio * (1.18 if archetype == 'archon' else 1.08)))
    limb_connection_score = max(0.0, min(1.0, _count_bridges(smooth) / 5.0))
    frontal_block_score = _frontal_block_score(smooth)
    return smooth, {
        'silhouette_integrity': round(silhouette_integrity, 4),
        'limb_connection_score': round(limb_connection_score, 4),
        'frontal_block_score': frontal_block_score,
    }
