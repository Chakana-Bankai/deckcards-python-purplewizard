from __future__ import annotations

import json
import os
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.main import App
from game.ui.screens.scene_fusion import SceneFusionScreen
from game.ui.screens.event import EventScreen
from game.systems.event_system import enrich_event_payload, apply_event_state_flags, classify_event, event_tags


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _advance_until_event(app: App, steps: int = 40, dt: float = 0.12) -> bool:
    for _ in range(max(1, steps)):
        cur = app.sm.current
        if isinstance(cur, EventScreen):
            return True
        if cur is None:
            return False
        cur.update(dt)
    return isinstance(app.sm.current, EventScreen)


def run() -> dict:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    app = App()
    app.ensure_boot_content_ready()
    app.start_run_with_deck(["strike", "defend"] * 15)

    # Phase 3B runtime: event should route through hologram transition first.
    app.goto_event()
    starts_with_hologram = isinstance(app.sm.current, SceneFusionScreen)
    enters_event_screen = _advance_until_event(app)
    current = app.sm.current

    event_payload = dict(getattr(current, "event", {}) if isinstance(current, EventScreen) else {})
    payload_has_type = isinstance(event_payload.get("event_type"), str) and bool(event_payload.get("event_type"))
    payload_has_tags = isinstance(event_payload.get("tags"), list) and len(event_payload.get("tags", [])) > 0
    payload_has_speaker = bool(event_payload.get("speaker_label")) and bool(event_payload.get("portrait_key"))

    # Validate helper mapping and tags coverage.
    mapped_types = {
        "apacheta_offer": classify_event("apacheta_offer"),
        "ayni_pact": classify_event("ayni_pact"),
        "serpent_shed": classify_event("serpent_shed"),
    }
    tags_ok = all(len(event_tags(v)) >= 1 for v in mapped_types.values())

    # Conditional rewards/state flags support.
    rs = app.run_state
    effects = [
        {"type": "set_next_combat_bonus", "amount": 2},
        {"type": "set_next_shop_discount", "amount": 15},
        {"type": "set_next_shop_pack_reveal", "pack": "hiperborea_pack"},
        {"type": "unlock_hiperborea_entry"},
    ]
    applied_count = sum(1 for ef in effects if apply_event_state_flags(rs, ef))
    flags = dict((rs or {}).get("event_flags", {}) or {})
    conditional_flags_ok = (
        applied_count == len(effects)
        and int(flags.get("next_combat_bonus", 0)) == 2
        and int(flags.get("next_shop_discount", 0)) == 15
        and str(flags.get("next_shop_pack_reveal", "")) == "hiperborea_pack"
        and bool(flags.get("unlock_hiperborea_entry", False))
    )

    checks = {
        "event_node_routes_hologram_then_event_screen": starts_with_hologram and enters_event_screen,
        "event_payload_has_type_tags_speaker": payload_has_type and payload_has_tags and payload_has_speaker,
        "event_type_mapping_and_tags_available": tags_ok,
        "conditional_event_flags_supported": conditional_flags_ok,
    }

    overall = "PASS" if all(checks.values()) else "FAIL"

    refactor_lines = [
        "CHAKANA PHASE 3B - EVENT NODE REFACTOR REPORT",
        "=" * 58,
        f"overall={overall}",
        "",
        "Checks",
    ]
    for k, v in checks.items():
        refactor_lines.append(f"- {k}: {_status(v)}")
    refactor_lines.extend([
        "",
        "Details",
        f"- starts_with_hologram={starts_with_hologram}",
        f"- enters_event_screen={enters_event_screen}",
        f"- payload_event_type={event_payload.get('event_type', '')}",
        f"- payload_tags={event_payload.get('tags', [])}",
        f"- payload_speaker={event_payload.get('speaker_label', '')}",
        f"- payload_portrait={event_payload.get('portrait_key', '')}",
        f"- mapped_types={json.dumps(mapped_types, ensure_ascii=False)}",
        f"- event_flags={json.dumps(flags, ensure_ascii=False)}",
    ])
    Path("event_node_refactor_report.txt").write_text("\n".join(refactor_lines) + "\n", encoding="utf-8")

    design_lines = [
        "CHAKANA PHASE 3B - EVENT SYSTEM DESIGN REPORT",
        "=" * 57,
        "Design decisions",
        "- Event node flow: Map node -> SceneFusion hologram -> EventScreen decision modal.",
        "- Event payload enrichment: event_type, tags, speaker_label, portrait_key, alignment.",
        "- Reward philosophy: events favor conditional/small rewards; major rewards remain combat/shop/pack.",
        "- Conditional event flags supported:",
        "  - set_next_combat_bonus",
        "  - set_next_shop_discount",
        "  - set_temp_curse",
        "  - unlock_hiperborea_entry",
        "  - guarantee_next_elite_relic",
        "  - set_next_shop_pack_reveal",
        "- Guide/angel/demon speakers preserved through mapped speaker profiles.",
        "",
        f"overall={overall}",
    ]
    Path("event_system_design_report.txt").write_text("\n".join(design_lines) + "\n", encoding="utf-8")

    return {
        "overall": overall,
        "checks": {k: _status(v) for k, v in checks.items()},
        "reports": ["event_node_refactor_report.txt", "event_system_design_report.txt"],
    }


if __name__ == "__main__":
    out = run()
    print("[qa_phase3b] generated")
    print(json.dumps(out, ensure_ascii=False, indent=2))
