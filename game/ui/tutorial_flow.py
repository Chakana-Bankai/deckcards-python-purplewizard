from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStep:
    step_id: str
    screen: str
    title: str
    lines: tuple[str, str]
    target: str


class TutorialFlowController:
    """Guided first-run tutorial state machine integrated into gameplay."""

    def __init__(self):
        self.steps = [
            TutorialStep(
                "show_cards",
                "combat",
                "Tus cartas",
                ("Estas son tus opciones del turno.", "Selecciona una carta para comenzar."),
                "hand",
            ),
            TutorialStep(
                "play_card",
                "combat",
                "Juega una carta",
                ("El costo aparece arriba de cada carta.", "Juega una para ejecutar su efecto."),
                "hand",
            ),
            TutorialStep(
                "explain_block",
                "combat",
                "Bloqueo",
                ("El BLK reduce el dano del enemigo.", "Busca subir tu BLK cuando te ataquen."),
                "player_block",
            ),
            TutorialStep(
                "enemy_intent",
                "combat",
                "Intencion enemiga",
                ("Aqui ves cuanto hara el enemigo.", "Planea tu turno segun ese valor."),
                "enemy_intent",
            ),
            TutorialStep(
                "harmony",
                "combat",
                "Armonia",
                ("La Armonia habilita poder ritual.", "Llena el umbral para activar el sello."),
                "harmony",
            ),
            TutorialStep(
                "end_turn",
                "combat",
                "Fin de turno",
                ("Cuando termines de jugar, cierra tu turno.", "Pulsa el boton central para continuar."),
                "action_button",
            ),
            TutorialStep(
                "reward_selection",
                "reward",
                "Elige recompensa",
                ("Tras vencer, toma una mejora para tu run.", "Selecciona y confirma una opcion."),
                "reward_choices",
            ),
        ]
        self._index = 0
        self.active = False
        self.completed = False
        self._entered_combat = False
        self._completed_now = False
        self._combat_turns_seen = 0

    def start_for_run(self, enabled: bool):
        self.active = bool(enabled)
        self.completed = False
        self._completed_now = False
        self._entered_combat = False
        self._combat_turns_seen = 0
        self._index = 0

    def current_step(self) -> TutorialStep | None:
        if not self.active or self.completed:
            return None
        if self._index < 0 or self._index >= len(self.steps):
            return None
        return self.steps[self._index]

    def current_hint(self, screen: str) -> dict | None:
        step = self.current_step()
        if step is None or step.screen != str(screen):
            return None
        return {
            "id": step.step_id,
            "title": step.title,
            "lines": list(step.lines),
            "target": step.target,
            "index": self._index + 1,
            "total": len(self.steps),
        }

    def on_combat_enter(self):
        if not self.active or self.completed:
            return
        self._entered_combat = True
        self._combat_turns_seen = 1

    def on_turn_advanced(self):
        if not self.active or self.completed:
            return
        self._combat_turns_seen += 1

    def on_hand_clicked(self):
        if self._current_is("show_cards"):
            self._advance()

    def on_card_played(self, is_block_card: bool, player_block: int):
        if self._current_is("play_card"):
            self._advance()
            return
        if self._current_is("explain_block") and (is_block_card or int(player_block or 0) > 0):
            self._advance()

    def on_enemy_intent_seen(self):
        if self._current_is("enemy_intent"):
            self._advance()

    def on_harmony_progress(self, harmony_current: int, harmony_ready: bool):
        if not self._current_is("harmony"):
            return
        if int(harmony_current or 0) > 0 or bool(harmony_ready) or self._combat_turns_seen >= 3:
            self._advance()

    def on_end_turn_pressed(self):
        if self._current_is("end_turn"):
            self._advance()

    def on_reward_enter(self):
        if not self.active or self.completed:
            return
        reward_idx = self._step_index("reward_selection")
        if self._index < reward_idx:
            self._index = reward_idx

    def on_reward_confirmed(self):
        if self._current_is("reward_selection"):
            self._advance()

    def manual_advance(self):
        if self.active and not self.completed:
            self._advance()

    def consume_completed(self) -> bool:
        if self._completed_now:
            self._completed_now = False
            return True
        return False

    def snapshot(self) -> dict:
        step = self.current_step()
        return {
            "active": bool(self.active and not self.completed),
            "completed": bool(self.completed),
            "step_id": step.step_id if step else "",
            "step_index": int(self._index),
            "step_total": len(self.steps),
        }

    def _current_is(self, step_id: str) -> bool:
        step = self.current_step()
        return bool(step and step.step_id == step_id)

    def _step_index(self, step_id: str) -> int:
        for idx, step in enumerate(self.steps):
            if step.step_id == step_id:
                return idx
        return len(self.steps) - 1

    def _advance(self):
        if not self.active or self.completed:
            return
        self._index += 1
        if self._index >= len(self.steps):
            self._index = len(self.steps) - 1
            self.completed = True
            self.active = False
            self._completed_now = True
