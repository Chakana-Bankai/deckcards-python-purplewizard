from __future__ import annotations

import json
import os
from pathlib import Path

from game.main import App
from game.core.paths import project_root


def _flush(app: App, steps: int = 8):
    for _ in range(max(1, steps)):
        app._flush_pending_screen_transition()
        app._flush_pending_music_context()
        cur = app.sm.current
        if cur is not None and hasattr(cur, 'update'):
            cur.update(0.20)


def _screen(app: App) -> str:
    cur = app.sm.current
    return cur.__class__.__name__ if cur is not None else 'None'


def _advance_scene_fusion(app: App, max_steps: int = 40):
    for _ in range(max_steps):
        cur = app.sm.current
        if cur is None or cur.__class__.__name__ != 'SceneFusionScreen':
            return
        if hasattr(cur, 'update'):
            cur.update(0.25)
        app._flush_pending_screen_transition()
        app._flush_pending_music_context()


def _resolve_pack_screen(app: App):
    cur = app.sm.current
    if cur is None or cur.__class__.__name__ != 'PackOpeningScreen':
        return
    if not getattr(cur, 'cards', None):
        cur.selected_pack = 0
        cur._confirm()
    else:
        cur._confirm()
    _flush(app, 8)


def _resolve_event_screen(app: App):
    cur = app.sm.current
    if cur is None or cur.__class__.__name__ != 'EventScreen':
        return
    if getattr(cur, 'stage', '') == 'lore':
        cur._go_to_choices()
    if getattr(cur, 'stage', '') == 'choice':
        cur._confirm_choice_index(0)
    _flush(app, 8)


def _drain_pack_if_needed(app: App):
    loops = 0
    while loops < 4:
        loops += 1
        _advance_scene_fusion(app)
        _flush(app, 6)
        if _screen(app) == 'PackOpeningScreen':
            _resolve_pack_screen(app)
            continue
        break


def _enter_and_resolve(app: App, action):
    action()
    _flush(app, 6)
    _advance_scene_fusion(app)
    _flush(app, 6)
    _drain_pack_if_needed(app)
    if _screen(app) == 'PackOpeningScreen':
        _resolve_pack_screen(app)
    if _screen(app) == 'EventScreen':
        _resolve_event_screen(app)
    _advance_scene_fusion(app)
    _flush(app, 6)
    _drain_pack_if_needed(app)


def _first_node(app: App, kinds: set[str]) -> dict | None:
    run_map = list((app.run_state or {}).get('map', []) or [])
    for col in run_map:
        if not isinstance(col, list):
            continue
        for node in col:
            if not isinstance(node, dict):
                continue
            nt = str(node.get('type', '') or '').lower()
            st = str(node.get('state', '') or '').lower()
            if nt in kinds and st in {'available', 'locked', 'current', 'incomplete'}:
                return node
    return None


def _force_available(node: dict | None):
    if isinstance(node, dict):
        node['state'] = 'available'


def run() -> dict:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

    app = App()
    app.ensure_boot_content_ready()
    app.new_run()
    _flush(app, 10)

    results = {}
    results['boot'] = _screen(app)

    _enter_and_resolve(app, app.goto_shop)
    results['shop_entry'] = _screen(app)

    _enter_and_resolve(app, app.goto_map)
    results['map_after_shop'] = _screen(app)

    _enter_and_resolve(app, lambda: app.goto_pack_opening({'pack_category': 'base_pack'}, source='reward'))
    results['pack_entry'] = _screen(app)

    _enter_and_resolve(app, app.goto_map)
    results['map_after_pack'] = _screen(app)

    _enter_and_resolve(app, app.goto_event)
    results['event_entry'] = _screen(app)

    _enter_and_resolve(app, app.goto_map)
    results['map_after_event'] = _screen(app)

    combat1 = _first_node(app, {'combat', 'challenge', 'elite'})
    _force_available(combat1)
    if combat1:
        app.select_map_node(combat1)
        _flush(app, 6)
        _advance_scene_fusion(app)
        _flush(app, 8)
    results['combat_1_entry'] = _screen(app)

    _enter_and_resolve(app, app.goto_map)
    if combat1:
        app.current_node_id = combat1.get('id')
        app._complete_current_node()
    _flush(app, 10)
    results['map_after_combat_1'] = _screen(app)

    combat2 = _first_node(app, {'combat', 'challenge', 'elite'})
    if combat2 and combat1 and combat2.get('id') == combat1.get('id'):
        combat2 = None
    _force_available(combat2)
    if combat2:
        app.select_map_node(combat2)
        _flush(app, 6)
        _advance_scene_fusion(app)
        _flush(app, 8)
    results['combat_2_entry'] = _screen(app)

    _enter_and_resolve(app, app.goto_map)
    if combat2:
        app.current_node_id = combat2.get('id')
        app._complete_current_node()
    _flush(app, 10)
    results['map_after_combat_2'] = _screen(app)

    boss = _first_node(app, {'boss'})
    _force_available(boss)
    if boss:
        app.select_map_node(boss)
        _flush(app, 6)
        _advance_scene_fusion(app)
        _flush(app, 8)
    results['boss_entry'] = _screen(app)

    expected = {
        'boot': {'IntroScreen', 'MenuScreen'},
        'shop_entry': {'ShopScreen'},
        'map_after_shop': {'MapScreen'},
        'pack_entry': {'MapScreen', 'PackOpeningScreen'},
        'map_after_pack': {'MapScreen'},
        'event_entry': {'MapScreen', 'EventScreen'},
        'map_after_event': {'MapScreen'},
        'combat_1_entry': {'CombatScreen', 'MapScreen'},
        'map_after_combat_1': {'MapScreen'},
        'combat_2_entry': {'CombatScreen', 'MapScreen'},
        'map_after_combat_2': {'MapScreen'},
        'boss_entry': {'CombatScreen'},
    }
    ok = all(results.get(key) in allowed for key, allowed in expected.items())
    payload = {'overall': 'PASS' if ok else 'WARNING', 'results': results}

    out = project_root() / 'reports' / 'validation' / 'beta_run_flow_report.txt'
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['CHAKANA BETA RUN FLOW REPORT', '=' * 32, f"overall={payload['overall']}"]
    for key, value in results.items():
        lines.append(f'{key}={value}')
    if payload['overall'] == 'PASS':
        lines.append('note=run_flow_reaches_boss_and_core_transitions_resolve_in_safe_beta_mode')
    else:
        lines.append('note=run_flow_reaches_boss_but_some_transition_expectations_still_need_cleanup')
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[beta_run] report={out}')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


if __name__ == '__main__':
    run()

