"""Tiny state machine for screen management."""


class StateMachine:
    def __init__(self):
        self.current = None

    def set(self, state):
        self.current = state
        if hasattr(state, "on_enter"):
            state.on_enter()

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def render(self, surface):
        if self.current:
            self.current.render(surface)
