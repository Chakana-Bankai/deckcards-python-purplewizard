from __future__ import annotations

import json
import os
import re
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.main import App
from game.combat.combat_state import CombatState
from game.ui.screens.combat import CombatScreen


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _first_enemy_id(app: App) -> str:
    for e in list(getattr(app, "enemies_data", []) or []):
        if isinstance(e, dict) and e.get("id"):
            return str(e["id"])
    return "dummy"


def _source_checks() -> dict:
    src = Path("game/ui/screens/combat.py").read_text(encoding="utf-8")
    checks = {
        "enemy_avatar_capped_to_28_percent": "avatar_h = max(52, int(panel.h * 0.28))" in src,
        "enemy_intent_block_status_compact_layout": all(k in src for k in ["intent_line = pygame.Rect", "block_line = pygame.Rect", "status_line = pygame.Rect"]),
        "enemy_status_tokens_clipped": "clip_limit = status_line.right - 74" in src,
        "player_row3_min_height_guard": "if row3_h < 52:" in src,
        "harmony_seal_inside_harmony_core": "self.harmony_seal_rect = pygame.Rect(hr.centerx" in src,
    }
    return checks


def _runtime_render_check(app: App) -> tuple[bool, dict]:
    app.start_run_with_deck(["strike", "defend"] * 15)
    state = CombatState(
        app.rng,
        app.run_state,
        [_first_enemy_id(app)],
        cards_data=app._combat_card_catalog(),
        enemies_data=app.enemies_data,
    )
    screen = CombatScreen(app, state, is_boss=False)
    surface = pygame.Surface((1920, 1080))
    ok = True
    err = ""
    try:
        screen.update(0.016)
        screen.render(surface)
    except Exception as exc:
        ok = False
        err = repr(exc)

    details = {
        "render_ok": ok,
        "error": err,
        "end_turn_rect": [int(screen.end_turn_rect.x), int(screen.end_turn_rect.y), int(screen.end_turn_rect.w), int(screen.end_turn_rect.h)],
        "harmony_seal_rect": [int(screen.harmony_seal_rect.x), int(screen.harmony_seal_rect.y), int(screen.harmony_seal_rect.w), int(screen.harmony_seal_rect.h)],
        "harmony_rect": [int(screen.layout.harmony_rect.x), int(screen.layout.harmony_rect.y), int(screen.layout.harmony_rect.w), int(screen.layout.harmony_rect.h)],
        "playerhud_rect": [int(screen.layout.playerhud_rect.x), int(screen.layout.playerhud_rect.y), int(screen.layout.playerhud_rect.w), int(screen.layout.playerhud_rect.h)],
    }
    return ok, details


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()

    src_checks = _source_checks()
    rt_ok, rt_details = _runtime_render_check(app)

    checks = dict(src_checks)
    checks["combat_screen_runtime_render"] = rt_ok

    overall = "PASS" if all(checks.values()) else "FAIL"
    lines = [
        "PHASE 6 - COMBAT HUD POLISH REPORT",
        "=" * 40,
        f"overall={overall}",
        "",
        "Checks",
    ]
    for k, v in checks.items():
        lines.append(f"- {k}: {_status(v)}")
    lines.extend([
        "",
        "Runtime details",
        f"- {json.dumps(rt_details, ensure_ascii=False)}",
    ])
    Path("combat_hud_polish_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"overall": overall, "checks": {k: _status(v) for k, v in checks.items()}, "report": "combat_hud_polish_report.txt"}


if __name__ == "__main__":
    out = run()
    print("[qa_phase6] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))
