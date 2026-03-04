from __future__ import annotations

from game.combat.combat_state import CombatState


class CombatEngine:
    def __init__(self, state: CombatState):
        self.state = state

    @property
    def player(self):
        return self.state.player

    @property
    def hand(self):
        return self.state.hand

    @property
    def enemies(self):
        return self.state.enemies

    @property
    def turn(self):
        return self.state.turn

    @property
    def result(self):
        return self.state.result

    def start_turn(self):
        self.state.start_player_turn()

    def play_card(self, hand_index: int, target_idx: int | None = None):
        self.state.play_card(hand_index, target_idx)

    def end_turn(self):
        self.state.end_turn()

    def enemy_act(self):
        self.state.enemy_turn()

    def update(self, dt: float):
        self.state.update(dt)

    def pop_events(self):
        return self.state.pop_events()

    @property
    def scry_pending(self):
        return self.state.scry_pending

    def apply_scry_order(self, cards):
        return self.state.apply_scry_order(cards)
