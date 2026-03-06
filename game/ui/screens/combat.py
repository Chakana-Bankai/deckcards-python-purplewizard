from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.combat.play_validation import can_play_card, can_play, reason_to_es, REASON_OK
from game.ui.anim import TypewriterBanner
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.mana_orbs import ManaOrbsWidget
from game.ui.components.modal_card_picker import ModalCardPicker
from game.ui.controllers.card_interaction import CardInteractionController
from game.ui.controllers.combat_dialogue_controller import CombatDialogueController
from game.ui.controllers.dialogue_router import DialogueRouter
from game.ui.layout.combat_layout import build_combat_layout
from game.ui.theme import UI_THEME
from game.ui.components.topbar import CombatTopBar
from game.ui.components.pixel_icons import draw_icon_with_value
from game.telemetry.logger import TelemetryLogger


DEBUG_UI = True


def wrap_text(font, text, width, max_lines=None):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if font.size(nxt)[0] <= width:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(1, len(lines[-1]) - 3)] + "..."
    return lines


class CombatScreen:
    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.ctrl = CardInteractionController()
        self.mana_orbs = ManaOrbsWidget()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0.0
        self.enemy_line_fx = 0.0
        self.hero_line_fx = 0.0
        self.resolving_t = 0.0
        self.last_turn = self.c.turn
        run_biome = self.app.run_state.get("biome") if isinstance(self.app.run_state, dict) else None
        self.selected_biome = str(run_biome or self.app.rng.choice(self.app.bg_gen.BIOMES))
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self.pause_open = False
        self.pause_confirm_target = None
        self.hover_card_index = None
        self.dialog_debug_overlay = False
        self.qa_debug_overlay = False
        self.art_debug_overlay = False
        self.last_trigger = "combat_start"
        self.hover_anim = {}
        self._combat_triggers = ["combat_start", "player_turn_start", "enemy_turn_start", "enemy_big_attack", "player_low_hp", "enemy_low_hp", "victory"]
        self._art_manifest = load_json(data_dir() / "art_manifest.json", default={})
        self._card_prompts = load_json(data_dir() / "card_prompts.json", default={})
        self.turn_timer_enabled = bool(self.app.user_settings.get("turn_timer_enabled", False))
        self.turn_timer_limit = float(max(3, int(self.app.user_settings.get("turn_timer_seconds", 20))))
        self.turn_timer_left = self.turn_timer_limit
        self.actions_log = getattr(self.app, "combat_actions_log", [])
        self._action_state = "END_TURN"
        self._action_state_reason = "default"
        self._action_button_fsm = "IDLE"
        self._ui_lock_until_ms = 0
        self._last_reason_code = REASON_OK
        self._status_line = ""
        self._invalid_feedback_until_ms = 0
        self._invalid_feedback_msg = ""
        self._cost_pulse_until = {}
        self.telemetry = TelemetryLogger("INFO")
        self.dialogue_ctrl = CombatDialogueController(self.app.lore_engine, self._set_dialogue_lines)
        self.dialog_router = DialogueRouter(self.app.lore_engine, cooldown_ms=850)
        self.last_enemy_line = ""
        self.last_player_line = ""
        self.topbar = CombatTopBar()
        self.scry_picker = ModalCardPicker()
        self.layout = build_combat_layout(1920, 1080)
        self.end_turn_rect = pygame.Rect(0, 0, 1, 1)
        self.harmony_seal_rect = pygame.Rect(0, 0, 1, 1)
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.set_dialogue("combat_start", enemy_id, {})

    def on_leave(self):
        self.ctrl.clear_selection("screen_change")

    def _refresh_layout(self, surface: pygame.Surface):
        self.layout = build_combat_layout(surface.get_width(), surface.get_height())
        base_w = max(260, int(self.layout.actions_rect.w * 0.22))
        base_h = max(62, int(self.layout.actions_rect.h * 0.62))
        btn_w = min(self.layout.actions_rect.w - 56, int(base_w * 1.60))
        btn_h = min(self.layout.actions_rect.h - 40, int(base_h * 1.12))
        top_band = 30
        btn_y = self.layout.actions_rect.y + top_band + max(0, (self.layout.actions_rect.h - top_band - btn_h - 8) // 2)
        self.end_turn_rect = pygame.Rect(self.layout.actions_rect.centerx - btn_w // 2, btn_y, btn_w, btn_h)
        self.harmony_seal_rect = pygame.Rect(self.layout.playerhud_rect.right - 108, self.layout.playerhud_rect.y + 122, 92, 26)

    def _dialogue_lookup(self, enemy_id: str, trigger: str):
        e, c = self.app.lore_engine.get_combat_lines(enemy_id, trigger)
        if str(e or "").strip() and str(c or "").strip():
            return str(e), str(c), "lore"
        item = self.app.lore_engine.combat_dialogues.get(enemy_id, self.app.lore_engine.combat_dialogues.get("default", {}))
        tr = item.get(trigger, {}) if isinstance(item, dict) else {}
        if isinstance(tr, dict):
            ee, cc = str(tr.get("enemy", "")).strip(), str(tr.get("chakana", "")).strip()
            if ee or cc:
                return ee or "", cc or "", "pair"
        return "", "", "missing"

    def set_dialogue(self, trigger: str, enemy_id: str, ctx: dict | None = None):
        picked = self.dialog_router.pick(enemy_id, trigger, ctx or {})
        if picked is None:
            return
        enemy_line, hero_line, mapped_trigger = picked
        if enemy_line == self.last_enemy_line and hero_line == self.last_player_line:
            enemy_line, hero_line = "La Trama cambia de tono.", "Escucho y respondo."
        self._set_dialogue_lines(enemy_line, hero_line, mapped_trigger)
        self.last_enemy_line, self.last_player_line = enemy_line, hero_line
        print(f"[dlg] trigger={mapped_trigger} enemy={enemy_id} ctx={ctx or {}}")

    def _card_playable(self, card) -> bool:
        ok, _reason_code, _reason_text = can_play_card(card, self.c.player, self.c)
        return bool(ok)

    def _selected_card_play_state(self):
        idx = self.ctrl.selected_index
        if idx is None or idx >= len(self.c.hand):
            return False, "OTHER", "Sin selección"
        return can_play_card(self.c.hand[idx], self.c.player, self.c)

    def _playable_cards(self):
        return [c for c in self.c.hand if self._card_playable(c)]

    def _enemy_rupture_total(self) -> int:
        total = 0
        for enemy in getattr(self.c, "enemies", []) or []:
            if not getattr(enemy, "alive", False):
                continue
            st = getattr(enemy, "statuses", {}) or {}
            total += int(st.get("break", 0) or 0)
            total += int(st.get("rupture", 0) or 0)
        return max(0, total)

    def _ui_locked(self) -> bool:
        return pygame.time.get_ticks() < self._ui_lock_until_ms

    def _lock_ui(self):
        cd = int(getattr(self.c, "ui_cooldown_ms", 200) or 200)
        self._ui_lock_until_ms = pygame.time.get_ticks() + max(150, min(250, cd))

    def _set_invalid_feedback(self, message: str):
        self._invalid_feedback_msg = str(message or "Accion invalida")
        self._invalid_feedback_until_ms = pygame.time.get_ticks() + 1200

    def _resolve_action_state(self):
        p = self.c.player
        h_cur = int(p.get("harmony_current", 0) or 0)
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))

        if self._ui_locked() or self.resolving_t > 0:
            fsm, state, reason, label, disabled = "LOCKED_COOLDOWN", "INVALID", "STATE_LOCK", "BLOQUEADO", True
        else:
            idx = self.ctrl.selected_index
            if idx is None or idx >= len(self.c.hand):
                if h_cur >= h_thr:
                    fsm, state, reason, label, disabled = "HARMONY_CHARGED", "RELEASE_SEAL", REASON_OK, "ACTIVAR SELLO", False
                else:
                    fsm, state, reason, label, disabled = "IDLE", "END_TURN", REASON_OK, "FIN DEL RITUAL", False
            else:
                card = self.c.hand[idx]
                ok, reason_code, reason_text = can_play(card, self.c)
                self._last_reason_code = reason_code
                if ok:
                    fsm, state, reason, label, disabled = "READY_TO_EXECUTE", "EXECUTE", reason_code, "EJECUTAR", False
                else:
                    fsm, state, reason, label, disabled = "CARD_INVALID", "INVALID", reason_code, "ACCIÓN INVÁLIDA", False
                    self._status_line = reason_text

        if DEBUG_UI and (fsm != self._action_button_fsm or reason != self._action_state_reason):
            print(f"[ui] action_fsm={fsm} reason_code={reason}")
        self._action_button_fsm = fsm
        self._action_state = state
        self._action_state_reason = reason
        if reason == REASON_OK:
            self._status_line = ""
        elif fsm == "LOCKED_COOLDOWN":
            self._status_line = reason_to_es(reason)
        return state, label, disabled, reason

    def _set_dialogue_lines(self, enemy_line: str, hero_line: str, trigger: str):
        self.dialog_enemy.set(enemy_line or "...", 1.0)
        self.dialog_hero.set(hero_line or "...", 1.0)
        self.enemy_line_fx = 0.24
        self.hero_line_fx = 0.22
        self.dialog_cd = 0.8
        self.last_trigger = trigger

    def _push_log(self, text: str):
        if not text:
            return
        entry = str(text).strip()
        if not entry:
            return

        if self.actions_log:
            prev = str(self.actions_log[-1])
            if " x" in prev and prev.rsplit(" x", 1)[-1].isdigit():
                base, n = prev.rsplit(" x", 1)
                if base == entry:
                    self.actions_log[-1] = f"{base} x{int(n) + 1}"
                else:
                    self.actions_log.append(entry)
            elif prev == entry:
                self.actions_log[-1] = f"{entry} x2"
            else:
                self.actions_log.append(entry)
        else:
            self.actions_log.append(entry)

        if len(self.actions_log) > 6:
            del self.actions_log[:-6]

    def _wrap_panel_text(self, text: str, max_width: int, max_lines: int = 2):
        words = str(text or "").split()
        if not words:
            return [""]
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.app.tiny_font.size(test)[0] <= max_width:
                cur = test
                continue
            if cur:
                lines.append(cur)
                if len(lines) >= max_lines:
                    break
                cur = w
            else:
                part = w
                while self.app.tiny_font.size(part)[0] > max_width and len(part) > 1:
                    part = part[:-1]
                lines.append(part)
                if len(lines) >= max_lines:
                    cur = ""
                    break
                cur = w[len(part):].strip()
        if cur and len(lines) < max_lines:
            lines.append(cur)

        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if lines:
            while self.app.tiny_font.size(lines[-1])[0] > max_width and len(lines[-1]) > 1:
                lines[-1] = lines[-1][:-1]
            if len(words) > len(" ".join(lines).split()):
                ell = "..."
                while self.app.tiny_font.size(lines[-1] + ell)[0] > max_width and len(lines[-1]) > 1:
                    lines[-1] = lines[-1][:-1]
                lines[-1] = (lines[-1].rstrip(".") + ell) if not lines[-1].endswith("...") else lines[-1]
        return lines

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.set_dialogue(trigger, enemy_id, {})

    def _execute_selected(self):
        idx = self.ctrl.selected_index
        if idx is None or idx >= len(self.c.hand):
            return
        card = self.c.hand[idx]
        ok_code, reason_code, reason_text = can_play(card, self.c)
        self.telemetry.info("card_click", card_id=getattr(card.definition, "id", "-"), ok=ok_code, reason_code=reason_code)
        if not ok_code:
            msg = reason_text
            self._push_log(f"No se puede jugar: {msg}")
            self._status_line = msg
            self._last_reason_code = reason_code
            try:
                self.app.sfx.play("deny")
            except Exception:
                pass
            return
        self.resolving_t = 0.15
        target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
        self.c.play_card(idx, target_idx)
        self._lock_ui()
        tags = set(getattr(card.definition, "tags", []) or [])
        trig = "card_played_attack" if "attack" in tags else "card_played_block" if ("skill" in tags or "defense" in tags or "block" in tags) else "card_played_ritual"
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.set_dialogue(trig, enemy_id, {"card_id": card.definition.id})
        self._push_log(f"Jugada: {getattr(card.definition, 'name_key', 'Carta')}")
        pc = self._pile_counts()
        self.telemetry.info("card_played", card_id=getattr(card.definition, "id", "-"), energy=self.c.player.get("energy", 0), hand=pc["hand"], draw=pc["draw"], discard=pc["discard"])
        self.ctrl.clear_selection("card_played")

    def _activate_action_button(self):
        state, _label, disabled, reason = self._resolve_action_state()
        self.telemetry.info("action_button_press", fsm=self._action_button_fsm, state=state, reason_code=reason)
        if disabled:
            return
        if state != "INVALID":
            self._invalid_feedback_until_ms = 0
            self._invalid_feedback_msg = ""
        if state == "EXECUTE":
            self._execute_selected()
            return
        if state == "RELEASE_SEAL":
            ok, msg = self.c.activate_harmony_seal()
            self._push_log(str(msg or "SELLO activado"))
            if ok:
                self._lock_ui()
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                self.set_dialogue("harmony_ready", enemy_id, {})
            return
        if state == "INVALID":
            msg = self._status_line or reason_to_es(reason)
            self._push_log(f"No se puede jugar: {msg}")
            self._set_invalid_feedback(msg)
            try:
                self.app.sfx.play("deny")
            except Exception:
                pass
            return
        if state == "END_TURN":
            self._trigger_dialog("enemy_turn_start")
            self.c.end_turn()
            self._lock_ui()
            self.telemetry.info("end_turn_pressed", turn=self.c.turn, energy=self.c.player.get("energy", 0), hand=len(self.c.hand))
            self._push_log("Jugada: Fin del ritual")
            self.ctrl.clear_selection("end_turn")
            self.ctrl.clear_hover()


    def _pile_counts(self):
        if hasattr(self.c, "pile_counts"):
            try:
                pc = self.c.pile_counts()
                return {"draw": int(pc.get("draw", 0)), "hand": int(pc.get("hand", len(getattr(self.c, "hand", []) or []))), "discard": int(pc.get("discard", 0))}
            except Exception:
                pass
        return {
            "draw": len(getattr(self.c, "draw_pile", []) or []),
            "hand": len(getattr(self.c, "hand", []) or []),
            "discard": len(getattr(self.c, "discard_pile", []) or []),
        }

    def _card_rect(self, i, total):
        inner = self.layout.hand_rect.inflate(-18, -36)
        w, h, g = 180, inner.h - 8, 12
        tw = total * w + max(0, total - 1) * g
        x = inner.x + (inner.w - tw) // 2 + i * (w + g)
        y = inner.y + 6
        return pygame.Rect(x, y, w, h)

    def _art_debug_info(self, card):
        try:
            cid = card.definition.id if card else "-"
            card_family = getattr(card.definition, "family", "spirit") if card else "-"
            base_assets = getattr(self.app, "asset_root", None)
            if not isinstance(base_assets, Path):
                base_assets = Path(__file__).resolve().parents[2] / "assets"
            apath = base_assets / "sprites" / "cards" / f"{cid}.png" if card else Path("-")
            exists = apath.exists() if card else False
            items = self._art_manifest.get("items", {}) if isinstance(self._art_manifest, dict) else {}
            entry = items.get(cid, {}) if isinstance(items, dict) else {}
            mstatus = "missing"
            if entry:
                mstatus = "present" if entry.get("generator_version") == GEN_CARD_ART_VERSION else "version mismatch"
            generator_used = entry.get("generator_version", "placeholder" if not exists else "unknown")
            cards_prompts = self._card_prompts.get("cards", {}) if isinstance(self._card_prompts, dict) and isinstance(self._card_prompts.get("cards", {}), dict) else self._card_prompts
            prompts = cards_prompts.get(cid, "") if isinstance(cards_prompts, dict) else ""
            prompt = str((prompts.get("prompt") or prompts.get("prompt_text", "")) if isinstance(prompts, dict) else prompts)[:80]
            return {"card_id": cid, "card_type": card_family, "art_path": str(apath), "file_exists": exists, "manifest_status": mstatus, "generator_used": generator_used, "prompt_used": prompt}
        except Exception as exc:
            return {"card_id": "-", "card_type": "-", "art_path": "-", "file_exists": False, "manifest_status": "missing", "generator_used": f"error:{exc}", "prompt_used": ""}

    def _intent_led_color(self, enemy):
        label = str(enemy.current_intent().get("label", "")).lower()
        if "ata" in label:
            return (250, 84, 100)
        if "blo" in label or "def" in label:
            return (72, 188, 240)
        return (174, 116, 255)

    def _topbar_narrative(self):
        run = self.app.run_state or {}
        deck_name = str(run.get("deck_name") or run.get("starter_name") or "Inicial")
        left = f"Chakana • Mazo: {deck_name}"

        node = self.app.node_lookup.get(self.app.current_node_id) if getattr(self.app, "current_node_id", None) else None
        pacha = self.app.get_biome_display_name(self.selected_biome or run.get("biome"))
        if isinstance(node, dict):
            node_name = "Élite" if node.get("type") == "challenge" else self.app.loc.t(f"node_{node.get('type', 'combat')}")
        else:
            node_name = "Nodo desconocido"
        center = f"{pacha} — {node_name}"
        subtitle = str(self.app.lore_engine.get_map_narration("default") if hasattr(self.app, "lore_engine") else "")

        timer_text = f"{self.turn_timer_left:04.1f}s" if self.turn_timer_enabled else "--"
        turn_text = f"Turno {int(self.c.turn) if hasattr(self.c, 'turn') else '-'}"
        return left, center, subtitle, timer_text, turn_text

    def _mark_current_node_incomplete(self):
        node = self.app.node_lookup.get(self.app.current_node_id) if getattr(self.app, "current_node_id", None) else None
        if isinstance(node, dict) and node.get("state") not in {"cleared", "completed"}:
            node["state"] = "incomplete"

    def handle_event(self, event):
        if self.scry_picker.open:
            mapped_pos = self.app.renderer.map_mouse(event.pos) if hasattr(event, "pos") else None
            if self.scry_picker.handle_event(event, mapped_pos):
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pause_open = not self.pause_open
            if self.pause_open:
                self.ctrl.clear_selection("pause_open")
            self.pause_confirm_target = None
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            self.dialog_debug_overlay = not self.dialog_debug_overlay
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            self.qa_debug_overlay = not self.qa_debug_overlay
            return
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            idx = (self._combat_triggers.index(self.last_trigger) + 1) % len(self._combat_triggers) if self.last_trigger in self._combat_triggers else 0
            self._trigger_dialog(self._combat_triggers[idx])
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
            self.art_debug_overlay = not self.art_debug_overlay
            return

        if self.pause_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.app.renderer.map_mouse(event.pos)
                panel = pygame.Rect(680, 330, 560, 420)
                options = {
                    "continue": pygame.Rect(panel.x + 80, panel.y + 84, 400, 64),
                    "map": pygame.Rect(panel.x + 80, panel.y + 170, 400, 64),
                    "menu": pygame.Rect(panel.x + 80, panel.y + 256, 400, 64),
                }
                for k, r in options.items():
                    if not r.collidepoint(pos):
                        continue
                    if k == "continue":
                        self.pause_open = False
                        self.pause_confirm_target = None
                    elif k == "map":
                        if self.pause_confirm_target == "map":
                            self.pause_open = False
                            self.pause_confirm_target = None
                            self._mark_current_node_incomplete()
                            self.app.goto_map()
                        else:
                            self.pause_confirm_target = "map"
                    elif k == "menu":
                        if self.pause_confirm_target == "menu":
                            self.pause_open = False
                            self.pause_confirm_target = None
                            self._mark_current_node_incomplete()
                            self.app.menu_return_screen = None
                            self.app.goto_menu()
                        else:
                            self.pause_confirm_target = "menu"
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self.ctrl.on_mouse_down("action")
                return
            in_card = False
            for i, _ in enumerate(self.c.hand[:6]):
                if self._card_rect(i, min(6, len(self.c.hand))).collidepoint(pos):
                    self.ctrl.on_card_click(i)
                    in_card = True
                    sel = self.c.hand[i] if i < len(self.c.hand) else None
                    ok_code, reason_code, reason_text = can_play(sel, self.c) if sel else (False, "OTHER", "No se puede jugar")
                    self._last_reason_code = reason_code
                    self.telemetry.info("card_click", card_id=getattr(getattr(sel, "definition", None), "id", "-"), ok=ok_code, reason_code=reason_code)
                    if not ok_code:
                        self._status_line = reason_text
                        self._push_log(f"No se puede jugar: {reason_text}")
                    break
            if not in_card:
                self.ctrl.clear_selection("click_outside")

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            button_id = "action" if self.end_turn_rect.collidepoint(pos) else None
            if self.ctrl.on_mouse_up(button_id):
                self._activate_action_button()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._execute_selected()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            self._push_log("Armonía: se carga con rituales. Cuando está LISTA, potencia defensas o activa SELLO.")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.harmony_seal_rect.collidepoint(pos):
                ok, msg = self.c.activate_harmony_seal()
                self._push_log(msg)
                if ok:
                    enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                    self.set_dialogue("harmony_ready", enemy_id, {})

    def _card_icons(self, card):
        tags = set(getattr(card.definition, "tags", []) or [])
        effects = list(getattr(card.definition, "effects", []) or [])
        icons = []
        if "attack" in tags:
            icons.append("sword")
        if "skill" in tags or any(str(e.get("type", "")) in {"block", "gain_block"} for e in effects if isinstance(e, dict)):
            icons.append("shield")
        if "ritual" in tags:
            icons.append("star")
        if any(str(e.get("type", "")) == "scry" for e in effects if isinstance(e, dict)):
            icons.append("eye")
        if any(str(e.get("type", "")) == "draw" for e in effects if isinstance(e, dict)):
            icons.append("scroll")
        if any(str(e.get("type", "")) in {"rupture", "apply_break"} for e in effects if isinstance(e, dict)):
            icons.append("crack")
        if any(str(e.get("type", "")) in {"energy", "gain_mana"} for e in effects if isinstance(e, dict)):
            icons.append("bolt")
        return icons

    def _card_tier(self, card) -> str:
        rarity = str(getattr(card.definition, "rarity", "common") or "common").lower().strip()
        tags = set(getattr(card.definition, "tags", []) or [])
        if "ritual" in tags:
            return "ritual"
        if rarity in {"legendary", "boss"}:
            return "legendary"
        if rarity in {"rare", "uncommon"}:
            return "rare"
        return "normal"

    def _seed_from_card(self, card) -> int:
        cid = str(getattr(card.definition, "id", "card") or "card")
        return sum((i + 1) * ord(ch) for i, ch in enumerate(cid)) % 1000003

    def _fallback_card_art(self, card, size: tuple[int, int], tier: str, accent: tuple[int, int, int]) -> pygame.Surface:
        w, h = max(24, int(size[0])), max(24, int(size[1]))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        base_map = {
            "normal": (90, 78, 60),
            "rare": (86, 66, 124),
            "legendary": (118, 84, 36),
            "ritual": (68, 46, 98),
        }
        base = base_map.get(tier, (82, 60, 96))
        for y in range(h):
            f = y / max(1, h - 1)
            row = (int(base[0] * (0.72 + 0.28 * f)), int(base[1] * (0.72 + 0.28 * f)), int(base[2] * (0.72 + 0.28 * f)))
            pygame.draw.line(surf, row, (0, y), (w, y))
        pygame.draw.rect(surf, accent, surf.get_rect(), 1, border_radius=7)
        glyph = "✦" if tier in {"legendary", "ritual"} else "◈"
        if tier == "ritual":
            glyph = "ᚱ"
        txt = self.app.small_font.render(glyph, True, (232, 220, 170))
        surf.blit(txt, txt.get_rect(center=surf.get_rect().center))
        return surf

    def _draw_card_background(self, s, rect: pygame.Rect, card, tier: str, accent: tuple[int, int, int]):
        rng = random.Random(self._seed_from_card(card))
        base_map = {
            "normal": (70, 60, 48),
            "rare": (62, 48, 92),
            "legendary": (96, 66, 30),
            "ritual": (58, 38, 86),
        }
        border_map = {
            "normal": (166, 140, 102),
            "rare": (186, 142, 244),
            "legendary": (248, 212, 118),
            "ritual": (210, 154, 255),
        }
        base = base_map.get(tier, base_map["normal"])
        border = border_map.get(tier, border_map["normal"])

        # Solid mystical body to improve readability.
        for y in range(rect.y, rect.bottom):
            f = (y - rect.y) / max(1, rect.h - 1)
            row = (
                int(base[0] * (0.86 + 0.18 * f)),
                int(base[1] * (0.86 + 0.18 * f)),
                int(base[2] * (0.86 + 0.18 * f)),
            )
            pygame.draw.line(s, row, (rect.x, y), (rect.right, y))

        if tier == "normal":
            for _ in range(max(28, rect.w * rect.h // 720)):
                px = rng.randint(rect.x + 2, rect.right - 3)
                py = rng.randint(rect.y + 2, rect.bottom - 3)
                n = rng.randint(-12, 14)
                col = (
                    max(0, min(255, base[0] + n)),
                    max(0, min(255, base[1] + n)),
                    max(0, min(255, base[2] + n)),
                )
                s.set_at((px, py), col)
        elif tier == "rare":
            aura = pygame.Surface((rect.w + 28, rect.h + 28), pygame.SRCALPHA)
            pygame.draw.rect(aura, (*accent, 92), aura.get_rect(), border_radius=18)
            s.blit(aura, (rect.x - 14, rect.y - 14))
            for ring in range(2):
                alpha = 92 - ring * 26
                rr = pygame.Rect(rect.x - 4 - ring * 4, rect.y - 4 - ring * 4, rect.w + 8 + ring * 8, rect.h + 8 + ring * 8)
                pygame.draw.rect(s, (*accent, alpha), rr, 2, border_radius=14 + ring * 2)
        elif tier == "legendary":
            glow = pygame.Surface((rect.w + 36, rect.h + 36), pygame.SRCALPHA)
            pygame.draw.rect(glow, (246, 212, 128, 78), glow.get_rect(), border_radius=20)
            s.blit(glow, (rect.x - 18, rect.y - 18))
            inner = rect.inflate(-12, -12)
            pygame.draw.rect(s, (244, 220, 150), inner, 1, border_radius=10)
        else:
            step = 18
            rune_col = (218, 184, 255)
            for iy, y in enumerate(range(rect.y + 10, rect.bottom - 10, step)):
                for ix, x in enumerate(range(rect.x + 10, rect.right - 10, step)):
                    if (ix + iy) % 2 == 0:
                        pygame.draw.circle(s, rune_col, (x, y), 1)

        pygame.draw.rect(s, border, rect, 3, border_radius=12)

    def _card_kpis(self, summary: dict) -> list[tuple[str, int]]:
        stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
        ordered = [
            ("damage", "sword"),
            ("block", "shield"),
            ("rupture", "crack"),
            ("harmony_delta", "star"),
            ("scry", "eye"),
            ("draw", "scroll"),
        ]
        out = []
        for key, icon in ordered:
            val = int(stats.get(key, 0) or 0)
            if val > 0:
                out.append((icon, val))
        return out[:3]

    def _draw_card(self, s, rect, card, selected=False, family="violet_arcane"):
        accent = {
            "crimson_chaos": (220, 108, 84),
            "emerald_spirit": (88, 198, 154),
            "azure_cosmic": (112, 152, 228),
            "violet_arcane": (176, 126, 240),
            "solar_gold": (226, 190, 112),
        }.get(family, (176, 126, 240))
        tier = self._card_tier(card)

        self._draw_card_background(s, rect, card, tier, accent)

        art_frame = pygame.Rect(rect.x + 8, rect.y + 32, rect.w - 16, int(rect.h * 0.50))
        pygame.draw.rect(s, (24, 20, 30), art_frame, border_radius=9)
        pygame.draw.rect(s, accent, art_frame, 2, border_radius=9)
        art_inner = art_frame.inflate(-6, -6)
        pygame.draw.rect(s, (12, 12, 16), art_inner, border_radius=7)
        try:
            art = self.app.assets.sprite("cards", card.definition.id, (art_inner.w, art_inner.h), fallback=(70, 44, 105))
        except Exception:
            art = None
        if art is None or art.get_width() < 8 or art.get_height() < 8:
            art = self._fallback_card_art(card, (art_inner.w, art_inner.h), tier, accent)
        s.blit(art, art_inner.topleft)

        if tier == "legendary":
            pygame.draw.rect(s, (250, 226, 156), art_frame.inflate(6, 6), 1, border_radius=11)

        card_name = self.app.loc.t(getattr(card.definition, "name_key", getattr(card.definition, "id", "Carta")))
        title = str(card_name)[:20]
        title_shadow = self.app.small_font.render(title, True, (8, 8, 8))
        title_txt = self.app.small_font.render(title, True, (245, 238, 220))
        s.blit(title_shadow, (rect.x + 10, rect.y + 8))
        s.blit(title_txt, (rect.x + 9, rect.y + 7))

        base_cost = int(getattr(card.definition, "cost", card.cost) or 0)
        live_cost = int(card.cost or 0)
        modified = live_cost != base_cost
        reduced = live_cost < base_cost
        cost_col = UI_THEME["energy"] if not modified else (120, 220, 255) if reduced else (228, 132, 108)
        cost_bg = (18, 18, 24)
        center = (rect.right - 20, rect.y + 20)
        pygame.draw.circle(s, cost_bg, center, 19)
        pygame.draw.circle(s, cost_col, center, 16)
        pygame.draw.circle(s, (255, 244, 208), center, 16, 2)
        cost_txt = self.app.big_font.render(str(live_cost), True, UI_THEME["text_dark"])
        s.blit(cost_txt, (center[0] - cost_txt.get_width() // 2, center[1] - cost_txt.get_height() // 2))

        if modified:
            trans = f"{base_cost}->{live_cost}"
            tcol = UI_THEME["good"] if reduced else UI_THEME["bad"]
            s.blit(self.app.tiny_font.render(trans, True, tcol), (rect.x + 10, rect.y + 25))
            if reduced:
                g = pygame.Surface((rect.w + 12, rect.h + 12), pygame.SRCALPHA)
                alpha = 55
                pid = str(getattr(card, "instance_id", ""))
                if self._cost_pulse_until.get(pid, 0) > pygame.time.get_ticks():
                    alpha = 92 + int(56 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 90.0)))
                pygame.draw.rect(g, (96, 210, 255, alpha), g.get_rect(), border_radius=14)
                s.blit(g, (rect.x - 6, rect.y - 6))

        summary = summarize_card_effect(card.definition, card_instance=card, ctx=self.c)
        kpis = self._card_kpis(summary)

        lore = str(summary.get("header") or "")
        if not lore:
            lore = self.app.loc.t(getattr(card.definition, "text_key", ""))
        lore = lore.replace("\n", " ").strip()
        while self.app.tiny_font.size(lore)[0] > rect.w - 18 and len(lore) > 4:
            lore = lore[:-4] + "..."
        if lore:
            s.blit(self.app.tiny_font.render(lore, True, (236, 228, 206)), (rect.x + 9, art_frame.bottom + 8))

        kpi_band = pygame.Rect(rect.x + 6, rect.bottom - 34, rect.w - 12, 24)
        pygame.draw.rect(s, (18, 18, 24), kpi_band, border_radius=7)
        pygame.draw.rect(s, (76, 70, 94), kpi_band, 1, border_radius=7)
        x = kpi_band.x + 6
        if kpis:
            for icon_name, val in kpis:
                x = draw_icon_with_value(s, icon_name, val, (246, 228, 156), self.app.small_font, x, kpi_band.y + 4, size=1)
                if x > kpi_band.right - 30:
                    break
        else:
            s.blit(self.app.tiny_font.render("Sin KPI relevantes", True, UI_THEME["muted"]), (kpi_band.x + 6, kpi_band.y + 6))

        if selected:
            pygame.draw.rect(s, UI_THEME["gold"], rect.inflate(8, 8), 3, border_radius=14)
    def update(self, dt):
        self.c.update(dt)
        self.resolving_t = max(0, self.resolving_t - dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        self.mana_orbs.tick(dt)
        self.enemy_line_fx = max(0, self.enemy_line_fx - dt)
        self.hero_line_fx = max(0, self.hero_line_fx - dt)

        if self.turn_timer_enabled and self.c.result is None and not self.pause_open:
            self.turn_timer_left = max(0.0, self.turn_timer_left - dt)
            if self.turn_timer_left <= 0:
                self._trigger_dialog("enemy_turn_start")
                self.c.end_turn()
                self._push_log("Jugada: Fin de turno (timer)")
                self.ctrl.clear_selection("timer_end_turn")
                self.ctrl.clear_hover()
                self.turn_timer_left = self.turn_timer_limit

        if self.last_turn != self.c.turn:
            self.last_turn = self.c.turn
            self.turn_timer_left = self.turn_timer_limit
            self.ctrl.clear_selection("turn_changed")
            self._trigger_dialog("player_turn_start")
            enemy = self.c.enemies[0] if self.c.enemies else None
            if enemy is not None:
                self.set_dialogue("enemy_intent_set", enemy.id, {"intent": enemy.current_intent().get("label", "")})

        for ev in self.c.pop_events():
            if ev.get("type") == "damage" and ev.get("target") == "player" and ev.get("amount", 0) >= 8:
                self._trigger_dialog("enemy_big_attack")
                self._push_log(f"Daño recibido: {ev.get('amount',0)}")
            if ev.get("type") == "card_played":
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                card_id = str(ev.get("card_id", ""))
                card_def = next((c for c in self.app.cards_data if c.get("id") == card_id), {}) if card_id else {}
                tags = set(card_def.get("tags", []) if isinstance(card_def, dict) else [])
                trig = "card_played_attack" if "attack" in tags else "card_played_block" if ("skill" in tags or "defense" in tags or "block" in tags) else "card_played_ritual"
                self.set_dialogue(trig, enemy_id, {"card_id": card_id})
            if ev.get("type") == "card_cost_changed":
                if ev.get("in_hand"):
                    iid = str(ev.get("instance_id") or "")
                    old_c = int(ev.get("old_cost", 0) or 0)
                    new_c = int(ev.get("new_cost", 0) or 0)
                    if iid and new_c < old_c:
                        self._cost_pulse_until[iid] = pygame.time.get_ticks() + 950
            if ev.get("type") == "harmony_ready":
                self._push_log(str(ev.get("message") or "Armonía lista: desata tu sello."))
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                self.set_dialogue("harmony_ready", enemy_id, {})
            if ev.get("type") == "enemy_action":
                self.set_dialogue(str(ev.get("intent") or "turn_start"), str(ev.get("enemy") or "default"), {})
            if ev.get("type") == "harmony_seal":
                self._push_log(str(ev.get("message") or "SELLO activado"))

        if self.c.scry_pending and not self.scry_picker.open:
            self.scry_picker.show(
                self.c.scry_pending,
                on_confirm=lambda card: self.c.apply_scry_keep(card),
                on_cancel=lambda: self.c.apply_scry_keep(None),
            )

        if self.c.player["hp"] <= max(10, self.c.player["max_hp"] * 0.3):
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("low_hp_player", enemy_id, {})

        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("low_hp_enemy", enemy_id, {})

        self.ctrl.validate_selection(len(self.c.hand))
        if self.c.result == "victory":
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("victory", enemy_id, {})
            self.ctrl.clear_selection("victory")
            self._push_log("Combate ganado")
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.ctrl.clear_selection("defeat")
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("defeat", enemy_id, {})
            self._push_log("Combate perdido")
            self.app.goto_end(victory=False)

    def render(self, s):
        self._refresh_layout(s)
        self.app.bg_gen.render_parallax(
            s,
            self.selected_biome,
            self.bg_seed,
            pygame.time.get_ticks() * 0.02,
            clip_rect=pygame.Rect(0, 0, s.get_width(), self.layout.voices_rect.bottom + 12),
            particles_on=self.app.user_settings.get("fx_particles", True),
        )

        left, center, subtitle, timer_text, turn_text = self._topbar_narrative()
        self.topbar.render(s, self.app, self.layout, left, center, subtitle, timer_text, turn_text)

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.enemy_strip_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.enemy_strip_rect, 2, border_radius=12)

        enemy_count = max(1, len(self.c.enemies))
        inner_strip = self.layout.enemy_strip_rect.inflate(-24, -18)
        card_w = (inner_strip.w - (enemy_count - 1) * 16) // enemy_count
        if enemy_count == 1:
            card_w = min(inner_strip.w - 72, int(inner_strip.w * 0.62))
            enemy_start_x = inner_strip.centerx - card_w // 2
        else:
            enemy_start_x = inner_strip.x
        t = pygame.time.get_ticks() / 1000.0

        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(enemy_start_x + i * (card_w + 16), inner_strip.y, card_w, inner_strip.h)
            content = er.inflate(-8, -8)
            pygame.draw.rect(s, UI_THEME["deep_purple"], content, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], content, 2, border_radius=12)

            ratio = max(0, e.hp) / max(1, e.max_hp)
            title = pygame.Rect(content.x + 14, content.y + 10, content.w - 28, 24)
            hp_label = pygame.Rect(content.x + 14, title.bottom + 3, content.w - 28, 30)
            intent_line = pygame.Rect(content.x + 14, hp_label.bottom + 1, content.w - 28, 20)
            counters = pygame.Rect(content.x + 14, intent_line.bottom + 2, content.w - 28, 16)
            avatar_rect = pygame.Rect(content.x + 18, counters.bottom + 6, content.w - 36, max(92, content.bottom - counters.bottom - 20))
            hp_bar = pygame.Rect(content.x + 14, avatar_rect.bottom - 14, content.w - 28, 10)

            enemy_name = str(e.name_key)
            intent_name = str(e.current_intent().get("label", "..."))
            s.blit(self.app.small_font.render(enemy_name, True, UI_THEME["text"]), (title.x, title.y))
            s.blit(self.app.big_font.render(f"HP {e.hp}/{e.max_hp}", True, UI_THEME["hp"]), (hp_label.x, hp_label.y - 2))
            s.blit(self.app.small_font.render(intent_name, True, self._intent_led_color(e)), (intent_line.x, intent_line.y))

            pattern_len = max(1, len(getattr(e, "pattern", []) or []))
            deck_est = max(0, pattern_len - ((getattr(e, "intent_index", 0) + 1) % pattern_len))
            discard_est = min(pattern_len, getattr(e, "intent_index", 0))
            counter_txt = f"Deck {deck_est}  Hand 1  Discard {discard_est}"
            s.blit(self.app.tiny_font.render(counter_txt, True, UI_THEME["muted"]), (counters.x, counters.y))

            sprite = self.app.assets.sprite("enemies", e.id, (avatar_rect.w, avatar_rect.h), fallback=(100, 60, 90))
            sprite_box = sprite.get_rect(center=avatar_rect.center)
            s.blit(sprite, sprite_box.topleft)

            pygame.draw.rect(s, (28, 22, 36), hp_bar, border_radius=5)
            pygame.draw.rect(s, UI_THEME["hp"], pygame.Rect(hp_bar.x, hp_bar.y, int(hp_bar.w * ratio), hp_bar.h), border_radius=5)

            intent_col = self._intent_led_color(e)
            aura_h = 8
            aura_w = int(avatar_rect.w * (0.7 + 0.3 * (0.5 + 0.5 * math.sin(t * (1.8 + i * 0.2)))))
            aura_x = avatar_rect.centerx - aura_w // 2
            aura_y = avatar_rect.bottom - aura_h - 2
            aura = pygame.Surface((aura_w, aura_h), pygame.SRCALPHA)
            aura.fill((*intent_col, 140))
            s.blit(aura, (aura_x, aura_y))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.voices_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.voices_rect, 2, border_radius=12)
        e_line = self.dialog_enemy.current or "(el enemigo contiene la respiracion...)"
        h_line = self.dialog_hero.current or "(Chakana escucha la Trama...)"
        line_w = self.layout.voices_rect.w - 36
        enemy_lines = wrap_text(self.app.small_font, e_line, line_w, max_lines=2)
        hero_lines = wrap_text(self.app.small_font, h_line, line_w, max_lines=2)
        enemy_box = pygame.Rect(self.layout.voices_rect.x + 10, self.layout.voices_rect.y + 10, self.layout.voices_rect.w - 20, (self.layout.voices_rect.h - 26) // 2)
        hero_box = pygame.Rect(self.layout.voices_rect.x + 10, enemy_box.bottom + 6, self.layout.voices_rect.w - 20, (self.layout.voices_rect.h - 26) // 2)
        pygame.draw.rect(s, (58, 34, 52), enemy_box, border_radius=8)
        pygame.draw.rect(s, (36, 52, 46), hero_box, border_radius=8)
        s.blit(self.app.tiny_font.render("ENEMIGO", True, (245, 132, 142)), (enemy_box.x + 8, enemy_box.y + 4))
        s.blit(self.app.tiny_font.render("CHAKANA", True, (166, 240, 190)), (hero_box.x + 8, hero_box.y + 4))
        threat = 3 if any(k in str(self.last_trigger) for k in ["attack", "defeat", "low"]) else 0
        offx = threat if (pygame.time.get_ticks() // 40) % 2 == 0 else -threat
        y = enemy_box.y + 20
        for ln in enemy_lines:
            s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (enemy_box.x + 10 + offx, y))
            y += 16
        y = hero_box.y + 20
        for ln in hero_lines:
            s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (hero_box.x + 10, y))
            y += 16

        hand = self.c.hand[:6]
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card_index = None
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                self.hover_card_index = i
        self.ctrl.on_hover(self.hover_card_index)

        detail_rect = self.layout.card_detail
        pygame.draw.rect(s, UI_THEME["panel"], detail_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], detail_rect, 2, border_radius=12)
        panel_x = detail_rect.x + 14
        panel_y = detail_rect.y + 14
        panel_w = detail_rect.w - 26
        entries = list(self.actions_log[-6:])
        if self._status_line:
            entries.append(f"Estado: {self._status_line}")
        if not entries:
            entries = ["Sin acciones recientes."]
        for item in reversed(entries):
            for ln in self._wrap_panel_text(f"- {item}", panel_w, max_lines=2):
                if panel_y > detail_rect.bottom - 24:
                    break
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (panel_x, panel_y))
                panel_y += 16
            if panel_y > detail_rect.bottom - 24:
                break

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.hand_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.hand_rect, 2, border_radius=12)

        hand_inner = self.layout.hand_rect.inflate(-8, -8)
        pygame.draw.rect(s, UI_THEME["panel"], hand_inner, border_radius=10)

        old_clip = s.get_clip()
        s.set_clip(self.layout.hand_rect)
        for i, card in enumerate(hand):
            if i == self.hover_card_index:
                continue
            base = self._card_rect(i, len(hand))
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, base, card, selected=(i == self.ctrl.selected_index), family=fam)
        s.set_clip(old_clip)

        if self.hover_card_index is not None and self.hover_card_index < len(hand):
            i = self.hover_card_index
            card = hand[i]
            base_hover = self._card_rect(i, len(hand))
            ww = int(base_hover.w * 1.42)
            hh = int(base_hover.h * 1.42)
            rr = pygame.Rect(0, 0, ww, hh)
            rr.centerx = base_hover.centerx
            rr.centery = base_hover.centery - 44
            rr.x = max(8, min(s.get_width() - rr.w - 8, rr.x))
            rr.y = max(self.layout.topbar_rect.bottom + 8, min(self.layout.actions_rect.y - rr.h - 8, rr.y))

            shadow_rect = rr.inflate(28, 28)
            shadow = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 132), shadow.get_rect(), border_radius=22)
            s.blit(shadow, shadow_rect.topleft)
            hover_glow = pygame.Surface((rr.w + 18, rr.h + 18), pygame.SRCALPHA)
            pygame.draw.rect(hover_glow, (214, 174, 255, 72), hover_glow.get_rect(), border_radius=20)
            s.blit(hover_glow, (rr.x - 9, rr.y - 9))

            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, rr, card, selected=(i == self.ctrl.selected_index), family=fam)
            pygame.draw.rect(s, (236, 220, 255), rr.inflate(8, 8), 2, border_radius=15)

            summary = summarize_card_effect(card.definition, card_instance=card, ctx=self.c)
            tip = str(summary.get("header") or "Efecto")
            tip_w = min(520, s.get_width() - 16)
            tip_rect = pygame.Rect(rr.centerx - tip_w // 2, rr.y - 34, tip_w, 28)
            if tip_rect.y < self.layout.topbar_rect.bottom + 8:
                tip_rect.y = rr.bottom + 6
            tip_rect.x = max(8, min(s.get_width() - tip_rect.w - 8, tip_rect.x))
            pygame.draw.rect(s, UI_THEME["deep_purple"], tip_rect, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], tip_rect, 1, border_radius=8)
            line = tip
            while self.app.tiny_font.size(line)[0] > tip_rect.w - 12 and len(line) > 4:
                line = line[:-4] + "..."
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (tip_rect.x + 6, tip_rect.y + 6))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.playerhud_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.playerhud_rect, 2, border_radius=12)
        p = self.c.player
        pc = self._pile_counts()
        draw_n = pc["draw"]
        hand_n = pc["hand"]
        disc_n = pc["discard"]
        fatigue_n = int(getattr(self.c, "fatigue_counter", 0) or 0)
        energy_now = int(p.get("energy", 0) or 0)

        left_x = self.layout.playerhud_rect.x + 14
        top_y = self.layout.playerhud_rect.y + 12
        inner_w = self.layout.playerhud_rect.w - 28
        chip_w = (inner_w - 16) // 3
        chips = [
            ("HP", f"{p['hp']}/{p['max_hp']}", UI_THEME["hp"]),
            ("ENERGIA", f"{energy_now}", UI_THEME["energy"]),
            ("TURNO", f"{self.c.turn}", UI_THEME["gold"]),
        ]
        for i, (title, val, col) in enumerate(chips):
            chip = pygame.Rect(left_x + i * (chip_w + 8), top_y, chip_w, 52)
            pygame.draw.rect(s, UI_THEME["panel_2"], chip, border_radius=8)
            pygame.draw.rect(s, col, chip, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(title, True, UI_THEME["muted"]), (chip.x + 8, chip.y + 6))
            s.blit(self.app.big_font.render(val, True, col), (chip.x + 8, chip.y + 18))

        s.blit(
            self.app.tiny_font.render(
                f"Deck {draw_n}  Hand {hand_n}  Discard {disc_n}  Fatigue {fatigue_n}",
                True,
                UI_THEME["muted"],
            ),
            (left_x, top_y + 62),
        )
        s.blit(self.app.tiny_font.render(f"Block {p['block']}", True, UI_THEME["block"]), (left_x, top_y + 78))

        h_cur = int(p.get("harmony_current", 0) or 0)
        h_max = max(1, int(p.get("harmony_max", 10) or 10))
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        ready = h_cur >= h_thr
        hy = top_y + 98
        s.blit(
            self.app.small_font.render(f"Armonia {h_cur}/{h_max}", True, UI_THEME["good"] if ready else UI_THEME["text"]),
            (left_x, hy),
        )
        s.blit(self.app.tiny_font.render(f"Umbral {h_thr}", True, UI_THEME["muted"]), (left_x + 168, hy + 5))
        bar = pygame.Rect(left_x, hy + 26, self.layout.playerhud_rect.w - 136, 14)
        pygame.draw.rect(s, (28, 26, 40), bar, border_radius=6)
        pygame.draw.rect(s, UI_THEME["good"], pygame.Rect(bar.x, bar.y, int(bar.w * (h_cur / max(1, h_max))), bar.h), border_radius=6)

        seal_y = hy + 20
        self.harmony_seal_rect = pygame.Rect(self.layout.playerhud_rect.right - 100, seal_y, 84, 24)
        if ready:
            pygame.draw.rect(s, UI_THEME["violet"], self.harmony_seal_rect, border_radius=7)
            pygame.draw.rect(s, UI_THEME["gold"], self.harmony_seal_rect, 1, border_radius=7)
            s.blit(self.app.tiny_font.render("SELLO", True, UI_THEME["text"]), (self.harmony_seal_rect.x + 22, self.harmony_seal_rect.y + 5))
        else:
            pygame.draw.rect(s, UI_THEME["panel_2"], self.harmony_seal_rect, border_radius=7)
            s.blit(self.app.tiny_font.render("SELLO", True, UI_THEME["muted"]), (self.harmony_seal_rect.x + 22, self.harmony_seal_rect.y + 5))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.actions_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.actions_rect, 2, border_radius=12)
        state, label, disabled, _reason = self._resolve_action_state()

        state_ui = {
            "EXECUTE": ("EXECUTE_CARD", "EJECUTAR CARTA", (220, 68, 120), (255, 88, 146), UI_THEME["text"]),
            "RELEASE_SEAL": ("RELEASE_SEAL", "LIBERAR SELLO", (192, 132, 246), (246, 206, 112), UI_THEME["text"]),
            "END_TURN": ("END_TURN", "FIN DEL TURNO", UI_THEME["gold"], (244, 220, 154), UI_THEME["text_dark"]),
            "INVALID": ("INVALID_ACTION", "ACCION INVALIDA", (116, 102, 130), (144, 126, 162), UI_THEME["text"]),
        }
        state_tag, state_label, base_col, glow_col, text_col = state_ui.get(state, state_ui["END_TURN"])

        if self.ctrl.pressed_on_button_id == "action" and not disabled:
            base_col = tuple(max(0, min(255, int(c * 0.88))) for c in base_col)

        p = self.c.player
        energy_now = int(p.get("energy", 0) or 0)
        h_cur = int(p.get("harmony_current", 0) or 0)
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        enemy_rupture = self._enemy_rupture_total()

        info_items = [
            (f"ENERGIA {energy_now}", UI_THEME["energy"]),
            (f"ARMONIA {h_cur}/{h_thr}", UI_THEME["violet"] if h_cur >= h_thr else UI_THEME["muted"]),
        ]
        if enemy_rupture > 0:
            info_items.append((f"RUPTURA {enemy_rupture}", UI_THEME["rupture"]))

        chip_y = self.layout.actions_rect.y + 8
        gap = 8
        chip_h = 18
        chip_ws = [max(92, self.app.tiny_font.size(txt)[0] + 16) for txt, _ in info_items]
        total_w = sum(chip_ws) + gap * max(0, len(chip_ws) - 1)
        chip_x = self.layout.actions_rect.centerx - total_w // 2
        for (txtv, colv), cw in zip(info_items, chip_ws):
            chip = pygame.Rect(chip_x, chip_y, cw, chip_h)
            pygame.draw.rect(s, UI_THEME["panel_2"], chip, border_radius=7)
            pygame.draw.rect(s, colv, chip, 1, border_radius=7)
            s.blit(self.app.tiny_font.render(txtv, True, colv), (chip.x + 8, chip.y + 3))
            chip_x += cw + gap

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
        glow_pad = 16
        glow = pygame.Surface((self.end_turn_rect.w + glow_pad * 2, self.end_turn_rect.h + glow_pad * 2), pygame.SRCALPHA)
        ga = 66 + int(96 * pulse)
        if state == "INVALID":
            ga = 40
        if state == "RELEASE_SEAL":
            ga = 96 + int(110 * pulse)
        pygame.draw.rect(glow, (*glow_col, ga), glow.get_rect(), border_radius=22)
        s.blit(glow, (self.end_turn_rect.x - glow_pad, self.end_turn_rect.y - glow_pad))

        pygame.draw.rect(s, base_col, self.end_turn_rect, border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], self.end_turn_rect, 2, border_radius=16)

        tag_rect = pygame.Rect(self.end_turn_rect.x + 10, self.end_turn_rect.y + 8, 168, 18)
        pygame.draw.rect(s, (26, 24, 34), tag_rect, border_radius=7)
        pygame.draw.rect(s, glow_col, tag_rect, 1, border_radius=7)
        s.blit(self.app.tiny_font.render(state_tag, True, glow_col), (tag_rect.x + 6, tag_rect.y + 3))

        txt = self.app.big_font.render(state_label, True, text_col)
        s.blit(txt, (self.end_turn_rect.centerx - txt.get_width() // 2, self.end_turn_rect.centery - txt.get_height() // 2 + 8))

        if state == "RELEASE_SEAL":
            rune = self.app.tiny_font.render("*", True, UI_THEME["gold"])
            s.blit(rune, (self.end_turn_rect.x + 10, self.end_turn_rect.y + 30))
            s.blit(rune, (self.end_turn_rect.right - 16, self.end_turn_rect.y + 30))

        if pygame.time.get_ticks() < self._invalid_feedback_until_ms:
            msg = self._invalid_feedback_msg or "Accion invalida"
            feedback_rect = pygame.Rect(self.layout.actions_rect.centerx - 260, self.layout.actions_rect.bottom - 24, 520, 18)
            pygame.draw.rect(s, (48, 30, 44), feedback_rect, border_radius=6)
            pygame.draw.rect(s, (190, 116, 146), feedback_rect, 1, border_radius=6)
            line = msg
            while self.app.tiny_font.size(line)[0] > feedback_rect.w - 10 and len(line) > 4:
                line = line[:-4] + "..."
            s.blit(self.app.tiny_font.render(line, True, (242, 188, 202)), (feedback_rect.x + 6, feedback_rect.y + 2))
        if DEBUG_UI:
            pygame.draw.rect(s, UI_THEME["gold"], self.layout.voices_panel, 2)
            pygame.draw.rect(s, UI_THEME["gold"], self.layout.card_detail, 2)

        if self.dialog_debug_overlay:
            d = pygame.Rect(self.layout.topbar_rect.x + 10, self.layout.topbar_rect.bottom + 10, 620, 150)
            pygame.draw.rect(s, (0, 0, 0), d, border_radius=8)
            pygame.draw.rect(s, UI_THEME["gold"], d, 2, border_radius=8)
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            map_ok = "OK" if getattr(self.app.lore_engine, "loaded_map", False) else "MISSING"
            combat_ok = "OK" if getattr(self.app.lore_engine, "loaded_combat", False) else "MISSING"
            s.blit(self.app.tiny_font.render(f"MapLore: {map_ok}  CombatLore: {combat_ok}", True, UI_THEME["text"]), (d.x + 12, d.y + 14))
            s.blit(self.app.tiny_font.render(f"enemy_id: {enemy_id}  trigger: {self.last_trigger}", True, UI_THEME["text"]), (d.x + 12, d.y + 40))
            s.blit(self.app.tiny_font.render(f"enemy_len={len(self.dialog_enemy.current)} chakana_len={len(self.dialog_hero.current)}", True, UI_THEME["text"]), (d.x + 12, d.y + 66))

        if self.qa_debug_overlay:
            d = pygame.Rect(self.layout.topbar_rect.x + 10, self.layout.topbar_rect.bottom + 10, 680, 170)
            pygame.draw.rect(s, (8, 8, 12), d, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], d, 2, border_radius=8)
            sel = None
            if self.ctrl.selected_index is not None and self.ctrl.selected_index < len(hand):
                sel = getattr(hand[self.ctrl.selected_index].definition, "id", "-")
            sel = sel or "-"
            info_lines = [
                f"selected_card: {sel}",
                f"draw/hand/discard: {self._pile_counts()['draw']}/{self._pile_counts()['hand']}/{self._pile_counts()['discard']}",
                f"fsm={self._action_button_fsm} reason={self._last_reason_code}",
                f"harmony: {p.get('harmony_current',0)}/{p.get('harmony_max',10)} thr={p.get('harmony_ready_threshold',6)}",
                f"last_trigger: {self.last_trigger}",
            ]
            ok, reason_code, reason_text = self._selected_card_play_state()
            info_lines.append(f"can_play={ok} reason={reason_code} ({reason_text})")
            if self.ctrl.selected_index is not None and self.ctrl.selected_index < len(hand):
                sc = hand[self.ctrl.selected_index]
                info_lines.append(f"energy={p.get('energy',0)} cost={sc.cost} target_ok={any(e.alive for e in self.c.enemies)}")
            yy = d.y + 12
            for line in info_lines:
                s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (d.x + 12, yy))
                yy += 28

        if self.art_debug_overlay:
            idx = self.hover_card_index if self.hover_card_index is not None else self.ctrl.selected_index
            card = hand[idx] if idx is not None and idx < len(hand) else None
            info = self._art_debug_info(card)
            d = pygame.Rect(self.layout.topbar_rect.x + 10, self.layout.topbar_rect.bottom + 168, 760, 188)
            pygame.draw.rect(s, (0, 0, 0), d, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], d, 2, border_radius=8)
            y = d.y + 12
            for line in [
                f"card_id: {info['card_id']}",
                f"card_type/family: {info['card_type']}",
                f"expected art_path: {info['art_path']}",
                f"file_exists: {info['file_exists']}",
                f"manifest_status: {info['manifest_status']}",
                f"generator_used: {info['generator_used']}",
                f"prompt_used: {info['prompt_used']}",
            ]:
                s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (d.x + 12, y))
                y += 24

        if self.pause_open:
            ov = pygame.Surface((s.get_width(), s.get_height()), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 150))
            s.blit(ov, (0, 0))
            panel = pygame.Rect(s.get_width() // 2 - 280, s.get_height() // 2 - 210, 560, 420)
            pygame.draw.rect(s, UI_THEME["deep_purple"], panel, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=16)
            s.blit(self.app.big_font.render("PAUSA", True, UI_THEME["gold"]), (panel.centerx - 90, panel.y + 20))

            options = [("continue", "Continuar", panel.y + 84), ("map", "Salir al mapa", panel.y + 170), ("menu", "Salir al menú principal", panel.y + 256)]
            for key, lbl, y in options:
                r = pygame.Rect(panel.x + 80, y, 400, 64)
                active_confirm = self.pause_confirm_target == key and key in {"map", "menu"}
                btn_col = (132, 86, 94) if active_confirm else UI_THEME["panel"]
                pygame.draw.rect(s, btn_col, r, border_radius=10)
                pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=10)
                title = f"{lbl} (confirmar)" if active_confirm else lbl
                tw = self.app.font.render(title, True, UI_THEME["text"])
                s.blit(tw, (r.centerx - tw.get_width() // 2, r.y + 18))

            if self.pause_confirm_target in {"map", "menu"}:
                msg = "Pulsa de nuevo para confirmar salida."
                hint = self.app.small_font.render(msg, True, UI_THEME["muted"])
                s.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 340))

        self.scry_picker.render(s, self.app)
