from __future__ import annotations

from dataclasses import dataclass


class Action:
    def resolve(self, state) -> bool:
        return True


@dataclass
class DealDamage(Action):
    source: object
    target: object
    amount: int

    def resolve(self, state) -> bool:
        state.deal_damage(self.source, self.target, self.amount)
        return True


@dataclass
class GainBlock(Action):
    target: object
    amount: int

    def resolve(self, state) -> bool:
        state.gain_block(self.target, self.amount)
        return True


@dataclass
class GainEnergy(Action):
    amount: int

    def resolve(self, state) -> bool:
        state.player["energy"] += self.amount
        return True


@dataclass
class DrawCards(Action):
    n: int

    def resolve(self, state) -> bool:
        state.draw(self.n)
        return True


@dataclass
class ApplyStatus(Action):
    target: object
    name: str
    stacks: int

    def resolve(self, state) -> bool:
        state.apply_status(self.target, self.name, self.stacks)
        return True


@dataclass
class RemoveStatus(Action):
    target: object
    name: str
    stacks: int | None = None

    def resolve(self, state) -> bool:
        state.remove_status(self.target, self.name, self.stacks)
        return True


@dataclass
class ModifyStat(Action):
    entity: object
    stat: str
    delta: int

    def resolve(self, state) -> bool:
        if self.entity == "player":
            state.player[self.stat] = max(0, state.player.get(self.stat, 0) + self.delta)
        return True


@dataclass
class ExhaustCard(Action):
    card_instance: object

    def resolve(self, state) -> bool:
        state.exhaust_card(self.card_instance)
        return True


@dataclass
class DiscardCard(Action):
    card_instance: object

    def resolve(self, state) -> bool:
        state.discard_card(self.card_instance)
        return True


class ActionQueue:
    def __init__(self):
        self.queue: list[Action] = []

    def push(self, action: Action):
        self.queue.append(action)

    def extend(self, actions: list[Action]):
        self.queue.extend(actions)

    def update(self, state):
        if self.queue:
            done = self.queue[0].resolve(state)
            if done:
                self.queue.pop(0)
