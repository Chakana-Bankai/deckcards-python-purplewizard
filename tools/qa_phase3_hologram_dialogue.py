from __future__ import annotations

import json
import os
import re
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.main import App
from game.combat.combat_state import CombatState
from game.ui.screens.scene_fusion import SceneFusionScreen


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _first_enemy_id(app: App) -> str:
    for e in list(getattr(app, "enemies_data", []) or []):
        if isinstance(e, dict) and e.get("id"):
            return str(e["id"])
    return "dummy"


def _build_combat_state(app: App) -> CombatState:
    return CombatState(
        app.rng,
        app.run_state,
        [_first_enemy_id(app)],
        cards_data=app._combat_card_catalog(),
        enemies_data=app.enemies_data,
    )


def _source_checks() -> dict:
    src = Path("game/main.py").read_text(encoding="utf-8")
    checks = {
        "main_uses_scene_fusion_screen": "SceneFusionScreen(" in src,
        "main_has_hologram_transition_helper": "def _show_hologram_transition(" in src,
        "main_no_active_pacha_transition_call": "PachaTransitionScreen(" not in src,
    }

    # Extra guard: methods should route through helper.
    checks["goto_map_uses_hologram_helper"] = bool(re.search(r"def goto_map\(self\):[\s\S]*?_show_hologram_transition\(", src))
    checks["goto_combat_uses_hologram_helper"] = bool(re.search(r"def goto_combat\(self, combat_state, is_boss=False\):[\s\S]*?_show_hologram_transition\(", src))
    checks["goto_end_uses_hologram_helper"] = bool(re.search(r"def goto_end\(self, victory=True\):[\s\S]*?_show_hologram_transition\(", src))
    return checks


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()
    app.start_run_with_deck(["strike", "defend"] * 15)

    app.last_biome_seen = None
    app.goto_map()
    map_transition_ok = isinstance(app.sm.current, SceneFusionScreen)

    app.goto_combat(_build_combat_state(app), is_boss=False)
    combat_transition_ok = isinstance(app.sm.current, SceneFusionScreen)

    app.goto_combat(_build_combat_state(app), is_boss=True)
    boss_transition_ok = isinstance(app.sm.current, SceneFusionScreen)

    app.goto_end(victory=False)
    end_transition_ok = isinstance(app.sm.current, SceneFusionScreen)

    runtime_checks = {
        "goto_map_runtime_transition_scene_fusion": map_transition_ok,
        "goto_combat_runtime_transition_scene_fusion": combat_transition_ok,
        "goto_boss_runtime_transition_scene_fusion": boss_transition_ok,
        "goto_end_runtime_transition_scene_fusion": end_transition_ok,
    }
    source_checks = _source_checks()

    all_checks = {**source_checks, **runtime_checks}
    overall = "PASS" if all(all_checks.values()) else "FAIL"

    lines = [
        "CHAKANA PHASE 3 - HOLOGRAM DIALOGUE INTEGRATION REPORT",
        "=" * 60,
        f"overall={overall}",
        "",
        "Source checks",
    ]
    for key, val in source_checks.items():
        lines.append(f"- {key}: {_status(val)}")

    lines.extend(["", "Runtime checks"])
    for key, val in runtime_checks.items():
        lines.append(f"- {key}: {_status(val)}")

    report = Path("hologram_dialogue_integration_report.txt")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "overall": overall,
        "checks": {k: _status(v) for k, v in all_checks.items()},
        "report": str(report),
    }


if __name__ == "__main__":
    out = run()
    print("[qa_phase3] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))
