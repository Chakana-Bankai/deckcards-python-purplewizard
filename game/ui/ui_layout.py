import pygame

from game.settings import INTERNAL_WIDTH


def centered_column(count, width=320, height=56, gap=14, y_start=220):
    return [pygame.Rect((INTERNAL_WIDTH - width) // 2, y_start + i * (height + gap), width, height) for i in range(count)]
