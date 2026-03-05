"""QA smoke runner used by F8/F10 debug shortcuts."""

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


    def _claim_first_reward_if_present(self) -> bool:
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


    def _qa_pack_flow(self):
        from game.ui.screens.pack_opening import PackOpeningScreen

        screen = PackOpeningScreen(self.app)
        before = len(self.app.run_state.get("sideboard", []))
        screen._open_pack(0)
        if screen.legendary_pick_mode:
            screen.selected_card = screen.cards[0] if screen.cards else None
        screen._confirm()
        after = len(self.app.run_state.get("sideboard", []))
        gained = max(0, after - before)
        expected = 1 if screen.legendary_pick_mode else 5
        if gained < expected:
            raise RuntimeError(f"pack_flow expected>={expected} gained={gained}")
        return {"legendary_mode": screen.legendary_pick_mode, "gained": gained}

    def _qa_scry_modal_flow(self):
        from game.combat.card import CardDef, CardInstance
        from game.ui.components.modal_card_picker import ModalCardPicker

        sample_defs = [c for c in self.app.cards_data[:3] if isinstance(c, dict)]
        cards = [CardInstance(CardDef(**c)) for c in sample_defs] if sample_defs else []
        chosen = {"card": None}
        picker = ModalCardPicker()
        picker.show(cards, on_confirm=lambda c: chosen.__setitem__("card", c), required_selections=1)
        if cards:
            picker.selected_index = 0
            picker._confirm()
        else:
            picker._cancel()
        return chosen["card"] is not None or not cards

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
            self._force_combat_victory()
            self._claim_first_reward_if_present()
            self.app.goto_map()
            results.append(self._ok("qa_f8_return_map"))

            pack_info = self._qa_pack_flow()
            results.append(self._ok("qa_f8_pack_open", f"gained={pack_info['gained']} legendary={pack_info['legendary_mode']}"))

            self.app.goto_deck()
            ds = self.app.sm.current
            if hasattr(ds, "main_scroll"):
                ds.main_scroll = max(0, len(self.app.run_state.get("deck", [])) - 5)
            results.append(self._ok("qa_f8_deck_scroll"))
            self.app.goto_map()

            if self._qa_scry_modal_flow():
                results.append(self._ok("qa_f8_scry_modal"))
            else:
                results.append(self._fail("qa_f8_scry_modal", RuntimeError("scry modal failed")))
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
            self._force_combat_victory()
            self.app.sm.current.update(0.016)
            results.append(self._ok("combat_to_reward"))
        except Exception as exc:
            results.append(self._fail("combat_to_reward", exc))

        try:
            self._claim_first_reward_if_present()
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
