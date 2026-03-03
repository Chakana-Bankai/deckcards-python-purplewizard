from __future__ import annotations

import traceback


class QARunner:
    def __init__(self, app):
        self.app = app

    def _ok(self, name: str, detail: str = ""):
        return {"name": name, "status": "PASS", "detail": detail}

    def _fail(self, name: str, exc: Exception):
        return {"name": name, "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()}

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
            self.app.current_combat.result = "victory"
            self.app.sm.current.update(0.016)
            results.append(self._ok("combat_to_reward"))
        except Exception as exc:
            results.append(self._fail("combat_to_reward", exc))

        try:
            if hasattr(self.app.sm.current, "take") and getattr(self.app.sm.current, "reward_cards", []):
                self.app.sm.current.take(0)
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
