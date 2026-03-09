from __future__ import annotations

import json
import os
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.main import App
from game.ui.screens.codex import CodexScreen
from game.ui.screens.pack_opening import PackOpeningScreen
from game.ui.screens.reward import RewardScreen
from game.ui.screens.shop import ShopScreen


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()
    app.start_run_with_deck(["strike", "defend"] * 15)

    app.goto_reward(gold=33)
    current = app.sm.current
    reward_primary_pack = isinstance(current, PackOpeningScreen) and not isinstance(current, RewardScreen)

    pack_screen = current if isinstance(current, PackOpeningScreen) else PackOpeningScreen(app)
    pack_ids = [str(x.get("id", "")) for x in list(getattr(pack_screen, "pack_defs", []) or [])]
    pack_types_ok = all(x in pack_ids for x in ["base_pack", "hiperborea_pack", "mystery_pack"])

    shop = ShopScreen(app, app.cards_data[0] if app.cards_data else {"id": "strike"})
    shop_has_pack = bool(hasattr(shop, "pack_offer") and hasattr(shop, "buy_pack_btn"))

    # Codex visibility: Hiperborea tab should exist even before unlock.
    app.run_state["discovered_sets"] = ["base"]
    codex = CodexScreen(app)
    surface = pygame.Surface((1920, 1080))
    codex.active_section_id = "cards"
    codex.render(surface)
    codex_tabs = [tid for _r, tid in list(getattr(codex, "card_tab_rects", []) or [])]
    codex_has_hip_tab = "hiperborea" in codex_tabs

    # Hiperborea registry integration.
    app.run_state["discovered_sets"] = ["base", "hiperboria"]
    app.run_state["hiperboria_unlocked"] = True
    reward_pool = list(app._reward_card_pool() or [])
    reward_pool_has_hip = any(
        str(c.get("id", "")).lower().startswith("hip_")
        or "hiperboria" in str(c.get("set", "")).lower()
        or "hiperborea" in str(c.get("set", "")).lower()
        for c in reward_pool
        if isinstance(c, dict)
    )

    checks = {
        "legacy_pack_modal_replaced_as_primary": reward_primary_pack,
        "pack_object_flow_types": pack_types_ok,
        "shop_supports_cards_relics_packs": shop_has_pack,
        "hiperborea_visible_in_codex": codex_has_hip_tab,
        "hiperborea_connected_to_reward_pool": reward_pool_has_hip,
    }

    overall = "PASS" if all(checks.values()) else "FAIL"
    lines = [
        "CHAKANA PHASE 2 - PACK/SHOP/HIPERBOREA INTEGRATION REPORT",
        "=" * 64,
        f"overall={overall}",
        "",
        "Checks",
    ]
    for k, v in checks.items():
        lines.append(f"- {k}: {_status(v)}")
    lines.extend([
        "",
        "Details",
        f"- current_reward_screen={type(current).__name__ if current else 'None'}",
        f"- pack_ids={pack_ids}",
        f"- codex_tabs={codex_tabs}",
        f"- reward_pool_total={len(reward_pool)}",
        f"- reward_pool_has_hip={reward_pool_has_hip}",
    ])

    report = Path("pack_shop_integration_report.txt")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {"overall": overall, "checks": {k: _status(v) for k, v in checks.items()}, "report": str(report)}
    return payload


if __name__ == "__main__":
    out = run()
    print("[qa_phase2] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))
