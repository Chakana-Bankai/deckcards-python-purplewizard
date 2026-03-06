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
    def draw_pile(self):
        return self.get_draw_pile()

    @property
    def discard_pile(self):
        return self.get_discard_pile()

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

    def apply_scry_keep(self, keep_card):
        return self.state.apply_scry_keep(keep_card)

    def activate_harmony_seal(self):
        return self.state.activate_harmony_seal()

    def _first_seq_attr(self, candidates):
        for name in candidates:
            v = getattr(self.state, name, None)
            if isinstance(v, (list, tuple)):
                return list(v)
        return []

    def get_draw_pile(self):
        return self._first_seq_attr(["draw_pile", "draw", "deck", "pile_draw", "robo", "pila_robo"])

    def get_discard_pile(self):
        return self._first_seq_attr(["discard_pile", "discard", "graveyard", "cementerio", "pila_descarte"])

    def pile_counts(self) -> dict:
        hand = getattr(self.state, "hand", None)
        hand_n = len(hand) if isinstance(hand, (list, tuple)) else 0
        return {"draw": len(self.get_draw_pile()), "hand": hand_n, "discard": len(self.get_discard_pile())}

