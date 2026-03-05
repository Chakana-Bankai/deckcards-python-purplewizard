import pygame


class InputAction:
    def __init__(self, kind, **payload):
        self.kind = kind
        self.payload = payload


def is_key(event, key):
    return event.type == pygame.KEYDOWN and event.key == key
