from __future__ import annotations

import pygame


def _pt(point) -> tuple[int, int]:
    return (int(point[0]), int(point[1]))


def symbolic_prop_lane(origin, lane_anchor, rect: pygame.Rect, mode: str) -> tuple[tuple[float, float], tuple[float, float]]:
    lane_x, lane_y = float(lane_anchor[0]), float(lane_anchor[1])
    if mode == 'forward_diagonal_short_grip':
        grip = (origin[0] + rect.width * 0.06, origin[1] - rect.height * 0.04)
        lane = (lane_x, origin[1] - rect.height * 0.18)
    elif mode == 'support_side_short_grip':
        grip = (origin[0] + rect.width * 0.02, origin[1] - rect.height * 0.02)
        lane = (lane_x, origin[1] - rect.height * 0.12)
    else:
        grip = (origin[0] + rect.width * 0.03, origin[1] - rect.height * 0.03)
        lane = (lane_x, origin[1] - rect.height * 0.16)
    return grip, lane


def add_symbolic_shoulder_cut(points: list[tuple[float, float]], inward: float, drop: float) -> list[tuple[float, float]]:
    if len(points) < 4:
        return points
    left = points[0]
    right = points[1]
    return [
        (left[0] + inward, left[1] + drop),
        (right[0] - inward, right[1] + drop),
        *points[2:],
    ]


def add_symbolic_robe_notch(points: list[tuple[float, float]], notch_depth: float) -> list[tuple[float, float]]:
    if len(points) < 4:
        return points
    mid_x = (points[2][0] + points[3][0]) / 2.0
    bottom_y = max(points[2][1], points[3][1])
    return [*points, (mid_x, bottom_y - notch_depth)]


def draw_hard_edge_plate(surface: pygame.Surface, points: list[tuple[float, float]], color, alpha: int = 255):
    pygame.draw.polygon(surface, (*color[:3], alpha), [_pt(p) for p in points])
