from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.main import App


@dataclass
class Phase7Metrics:
    combats_for_unlock: int
    hiperboria_unlocked_after_3: bool
    discovered_sets: list[str]
    reveal_scene_seen: bool
    enemy_ids: list[str]
    enemy_unique_ratio: float
    enemy_consecutive_repeat_rate: float
    event_ids: list[str]
    event_unique_ratio: float
    event_consecutive_repeat_rate: float
    shop_has_hiperboria_pool: bool
    pack_has_hiperboria_pool: bool


def _status(ok: bool, warn: bool = False) -> str:
    if ok and not warn:
        return "PASS"
    if ok and warn:
        return "WARNING"
    return "FAIL"


def _ratio_unique(values: list[str]) -> float:
    if not values:
        return 0.0
    return len(set(values)) / float(len(values))


def _ratio_consecutive_repeats(values: list[str]) -> float:
    if len(values) <= 1:
        return 0.0
    repeats = 0
    for i in range(1, len(values)):
        if values[i] == values[i - 1]:
            repeats += 1
    return repeats / float(len(values) - 1)


def _force_scene_continue(app: App, max_seconds: float = 6.0):
    start = time.time()
    while time.time() - start < max_seconds:
        cur = app.sm.current
        if cur is None:
            break
        if cur.__class__.__name__ != "SceneFusionScreen":
            break
        cur.update(0.25)


def _claim_reward_if_present(app: App):
    cur = app.sm.current
    if cur is None:
        return
    if cur.__class__.__name__ != "RewardScreen":
        return
    mode = str(getattr(cur, "mode", ""))
    if mode == "choose1of3" and hasattr(cur, "claim"):
        cards = list(getattr(cur, "cards", []) or [])
        if cards:
            cur.claim(0)
            return
    if mode == "guide_choice":
        cur.selected_idx = 0
        cur.confirm()
        return
    if mode == "boss_pack":
        cur.confirm()


def _pick_available_node(app: App, allowed_types: set[str]) -> dict | None:
    run = app.run_state if isinstance(app.run_state, dict) else {}
    run_map = list(run.get("map", []) or [])
    chosen = None
    for col in run_map:
        if not isinstance(col, list):
            continue
        for n in col:
            if not isinstance(n, dict):
                continue
            if str(n.get("state", "")).lower() != "available":
                continue
            ntype = str(n.get("type", "")).lower()
            if ntype in allowed_types:
                return n
            if chosen is None:
                chosen = n
    return chosen


def _force_combat_victory(app: App):
    combat = getattr(app, "current_combat", None)
    if combat is None:
        return False
    state = getattr(combat, "state", None)
    if state is None:
        return False
    if getattr(state, "result", None) is not None:
        return True
    state.result = "victory"
    app.on_combat_victory()
    return True


def _run_combat(app: App, enemy_ids_out: list[str]) -> bool:
    node = _pick_available_node(app, {"combat", "challenge", "elite"})
    if not isinstance(node, dict):
        return False

    app.select_map_node(node)
    combat = getattr(app, "current_combat", None)
    if combat is None:
        return False
    enemies = list(getattr(combat, "enemies", []) or [])
    if enemies:
        enemy_ids_out.append(str(getattr(enemies[0], "id", "unknown")))

    ok = _force_combat_victory(app)
    _claim_reward_if_present(app)
    _force_scene_continue(app)
    if app.sm.current and app.sm.current.__class__.__name__ != "MapScreen":
        app.goto_map()
    return ok


def _probe_events(app: App, iterations: int = 8) -> list[str]:
    out = []
    for _ in range(iterations):
        app.goto_event()
        cur = app.sm.current
        if cur is None or cur.__class__.__name__ != "EventScreen":
            continue
        ev = getattr(cur, "event", {}) if isinstance(getattr(cur, "event", {}), dict) else {}
        eid = str(ev.get("id") or ev.get("title_key") or "event_unknown")
        out.append(eid)
        app.goto_map()
    return out


def run_phase7_extended() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()
    app.start_run_with_deck(["strike", "defend"] * 15)

    enemy_ids: list[str] = []
    reveal_seen = False

    combats_done = 0
    while combats_done < 3:
        if not _run_combat(app, enemy_ids):
            break
        combats_done += 1
        if str((app.sm.current.__class__.__name__ if app.sm.current else "")) == "SceneFusionScreen":
            reveal_seen = True
            _force_scene_continue(app)

    run = app.run_state if isinstance(app.run_state, dict) else {}
    hip_unlocked = bool(run.get("hiperboria_unlocked", False))
    discovered_sets = [str(x) for x in list(run.get("discovered_sets", []) or []) if x]

    # Extra combats for enemy variety probe (real flow).
    extra = 0
    while extra < 5:
        if not _run_combat(app, enemy_ids):
            break
        extra += 1

    event_ids = _probe_events(app, iterations=8)

    # Visibility checks in systems that consume reward pools.
    app.run_state["level"] = max(5, int(app.run_state.get("level", 1) or 1))
    from game.ui.screens.shop import ShopScreen
    from game.ui.screens.pack_opening import PackOpeningScreen

    shop = ShopScreen(app, app.cards_data[0] if app.cards_data else {"id": "strike"})
    pack = PackOpeningScreen(app)

    metrics = Phase7Metrics(
        combats_for_unlock=combats_done,
        hiperboria_unlocked_after_3=bool(hip_unlocked and combats_done >= 3),
        discovered_sets=discovered_sets,
        reveal_scene_seen=bool(reveal_seen or bool(app.pending_scene_reveal is not None) or ("hiperboria" in {x.lower() for x in discovered_sets})),
        enemy_ids=enemy_ids,
        enemy_unique_ratio=_ratio_unique(enemy_ids),
        enemy_consecutive_repeat_rate=_ratio_consecutive_repeats(enemy_ids),
        event_ids=event_ids,
        event_unique_ratio=_ratio_unique(event_ids),
        event_consecutive_repeat_rate=_ratio_consecutive_repeats(event_ids),
        shop_has_hiperboria_pool=bool(getattr(shop, "hip_pool", [])),
        pack_has_hiperboria_pool=bool(getattr(pack, "hip_pool", [])),
    )

    unlock_ok = metrics.hiperboria_unlocked_after_3
    enemy_ok = metrics.enemy_unique_ratio >= 0.40 and metrics.enemy_consecutive_repeat_rate <= 0.45
    event_ok = metrics.event_unique_ratio >= 0.35 and metrics.event_consecutive_repeat_rate <= 0.50
    visibility_ok = metrics.shop_has_hiperboria_pool and metrics.pack_has_hiperboria_pool

    summary = {
        "unlock": _status(unlock_ok),
        "enemy_variety": _status(enemy_ok, warn=not enemy_ok and metrics.enemy_unique_ratio >= 0.30),
        "event_variety": _status(event_ok, warn=not event_ok and metrics.event_unique_ratio >= 0.25),
        "hiperboria_visibility": _status(visibility_ok),
    }

    overall = "PASS"
    if "FAIL" in summary.values():
        overall = "FAIL"
    elif "WARNING" in summary.values():
        overall = "WARNING"

    return {
        "overall": overall,
        "summary": summary,
        "metrics": metrics.__dict__,
    }


def _build_text(version: str, build: str, payload: dict) -> str:
    m = payload.get("metrics", {})
    s = payload.get("summary", {})
    lines = []
    lines.append("CHAKANA - PHASE 7 EXTENDED QA")
    lines.append("=" * 44)
    lines.append(f"version={version}")
    lines.append(f"build={build}")
    lines.append(f"overall={payload.get('overall', 'WARNING')}")
    lines.append("")
    lines.append("Checks")
    lines.append(f"- unlock_after_3_combats: {s.get('unlock','WARNING')}")
    lines.append(f"- enemy_variety: {s.get('enemy_variety','WARNING')}")
    lines.append(f"- event_variety: {s.get('event_variety','WARNING')}")
    lines.append(f"- hiperboria_visibility(shop/pack): {s.get('hiperboria_visibility','WARNING')}")
    lines.append("")
    lines.append("Metrics")
    lines.append(f"- combats_for_unlock: {m.get('combats_for_unlock', 0)}")
    lines.append(f"- hiperboria_unlocked_after_3: {m.get('hiperboria_unlocked_after_3', False)}")
    lines.append(f"- discovered_sets: {m.get('discovered_sets', [])}")
    lines.append(f"- reveal_scene_seen: {m.get('reveal_scene_seen', False)}")
    lines.append(f"- enemy_ids: {m.get('enemy_ids', [])}")
    lines.append(f"- enemy_unique_ratio: {m.get('enemy_unique_ratio', 0.0):.3f}")
    lines.append(f"- enemy_consecutive_repeat_rate: {m.get('enemy_consecutive_repeat_rate', 0.0):.3f}")
    lines.append(f"- event_ids: {m.get('event_ids', [])}")
    lines.append(f"- event_unique_ratio: {m.get('event_unique_ratio', 0.0):.3f}")
    lines.append(f"- event_consecutive_repeat_rate: {m.get('event_consecutive_repeat_rate', 0.0):.3f}")
    lines.append(f"- shop_has_hiperboria_pool: {m.get('shop_has_hiperboria_pool', False)}")
    lines.append(f"- pack_has_hiperboria_pool: {m.get('pack_has_hiperboria_pool', False)}")
    lines.append("")
    return "\n".join(lines)


def generate_phase7_reports() -> tuple[dict, Path, Path]:
    version_info = load_json(data_dir() / "version.json", default={})
    version = str(version_info.get("version", "0.0.0"))
    build = str(version_info.get("build", "Unknown Build"))

    payload = run_phase7_extended()
    text = _build_text(version, build, payload)
    md = "```text\n" + text + "\n```\n"

    txt_path = Path("qa_report_phase7_extended.txt")
    md_path = Path("qa_report_phase7_extended.md")
    txt_path.write_text(text, encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    return payload, txt_path, md_path


if __name__ == "__main__":
    report, txt_path, md_path = generate_phase7_reports()
    print("[qa_phase7_extended] generated")
    print(json.dumps({"overall": report.get("overall"), "txt": str(txt_path), "md": str(md_path), "summary": report.get("summary", {})}, ensure_ascii=False, indent=2))
