from __future__ import annotations

import json
import os
from pathlib import Path

import pygame

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.main import App
from game.audio.audio_engine import get_audio_engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa_visual_runtime_fullhd.txt"


def _advance_scenefusion(app: App, seconds: float = 5.0):
    t = 0.0
    while t < seconds:
        cur = app.sm.current
        if cur is None or cur.__class__.__name__ != "SceneFusionScreen":
            break
        cur.update(0.25)
        t += 0.25


def _render_current(app: App, tag: str, surface: pygame.Surface) -> tuple[str, str]:
    cur = app.sm.current
    if cur is None:
        return ("FAIL", f"{tag}: no_current_screen")
    name = cur.__class__.__name__
    try:
        cur.render(surface)
        return ("PASS", f"{tag}: {name} rendered {surface.get_width()}x{surface.get_height()}")
    except Exception as ex:
        return ("FAIL", f"{tag}: {name} render_error={type(ex).__name__}: {ex}")


def _pick_available_node(app: App, allowed: set[str]) -> dict | None:
    run = app.run_state if isinstance(app.run_state, dict) else {}
    for col in list(run.get("map", []) or []):
        if not isinstance(col, list):
            continue
        for node in col:
            if not isinstance(node, dict):
                continue
            if str(node.get("state", "")).lower() != "available":
                continue
            if str(node.get("type", "")).lower() in allowed:
                return node
    return None


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()
    app.start_run_with_deck(["strike", "defend"] * 15)

    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    checks: list[tuple[str, str]] = []

    # 1) Hologram transition layer
    app._show_hologram_transition(
        title="QA Holograma",
        dialogue="Prueba de escena holografica Full HD",
        lore_line="Capa narrativa activa",
        next_fn=lambda: app.goto_map(),
        speaker="CHAKANA",
        portrait_key="chakana_mage_portrait",
        biome_layer="kaypacha",
        auto_seconds=1.8,
    )
    checks.append(_render_current(app, "hologram_transition", surface))
    _advance_scenefusion(app, 3.0)

    # 2) Map render
    app.goto_map()
    _advance_scenefusion(app, 3.5)
    checks.append(_render_current(app, "map_screen", surface))

    # 3) Codex render
    app.goto_codex()
    checks.append(_render_current(app, "codex_screen", surface))

    # 4) Combat render
    app.goto_map()
    _advance_scenefusion(app, 3.5)
    node = _pick_available_node(app, {"combat", "challenge", "elite"})
    if node is None:
        checks.append(("WARNING", "combat_screen: no available combat node found"))
    else:
        app.select_map_node(node)
        _advance_scenefusion(app, 3.5)
        checks.append(_render_current(app, "combat_screen", surface))

    # 5) Audio runtime mapping sanity
    engine = get_audio_engine()
    audio_ok = True
    audio_notes = []
    contexts = ["menu", "map_ukhu", "combat", "combat_boss", "shop", "victory", "defeat"]
    for ctx in contexts:
        p = engine._ensure_bgm_variant(ctx, "a", force=False)
        exists = bool(p and Path(p).exists())
        audio_notes.append(f"{ctx}=>{Path(p).name if p else 'missing'} exists={exists}")
        audio_ok = audio_ok and exists
    checks.append(("PASS" if audio_ok else "WARNING", "audio_runtime: " + " | ".join(audio_notes)))

    fails = sum(1 for s, _ in checks if s == "FAIL")
    warns = sum(1 for s, _ in checks if s == "WARNING")
    overall = "PASS" if fails == 0 and warns == 0 else "WARNING" if fails == 0 else "FAIL"

    lines = [
        "CHAKANA - QA VISUAL RUNTIME FULLHD",
        "=" * 40,
        f"overall={overall}",
        "",
        "Checks",
    ]
    for st, msg in checks:
        lines.append(f"- {st}: {msg}")

    lines += [
        "",
        "Summary",
        f"- pass={sum(1 for s, _ in checks if s == 'PASS')}",
        f"- warning={warns}",
        f"- fail={fails}",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"overall": overall, "report": str(OUT.name), "checks": len(checks)}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
