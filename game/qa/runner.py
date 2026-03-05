<<<<<<< ours
<<<<<<< ours
=======
"""QA smoke runner used by F8/F10 debug shortcuts."""

>>>>>>> theirs
=======
"""QA smoke runner used by F8/F10 debug shortcuts."""

>>>>>>> theirs
from __future__ import annotations

import os
import traceback


class QARunner:
    def __init__(self, app):
        self.app = app

    def _ok(self, name: str, detail: str = ""):
        return {"name": name, "status": "PASS", "detail": detail}

    def _fail(self, name: str, exc: Exception):
        return {"name": name, "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()}

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
=======

    def _claim_first_reward_if_present(self):
=======

    def _claim_first_reward_if_present(self) -> bool:
>>>>>>> theirs
=======

    def _claim_first_reward_if_present(self) -> bool:
>>>>>>> theirs
        screen = getattr(self.app.sm, "current", None)
        if screen is None or screen.__class__.__name__ != "RewardScreen":
            return False
        picks = getattr(screen, "picks", [])
        if not picks:
            return False
        if hasattr(screen, "claim"):
            screen.claim(0)
            return True
        self.app.run_state["sideboard"].append(picks[0].definition.id)
        self.app.goto_map()
        return True

<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
=======
>>>>>>> theirs

    def _force_combat_victory(self) -> bool:
        combat = getattr(self.app, "current_combat", None)
        if combat is None or getattr(combat, "result", None) is not None:
            return False
        if hasattr(combat, "state"):
            combat.state.result = "victory"
        else:
            combat.result = "victory"
        self.app.on_combat_victory()
        return True

<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
    def run_combat_scripted_smoke(self):
        results = []
        try:
            if not self.app.run_state:
                self.app.start_run_with_deck(["strike", "defend"] * 5)
            n = self.app.run_state["map"][0][0]
            self.app.select_map_node(n)
            results.append(self._ok("qa_f8_enter_combat"))
            played = 0
            for _ in range(10):
                cs = self.app.current_combat
                if not cs or cs.result is not None:
                    break
                if cs.hand:
                    idx = 0
                    try:
                        cs.play_card(idx, 0)
                        played += 1
                    except Exception:
                        cs.end_turn()
                else:
                    cs.end_turn()
                cs.update(0.016)
            results.append(self._ok("qa_f8_play_cards", f"played={played}"))
<<<<<<< ours
<<<<<<< ours
            if self.app.current_combat and self.app.current_combat.result is None:
                self.app.current_combat.result = "victory"
                self.app.on_combat_victory()
<<<<<<< ours
            if self.app.sm.current.__class__.__name__ == "RewardScreen":
<<<<<<< ours
<<<<<<< ours
                if getattr(self.app.sm.current, "picks", None):
                    self.app.sm.current.picks and self.app.sm.current.picks[0:1]
                    if hasattr(self.app.sm.current, "picks") and self.app.sm.current.picks:
                        self.app.run_state["sideboard"].append(self.app.sm.current.picks[0].definition.id)
=======
=======
>>>>>>> theirs
                picks = getattr(self.app.sm.current, "picks", [])
                if picks:
                    if hasattr(self.app.sm.current, "claim"):
                        self.app.sm.current.claim(0)
                    else:
                        self.app.run_state["sideboard"].append(picks[0].definition.id)
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
                        self.app.goto_map()
=======
            self._claim_first_reward_if_present()
>>>>>>> theirs
=======
            self._force_combat_victory()
            self._claim_first_reward_if_present()
>>>>>>> theirs
=======
            self._force_combat_victory()
            self._claim_first_reward_if_present()
>>>>>>> theirs
            self.app.goto_map()
            results.append(self._ok("qa_f8_return_map"))
        except Exception as exc:
            results.append(self._fail("qa_f8_smoke", exc))
        return results

    def run_all(self):
        results = []
        try:
            self.app.validate_navigation_methods()
            results.append(self._ok("validate_navigation_methods"))
        except Exception as exc:
            results.append(self._fail("validate_navigation_methods", exc))
            return results

        try:
            self.app.start_run_with_deck(["strike", "defend"] * 5)
            results.append(self._ok("start_run"))
        except Exception as exc:
            results.append(self._fail("start_run", exc)); return results

        try:
            n = self.app.run_state["map"][0][0]
            self.app.select_map_node(n)
            results.append(self._ok("enter_combat"))
        except Exception as exc:
            results.append(self._fail("enter_combat", exc)); return results

        try:
<<<<<<< ours
<<<<<<< ours
            self.app.current_combat.result = "victory"
=======
            self._force_combat_victory()
>>>>>>> theirs
=======
            self._force_combat_victory()
>>>>>>> theirs
            self.app.sm.current.update(0.016)
            results.append(self._ok("combat_to_reward"))
        except Exception as exc:
            results.append(self._fail("combat_to_reward", exc))

        try:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            if hasattr(self.app.sm.current, "take") and getattr(self.app.sm.current, "reward_cards", []):
                self.app.sm.current.take(0)
=======
            if hasattr(self.app.sm.current, "claim") and getattr(self.app.sm.current, "picks", []):
                self.app.sm.current.claim(0)
>>>>>>> theirs
=======
            if hasattr(self.app.sm.current, "claim") and getattr(self.app.sm.current, "picks", []):
                self.app.sm.current.claim(0)
>>>>>>> theirs
=======
            self._claim_first_reward_if_present()
>>>>>>> theirs
=======
            self._claim_first_reward_if_present()
>>>>>>> theirs
=======
            self._claim_first_reward_if_present()
>>>>>>> theirs
            results.append(self._ok("reward_to_map"))
        except Exception as exc:
            results.append(self._fail("reward_to_map", exc))

        try:
            self.app.goto_shop()
            results.append(self._ok("goto_shop"))
            if hasattr(self.app.sm.current, "buy"):
                self.app.sm.current.buy()
            self.app.goto_event()
            results.append(self._ok("goto_event"))
            self.app.goto_deck()
            results.append(self._ok("goto_deck"))
            self.app.goto_map()
            results.append(self._ok("back_to_map"))
        except Exception as exc:
            results.append(self._fail("mid_flow", exc))

        try:
            self.app.enter_node({"type": "boss"})
            results.append(self._ok("enter_boss"))
        except Exception as exc:
            results.append(self._fail("enter_boss", exc))
        return results


def run_smoke_tests() -> int:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from game.main import App

    app = App()
    results = QARunner(app).run_all()
    for result in results:
        detail = f" - {result['detail']}" if result.get("detail") else ""
        print(f"[{result['status']}] {result['name']}{detail}")
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(run_smoke_tests())
