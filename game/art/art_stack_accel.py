from __future__ import annotations

from pathlib import Path
import math

import cv2
import numpy as np
from noise import pnoise2
from PIL import Image, ImageOps
import pygame


def surface_rgba_array(surface: pygame.Surface) -> np.ndarray:
    width, height = surface.get_size()
    data = pygame.image.tobytes(surface, 'RGBA')
    return np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4)).copy()


def surface_alpha_array(surface: pygame.Surface) -> np.ndarray:
    return surface_rgba_array(surface)[:, :, 3]


def surface_luma_array(surface: pygame.Surface) -> np.ndarray:
    rgba = surface_rgba_array(surface).astype(np.float32)
    return (0.2126 * rgba[:, :, 0] + 0.7152 * rgba[:, :, 1] + 0.0722 * rgba[:, :, 2]) / 255.0


def pil_from_surface(surface: pygame.Surface) -> Image.Image:
    return Image.frombytes('RGBA', surface.get_size(), pygame.image.tobytes(surface, 'RGBA'))


def surface_from_pil(image: Image.Image) -> pygame.Surface:
    image = image.convert('RGBA')
    return pygame.image.fromstring(image.tobytes(), image.size, 'RGBA').convert_alpha()


def load_reference_with_pillow(path: Path, size: tuple[int, int]) -> pygame.Surface:
    image = Image.open(path).convert('RGBA')
    fitted = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return surface_from_pil(fitted)


def save_surface_with_pillow(surface: pygame.Surface, path: Path, size: tuple[int, int] | None = None) -> None:
    image = pil_from_surface(surface)
    if size and image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def blur_score_cv(path: Path) -> float:
    frame = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if frame is None:
        return 0.0
    return float(cv2.Laplacian(frame, cv2.CV_64F).var())


def cleanup_mask_with_cv(mask_surface: pygame.Surface, threshold: int = 18) -> pygame.Surface:
    alpha = surface_alpha_array(mask_surface)
    binary = np.where(alpha >= threshold, 255, 0).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_canvas = np.zeros_like(cleaned)
    if contours:
        cv2.drawContours(contour_canvas, contours, -1, 255, thickness=cv2.FILLED)
    height, width = contour_canvas.shape
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, 3] = contour_canvas
    out.blit(pygame.image.frombuffer(rgba.tobytes(), (width, height), 'RGBA'), (0, 0))
    return out


def contour_edge_score(mask_surface: pygame.Surface, threshold: int = 18) -> float:
    alpha = surface_alpha_array(mask_surface)
    binary = np.where(alpha >= threshold, 255, 0).astype(np.uint8)
    edges = cv2.Canny(binary, 60, 180)
    area = max(1.0, float(np.count_nonzero(binary)))
    return round(float(np.count_nonzero(edges)) / math.sqrt(area), 4)


def noise_overlay(
    size: tuple[int, int],
    color: tuple[int, int, int],
    alpha: int,
    *,
    scale: float = 26.0,
    octaves: int = 2,
    persistence: float = 0.55,
    lacunarity: float = 2.0,
    seed: int = 0,
) -> pygame.Surface:
    width, height = size
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            value = pnoise2(
                (x + seed * 17) / scale,
                (y + seed * 31) / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                repeatx=width,
                repeaty=height,
                base=seed,
            )
            norm = max(0.0, min(1.0, (value + 1.0) * 0.5))
            rgba[y, x, 0] = color[0]
            rgba[y, x, 1] = color[1]
            rgba[y, x, 2] = color[2]
            rgba[y, x, 3] = int(alpha * norm)
    overlay.blit(pygame.image.frombuffer(rgba.tobytes(), (width, height), 'RGBA'), (0, 0))
    return overlay
