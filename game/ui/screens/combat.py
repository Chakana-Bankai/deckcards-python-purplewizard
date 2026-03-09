from __future__ import annotations

import math
from pathlib import Path

import pygame

from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.combat.play_validation import can_play_card, can_play, reason_to_es, REASON_OK
from game.ui.anim import TypewriterBanner
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.card_renderer import render_card_large, render_card_medium
from game.ui.components.mana_orbs import ManaOrbsWidget
from game.ui.components.modal_card_picker import ModalCardPicker
from game.ui.controllers.card_interaction import CardInteractionController
from game.ui.controllers.combat_dialogue_controller import CombatDialogueController
from game.ui.controllers.dialogue_router import DialogueRouter
from game.ui.layout.combat_layout import build_combat_layout
from game.ui.theme import UI_THEME
from game.ui.system.layers import Layers
from game.ui.system.components import UIPanel, UITooltip
from game.ui.system.colors import UColors
from game.ui.system.icons import draw_icon_with_value
from game.ui.components.topbar import CombatTopBar
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

        self.combat_start_t = pygame.time.get_ticks() / 1000.0
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
        self._invalid_state_since_ms = 0
        self._cost_pulse_until = {}
        self.telemetry = TelemetryLogger("INFO")
        self.dialogue_ctrl = CombatDialogueController(self.app.lore_engine, self._set_dialogue_lines)
        self.dialog_router = DialogueRouter(self.app.lore_engine, cooldown_ms=850, action_gap=2)
        self._dialogue_action_idx = 0
        self.last_enemy_line = ""
        self.last_player_line = ""
        self.enemy_voice_label = "VOZ ENEMIGA"
        self.chakana_voice_label = "VOZ CHAKANA"
        self.topbar = CombatTopBar()
        self.scry_picker = ModalCardPicker()
        self.layout = build_combat_layout(1920, 1080)
        self.end_turn_rect = pygame.Rect(0, 0, 1, 1)
        self.harmony_seal_rect = pygame.Rect(0, 0, 1, 1)
        self._player_low_hp_active = False
        self._enemy_low_hp_active: set[str] = set()
        self.combat_start_t = pygame.time.get_ticks() / 1000.0
        self._reset_encounter_ui_state()
        print("[combat_reset] seal/harmony/action state reset OK")
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.set_dialogue("combat_start", enemy_id, {})

        self._tutorial_targets: dict[str, pygame.Rect] = {}
        self._relic_chip_rects: list[tuple[pygame.Rect, str]] = []
        flow = getattr(self.app, "tutorial_flow", None)
        if flow is not None:
            flow.on_combat_enter()
            if hasattr(self.app, "_sync_tutorial_run_state"):
                self.app._sync_tutorial_run_state()



    def _reset_encounter_ui_state(self):
        """Reset combat-only UI/session caches for a clean encounter start."""
        self.ctrl.clear_selection("combat_init")
        self.ctrl.clear_hover()
        self.hover_card_index = None

        self._action_state = "END_TURN"
        self._action_state_reason = "combat_init"
        self._action_button_fsm = "IDLE"
        self._last_reason_code = REASON_OK
        self._status_line = ""
        self._invalid_feedback_until_ms = 0
        self._invalid_feedback_msg = ""
        self._invalid_state_since_ms = 0
        self._ui_lock_until_ms = 0

        self._player_low_hp_active = False
        self._enemy_low_hp_active = set()

        self.dialog_cd = 0.0
        self.enemy_line_fx = 0.0
        self.hero_line_fx = 0.0
        self._dialogue_action_idx = 0
        self.last_enemy_line = ""
        self.last_player_line = ""
        self.enemy_voice_label = "VOZ ENEMIGA"
        self.chakana_voice_label = "VOZ CHAKANA"
        self.last_trigger = "combat_start"

        self.actions_log.clear()
        self._cost_pulse_until.clear()

        # Reset dialogue router memory so encounter lines start fresh.
        self.dialog_router.last_ms = 0
        self.dialog_router.last_priority = -1
        self.dialog_router.last_action_index = -999

        self.pause_open = False
        self.pause_confirm_target = None


    def on_leave(self):
        self.ctrl.clear_selection("screen_change")

    def _refresh_layout(self, surface: pygame.Surface):
        self.layout = build_combat_layout(surface.get_width(), surface.get_height())
        base_w = max(280, int(self.layout.actions_rect.w * 0.60))
        base_h = max(74, int(self.layout.actions_rect.h * 0.68))
        btn_w = min(self.layout.actions_rect.w - 26, int(base_w * 1.18))
        btn_h = min(self.layout.actions_rect.h - 26, int(base_h * 1.06))
        top_band = 10
        btn_y = self.layout.actions_rect.y + top_band + max(0, (self.layout.actions_rect.h - top_band - btn_h - 4) // 2)
        self.end_turn_rect = pygame.Rect(self.layout.actions_rect.centerx - btn_w // 2, btn_y, btn_w, btn_h)
        self.harmony_seal_rect = pygame.Rect(self.layout.harmony_rect.centerx - 62, self.layout.harmony_rect.bottom - 28, 124, 22)

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
        payload = dict(ctx or {})
        payload.setdefault("action_index", self._dialogue_action_idx)
        self._dialogue_action_idx += 1
        picked = self.dialog_router.pick(enemy_id, trigger, payload)
        if picked is None:
            return
        enemy_line, hero_line, mapped_trigger = picked
        if enemy_line == self.last_enemy_line and hero_line == self.last_player_line:
            enemy_line, hero_line = "La Trama cambia de tono.", "Escucho y respondo."
        self._set_dialogue_lines(enemy_line, hero_line, mapped_trigger)
        self.last_enemy_line, self.last_player_line = enemy_line, hero_line
        self._update_voice_labels(mapped_trigger, enemy_id)
        print(f"[dlg] trigger={mapped_trigger} enemy={enemy_id} ctx={payload}")

    def _update_voice_labels(self, mapped_trigger: str, enemy_id: str):
        event_label = {
            "combat_start": "RITO INICIAL",
            "enemy_intent": "INTENCION",
            "attack_played": "REACCION AL GOLPE",
            "block_played": "REACCION AL BLOQUEO",
            "seal_ready": "PRESAGIO",
            "seal_release": "DESCARGA",
            "player_low_hp": "PRESION FINAL",
            "enemy_low_hp": "QUIEBRE",
            "victory": "EPILOGO",
            "defeat": "CAIDA",
        }.get(str(mapped_trigger or ""), "ECO")
        enemy_name = str(enemy_id or "enemigo").replace("_", " ").upper()
        self.enemy_voice_label = f"{enemy_name} - {event_label}"
        self.chakana_voice_label = f"CHAKANA - {event_label}"

    def _card_playable(self, card) -> bool:
        ok, _reason_code, _reason_text = can_play_card(card, self.c.player, self.c)
        return bool(ok)

    def _selected_card_play_state(self):
        idx = self.ctrl.selected_index
        if idx is None or idx >= len(self.c.hand):
            return False, "OTHER", "Sin seleccion"
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

    def _clear_invalid_feedback(self):
        self._invalid_feedback_until_ms = 0
        self._invalid_feedback_msg = ""


    def _reset_seal_action_state(self, reason: str = ""):
        self._action_button_fsm = "IDLE"
        self._action_state = "END_TURN"
        self._action_state_reason = REASON_OK
        self._invalid_state_since_ms = 0
        self._clear_invalid_feedback()
        self.ctrl.clear_selection(reason or "seal_reset")

    def _resolve_action_state(self):
        p = self.c.player
        h_cur = int(p.get("harmony_current", 0) or 0)
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        seal_used = bool(p.get("harmony_seal_used", False))

        hand_empty = len(self.c.hand) <= 0
        if hand_empty and (h_cur >= h_thr or seal_used):
            self._reset_seal_action_state("hand_empty")
        if self._ui_locked() or self.resolving_t > 0:
            fsm, state, reason, label, disabled = "LOCKED_COOLDOWN", "INVALID", "STATE_LOCK", "BLOQUEADO", True
        else:
            idx = self.ctrl.selected_index
            if idx is None or idx >= len(self.c.hand):
                if h_cur >= h_thr and not seal_used:
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
                    fsm, state, reason, label, disabled = "CARD_INVALID", "INVALID", reason_code, "ACCION INVALIDA", False
                    self._status_line = reason_text

        now_ms = pygame.time.get_ticks()
        if state == "INVALID":
            if self._invalid_state_since_ms <= 0:
                self._invalid_state_since_ms = now_ms
        else:
            self._invalid_state_since_ms = 0

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

    def _update_low_hp_dialogue_edges(self):
        player_hp = int(self.c.player.get("hp", 0) or 0)
        player_max = max(1, int(self.c.player.get("max_hp", 1) or 1))
        player_threshold = max(10, int(player_max * 0.3))
        player_is_low = player_hp <= player_threshold
        if player_is_low and not self._player_low_hp_active:
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("player_low_hp", enemy_id, {"hp": player_hp, "threshold": player_threshold})
            if hasattr(self.app, "trigger_oracle"):
                self.app.trigger_oracle("player_low_hp", {"hp": player_hp, "threshold": player_threshold, "id": enemy_id})
        self._player_low_hp_active = player_is_low

        alive_enemy_ids = {str(e.id) for e in self.c.enemies if getattr(e, "alive", False)}
        self._enemy_low_hp_active.intersection_update(alive_enemy_ids)

        triggered_enemy_id = None
        for enemy in self.c.enemies:
            if not getattr(enemy, "alive", False):
                continue
            enemy_id = str(enemy.id)
            enemy_threshold = max(1, int(enemy.max_hp * 0.25))
            enemy_is_low = int(enemy.hp) <= enemy_threshold
            was_low = enemy_id in self._enemy_low_hp_active
            if enemy_is_low and not was_low:
                self._enemy_low_hp_active.add(enemy_id)
                if triggered_enemy_id is None:
                    triggered_enemy_id = enemy_id
            elif (not enemy_is_low) and was_low:
                self._enemy_low_hp_active.discard(enemy_id)

        if triggered_enemy_id is not None:
            self.set_dialogue("enemy_low_hp", triggered_enemy_id, {})
            if hasattr(self.app, "trigger_oracle"):
                self.app.trigger_oracle("enemy_low_hp", {"id": triggered_enemy_id})

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
        trig = "attack_played" if "attack" in tags else "block_played"
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
            if ok:
                self._push_log(str(msg or "SELLO activado"))
                self._lock_ui()
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                self.set_dialogue("seal_release", enemy_id, {})
            else:
                txt = str(msg or "No se pudo activar el sello")
                low = txt.lower()
                if "ya usado" in low:
                    txt = "Sello ya usado en este combate."
                    self._reset_seal_action_state("seal_already_used")
                self._set_invalid_feedback(txt)
                if not self.actions_log or str(self.actions_log[-1]) != txt:
                    self._push_log(txt)
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
            flow = getattr(self.app, "tutorial_flow", None)
            if flow is not None:
                flow.on_end_turn_pressed()
            self.c.end_turn()
            self._reset_seal_action_state("end_turn")
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

    def _card_pose(self, i, total):
        inner = self.layout.hand_rect.inflate(-20, -40)
        total = max(1, int(total or 1))
        card_w = 236
        card_h = max(260, inner.h - 12)
        mid = (total - 1) / 2.0
        offset_x = 60
        rotation_step = 4.0
        dx = i - mid
        cx = int(inner.centerx + dx * offset_x)
        arc = int(abs(dx) ** 1.35 * 5)
        cy = inner.y + card_h // 2 + 6 + arc
        rect = pygame.Rect(0, 0, card_w, card_h)
        rect.center = (cx, cy)

        # Keep a safe bottom margin so cards never invade end-turn button zone.
        safe_bottom = inner.bottom
        button_guard = self.end_turn_rect.inflate(18, 22)
        if rect.colliderect(button_guard):
            safe_bottom = min(safe_bottom, button_guard.y - 12)
        if rect.bottom > safe_bottom:
            rect.y -= (rect.bottom - safe_bottom)

        rect.x = max(inner.x + 2, min(inner.right - rect.w - 2, rect.x))
        rect.y = max(inner.y + 2, rect.y)
        angle = float(dx * rotation_step)
        return rect, angle

    def _card_rect(self, i, total):
        rect, _angle = self._card_pose(i, total)
        return rect

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
    def _intent_value_text(self, enemy) -> str:
        intent = enemy.current_intent() if enemy is not None else {}
        kind = str(intent.get("intent", "")).lower()
        value = intent.get("value", 0)
        if isinstance(value, list):
            lo = int(value[0]) if value else 0
            hi = int(value[1]) if len(value) > 1 else lo
            amount = f"{lo}-{hi}" if lo != hi else str(lo)
        else:
            amount = str(int(value or 0))
        if kind == "attack":
            return f"ATK {amount}"
        if kind == "defend":
            return f"DEF {amount}"
        if kind == "debuff":
            return f"DEBUF {max(1, int(intent.get('stacks', 1) or 1))}"
        if kind == "buff":
            return f"BUFF {max(1, int(intent.get('stacks', 1) or 1))}"
        return "INTENCION"

    def _enemy_major_statuses(self, enemy) -> list[tuple[str, int]]:
        st = getattr(enemy, "statuses", {}) or {}
        mapping = [
            ("rupture", int(st.get("rupture", 0) or 0) + int(st.get("break", 0) or 0)),
            ("ritual", int(st.get("ritual", 0) or 0)),
            ("support", int(st.get("weak", 0) or 0)),
            ("support", int(st.get("vulnerable", 0) or 0)),
        ]
        out = [(k, v) for k, v in mapping if v > 0]
        return out[:3]

    def _player_attack_cue(self) -> int:
        idx = self.ctrl.selected_index
        card = self.c.hand[idx] if idx is not None and 0 <= idx < len(self.c.hand) else None
        if card is None:
            card = next((c for c in self.c.hand if self._card_playable(c)), None)
        if card is None:
            return 0
        summary = summarize_card_effect(card.definition, card_instance=card, ctx=self.c) or {}
        return max(0, int(summary.get("damage", 0) or 0))
    def _enemy_presence_variant(self, enemy) -> str:
        eid = str(getattr(enemy, "id", "")).lower()
        name = str(getattr(enemy, "name_key", "")).lower()
        tier = str(getattr(enemy, "tier", "")).lower()
        if any(k in f"{eid} {name} {tier}" for k in ["angel", "seraph", "sacred", "light"]):
            return "angelic"
        if any(k in f"{eid} {name} {tier}" for k in ["demon", "void", "shadow", "abyss"]):
            return "demonic"
        if any(k in f"{eid} {name} {tier}" for k in ["nephilim", "giant", "titan", "astral"]):
            return "nephilim"
        return "nephilim" if tier == "boss" else "angelic"

    def _draw_enemy_geometry_overlay(self, s: pygame.Surface, rect: pygame.Rect, intent_col: tuple[int, int, int], variant: str, boss_factor: float, t: float):
        pad = 6
        frame = rect.inflate(pad * 2, pad * 2)
        geo = pygame.Surface((frame.w, frame.h), pygame.SRCALPHA)

        if variant == "angelic":
            geo_col = (232, 220, 170)
            rings = [0.30, 0.46, 0.62]
        elif variant == "demonic":
            geo_col = (226, 96, 118)
            rings = [0.28, 0.44, 0.58]
        else:
            geo_col = (174, 146, 248)
            rings = [0.34, 0.52, 0.68]

        cx, cy = frame.w // 2, frame.h // 2
        r0 = int(min(frame.w, frame.h) * 0.42)
        for idx, mul in enumerate(rings):
            rr = max(8, int(r0 * mul))
            alpha = int((54 + idx * 16) * boss_factor)
            pygame.draw.circle(geo, (*geo_col, alpha), (cx, cy), rr, 1)

        # Rotating diamond/star overlay tuned by variant.
        spin = t * (0.9 + 0.22 * boss_factor)
        spike = 7 if variant == "demonic" else 4 if variant == "angelic" else 8
        poly = []
        for i in range(spike):
            ang = spin + (2 * math.pi * i / spike)
            rad = r0 * (0.44 if i % 2 == 0 else 0.24)
            poly.append((cx + int(math.cos(ang) * rad), cy + int(math.sin(ang) * rad)))
        pygame.draw.polygon(geo, (*intent_col, int(40 * boss_factor)), poly, 1)

        if boss_factor > 1.2:
            # Boss-only sacred grid with subtle wobble.
            gw = max(1, int(frame.w * 0.12))
            off = int(3 * math.sin(t * 1.7))
            for x in range(gw // 2, frame.w, gw):
                pygame.draw.line(geo, (*geo_col, 22), (x + off, 0), (x + off, frame.h), 1)
            for y in range(gw // 2, frame.h, gw):
                pygame.draw.line(geo, (*geo_col, 22), (0, y - off), (frame.w, y - off), 1)

        pygame.draw.rect(geo, (*intent_col, int(72 * boss_factor)), geo.get_rect(), 2, border_radius=16)
        s.blit(geo, (frame.x, frame.y))

    def _draw_enemy_aura(self, s: pygame.Surface, avatar_rect: pygame.Rect, intent_col: tuple[int, int, int], boss_factor: float, variant: str, t: float, clip_rect: pygame.Rect | None = None):
        # RGB 2.1: stronger side glow footprint and layered pulse.
        old_clip = s.get_clip()
        if clip_rect is not None:
            s.set_clip(clip_rect)
        layer_count = 5 if boss_factor > 1.2 else 4
        base_phase = 2.65 if boss_factor > 1.2 else 2.05
        variant_shift = 0.35 if variant == "angelic" else 0.72 if variant == "demonic" else 1.05

        side_pad = int(24 * boss_factor)
        side_rect = avatar_rect.inflate(side_pad * 2, int(avatar_rect.h * 0.30))
        side_rect.centery = avatar_rect.centery + 2
        side_glow = pygame.Surface((side_rect.w, side_rect.h), pygame.SRCALPHA)
        for layer in range(layer_count):
            phase = t * (base_phase + layer * 0.29) + variant_shift
            wave = 0.5 + 0.5 * math.sin(phase)
            alpha = int((58 + layer * 26 + 36 * wave) * (1.22 if boss_factor > 1.2 else 1.08))
            band_h = max(16, int(side_rect.h * (0.24 + layer * 0.11)))
            band = pygame.Surface((side_rect.w, band_h), pygame.SRCALPHA)
            band.fill((*intent_col, max(24, min(236, alpha))))
            by = max(0, side_rect.h // 2 - band_h // 2 + int((layer - 1) * 2))
            side_glow.blit(band, (0, by))
        s.blit(side_glow, side_rect.topleft)

        # Base aura and floor ribbons to keep enemy anchored and premium.
        for layer in range(layer_count):
            phase = t * (base_phase + layer * 0.33) + variant_shift
            wave = 0.5 + 0.5 * math.sin(phase)
            width_mul = 1.02 + layer * 0.24 + 0.20 * wave
            aura_w = int(avatar_rect.w * width_mul)
            aura_h = int((13 + 5 * layer) * boss_factor)
            aura_x = avatar_rect.centerx - aura_w // 2
            aura_y = avatar_rect.bottom - 14 + layer * 2
            alpha = int((122 + layer * 30 + 28 * wave) * (1.16 if boss_factor > 1.2 else 1.03))
            aura = pygame.Surface((aura_w, aura_h), pygame.SRCALPHA)
            aura.fill((*intent_col, max(30, min(244, alpha))))
            s.blit(aura, (aura_x, aura_y))

        if boss_factor > 1.2:
            # Boss-only extra pulse shell for separation from busy backgrounds.
            pulse = 0.5 + 0.5 * math.sin(t * 2.2)
            shell = avatar_rect.inflate(int(48 + 22 * pulse), int(34 + 16 * pulse))
            shell_surf = pygame.Surface((shell.w, shell.h), pygame.SRCALPHA)
            pygame.draw.rect(shell_surf, (*intent_col, int(88 + 56 * pulse)), shell_surf.get_rect(), 2, border_radius=24)
            s.blit(shell_surf, shell.topleft)
        if clip_rect is not None:
            s.set_clip(old_clip)

    def _topbar_narrative(self):
        run = self.app.run_state or {}
        deck_name = str(run.get("deck_name") or run.get("starter_name") or "Inicial")
        left = f"Chakana | Mazo: {deck_name}"

        node = self.app.node_lookup.get(self.app.current_node_id) if getattr(self.app, "current_node_id", None) else None
        pacha = self.app.get_biome_display_name(self.selected_biome or run.get("biome"))
        if isinstance(node, dict):
            node_name = "Elite" if node.get("type") == "challenge" else self.app.loc.t(f"node_{node.get('type', 'combat')}")
        else:
            node_name = "Nodo desconocido"
        center = f"{pacha} - {node_name}"
        subtitle = str(self.app.lore_engine.get_map_narration("default") if hasattr(self.app, "lore_engine") else "")

        timer_text = f"{self.turn_timer_left:04.1f}s" if self.turn_timer_enabled else "--"
        turn_text = f"Turno {int(self.c.turn) if hasattr(self.c, 'turn') else '-'}"
        return left, center, subtitle, timer_text, turn_text

    def _mark_current_node_incomplete(self):
        node = self.app.node_lookup.get(self.app.current_node_id) if getattr(self.app, "current_node_id", None) else None
        if isinstance(node, dict) and node.get("state") not in {"cleared", "completed"}:
            node["state"] = "incomplete"

    def _tutorial_hint(self):
        flow = getattr(self.app, "tutorial_flow", None)
        if flow is None:
            return None
        return flow.current_hint("combat")

    def _render_tutorial_overlay(self, s: pygame.Surface):
        hint = self._tutorial_hint()
        if not hint or self.pause_open:
            return

        target_key = str(hint.get("target", ""))
        target = self._tutorial_targets.get(target_key)
        if target is None:
            return

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 220.0)
        frame = target.inflate(14, 14)
        glow = pygame.Surface((frame.w, frame.h), pygame.SRCALPHA)
        pygame.draw.rect(glow, (214, 168, 255, int(58 + 54 * pulse)), glow.get_rect(), 3, border_radius=12)
        s.blit(glow, frame.topleft)
        pygame.draw.rect(s, UI_THEME["gold"], target, 2, border_radius=10)

        panel = pygame.Rect(20, self.layout.topbar_rect.bottom + 8, 700, 124)
        pygame.draw.rect(s, (30, 22, 44), panel, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], panel, 2, border_radius=10)

        title = f"Tutorial {hint.get('index', 1)}/{hint.get('total', 1)} - {hint.get('title', '')}"
        s.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (panel.x + 14, panel.y + 10))

        yy = panel.y + 44
        for line in hint.get("lines", [])[:2]:
            s.blit(self.app.tiny_font.render(str(line), True, UI_THEME["text"]), (panel.x + 14, yy))
            yy += 24

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

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            flow = getattr(self.app, "tutorial_flow", None)
            if flow is not None and flow.current_hint("combat"):
                flow.manual_advance()
                if hasattr(self.app, "_sync_tutorial_run_state"):
                    self.app._sync_tutorial_run_state()
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
                    flow = getattr(self.app, "tutorial_flow", None)
                    if flow is not None:
                        flow.on_hand_clicked()
                    self.ctrl.on_card_click(i)
                    in_card = True
                    sel = self.c.hand[i] if i < len(self.c.hand) else None
                    ok_code, reason_code, reason_text = can_play(sel, self.c) if sel else (False, "OTHER", "No se puede jugar")
                    self._last_reason_code = reason_code
                    self.telemetry.info("card_click", card_id=getattr(getattr(sel, "definition", None), "id", "-"), ok=ok_code, reason_code=reason_code)
                    if not ok_code:
                        self._status_line = reason_text
                        self._push_log(f"No se puede jugar: {reason_text}")
                    else:
                        self._clear_invalid_feedback()
                    break
            if not in_card:
                self.ctrl.clear_selection("click_outside")
                self._clear_invalid_feedback()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            button_id = "action" if self.end_turn_rect.collidepoint(pos) else None
            if self.ctrl.on_mouse_up(button_id):
                self._activate_action_button()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._execute_selected()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            self._push_log("Armonia: se carga con rituales. Cuando esta LISTA, potencia defensas o activa SELLO.")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.harmony_seal_rect.collidepoint(pos):
                state, _label, disabled, _reason = self._resolve_action_state()
                if state == "RELEASE_SEAL" and not disabled:
                    self._activate_action_button()

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

    def _draw_card(self, s, rect, card, selected=False, family="violet_arcane", hovered=False, angle=0.0):
        state = {
            "app": self.app,
            "ctx": self.c,
            "family": family,
            "selected": bool(selected),
            "hovered": bool(hovered),
            "cost_pulse_until": self._cost_pulse_until,
            "render_context": "hover_view" if hovered else "hand_view",
        }
        target = pygame.Rect(rect)
        if abs(float(angle or 0.0)) > 0.01 and not hovered:
            tmp = pygame.Surface((target.w, target.h), pygame.SRCALPHA)
            if target.h >= 450 or target.w >= 420:
                render_card_large(tmp, tmp.get_rect(), card, theme=UI_THEME, state=state)
            else:
                render_card_medium(tmp, tmp.get_rect(), card, theme=UI_THEME, state=state)
            rotated = pygame.transform.rotozoom(tmp, -float(angle), 1.0)
            s.blit(rotated, rotated.get_rect(center=target.center).topleft)
            return
        if target.h >= 450 or target.w >= 420:
            render_card_large(s, target, card, theme=UI_THEME, state=state)
        else:
            render_card_medium(s, target, card, theme=UI_THEME, state=state)

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
                self._reset_seal_action_state("timer_end_turn")
                self._push_log("Jugada: Fin de turno (timer)")
                self.ctrl.clear_selection("timer_end_turn")
                self.ctrl.clear_hover()
                self.turn_timer_left = self.turn_timer_limit

        if self.last_turn != self.c.turn:
            self.last_turn = self.c.turn
            flow = getattr(self.app, "tutorial_flow", None)
            if flow is not None:
                flow.on_turn_advanced()
            self.turn_timer_left = self.turn_timer_limit
            self._reset_seal_action_state("hand_refill")
            self._trigger_dialog("player_turn_start")
            enemy = self.c.enemies[0] if self.c.enemies else None
            if enemy is not None:
                self.set_dialogue("enemy_intent", enemy.id, {"intent": enemy.current_intent().get("label", "")})

        for ev in self.c.pop_events():
            if ev.get("type") == "damage" and ev.get("target") == "player" and ev.get("amount", 0) >= 8:
                self._trigger_dialog("enemy_big_attack")
                self._push_log(f"Dano recibido: {ev.get('amount',0)}")
            if ev.get("type") == "card_played":
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                card_id = str(ev.get("card_id", ""))
                card_def = next((c for c in self.app.cards_data if c.get("id") == card_id), {}) if card_id else {}
                tags = set(card_def.get("tags", []) if isinstance(card_def, dict) else [])
                trig = "attack_played" if "attack" in tags else "block_played"
                self.set_dialogue(trig, enemy_id, {"card_id": card_id})
                flow = getattr(self.app, "tutorial_flow", None)
                if flow is not None:
                    is_block = ("skill" in tags) or ("block" in tags)
                    flow.on_card_played(is_block, int(self.c.player.get("block", 0) or 0))
            if ev.get("type") == "card_cost_changed":
                if ev.get("in_hand"):
                    iid = str(ev.get("instance_id") or "")
                    old_c = int(ev.get("old_cost", 0) or 0)
                    new_c = int(ev.get("new_cost", 0) or 0)
                    if iid and new_c < old_c:
                        self._cost_pulse_until[iid] = pygame.time.get_ticks() + 950
            if ev.get("type") == "harmony_ready":
                self._push_log(str(ev.get("message") or "Armonia lista: desata tu sello."))
                try:
                    self.app.sfx.play("stinger_seal_ready")
                except Exception:
                    pass
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                self.set_dialogue("seal_ready", enemy_id, {})
            if ev.get("type") == "enemy_action":
                self.set_dialogue("enemy_intent", str(ev.get("enemy") or "default"), {"intent": str(ev.get("intent") or "")})
                flow = getattr(self.app, "tutorial_flow", None)
                if flow is not None:
                    flow.on_enemy_intent_seen()
            if ev.get("type") == "harmony_seal":
                self._push_log(str(ev.get("message") or "SELLO activado"))
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                self.set_dialogue("seal_release", enemy_id, {})

        if self.c.scry_pending and not self.scry_picker.open:
            self.scry_picker.show(
                self.c.scry_pending,
                on_confirm=lambda card: self.c.apply_scry_keep(card),
                on_cancel=lambda: self.c.apply_scry_keep(None),
            )

        self._update_low_hp_dialogue_edges()

        flow = getattr(self.app, "tutorial_flow", None)
        if flow is not None:
            pstate = self.c.player or {}
            h_cur = int(pstate.get("harmony_current", 0) or 0)
            h_thr = max(1, int(pstate.get("harmony_ready_threshold", 6) or 6))
            flow.on_harmony_progress(h_cur, h_cur >= h_thr)
            if hasattr(self.app, "_sync_tutorial_run_state"):
                self.app._sync_tutorial_run_state()

        self.ctrl.validate_selection(len(self.c.hand))
        state, _label, disabled, _reason = self._resolve_action_state()
        if state != "INVALID" and not disabled and self._invalid_feedback_until_ms > 0:
            self._clear_invalid_feedback()

        # Auto-clear stale INVALID selection to avoid sticky FSM states.
        if state == "INVALID" and not self._ui_locked() and self.ctrl.selected_index is not None:
            now_ms = pygame.time.get_ticks()
            if self._invalid_state_since_ms > 0 and (now_ms - self._invalid_state_since_ms) >= 1200:
                self.ctrl.clear_selection("invalid_timeout_reset")
                self._status_line = ""
                self._clear_invalid_feedback()
                self._invalid_state_since_ms = 0
        if self.c.result == "victory":
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("victory", enemy_id, {})
            self._reset_seal_action_state("combat_end_victory")
            self._push_log("Combate ganado")
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self._reset_seal_action_state("combat_end_defeat")
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            self.set_dialogue("defeat", enemy_id, {})
            self._push_log("Combate perdido")
            self.app.goto_end(victory=False)

        flow_done = getattr(self.app, "tutorial_flow", None)
        if flow_done is not None and flow_done.consume_completed() and hasattr(self.app, "mark_tutorial_completed"):
            self.app.mark_tutorial_completed()

    def render(self, s):
        self._refresh_layout(s)

        # LAYER 1: background (Layers.LAYER_BACKGROUND)
        self.app.bg_gen.render_parallax(
            s,
            self.selected_biome,
            self.bg_seed,
            pygame.time.get_ticks() * 0.02,
            clip_rect=pygame.Rect(0, 0, s.get_width(), self.layout.voices_rect.bottom + 12),
            particles_on=self.app.user_settings.get("fx_particles", True),
        )

        # LAYER 2: board (Layers.LAYER_BOARD)
        left, center, subtitle, timer_text, turn_text = self._topbar_narrative()
        self.topbar.render(s, self.app, self.layout, left, center, subtitle, timer_text, turn_text)
        UIPanel(self.layout.enemy_strip_rect).draw(s)

        enemy_count = max(1, len(self.c.enemies))
        inner_strip = self.layout.enemy_strip_rect.inflate(-24, -18)
        card_w = (inner_strip.w - (enemy_count - 1) * 16) // enemy_count
        if enemy_count == 1:
            card_w = min(inner_strip.w - 40, int(inner_strip.w * 0.74))
            enemy_start_x = inner_strip.centerx - card_w // 2
        else:
            enemy_start_x = inner_strip.x
        t = pygame.time.get_ticks() / 1000.0

        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(enemy_start_x + i * (card_w + 16), inner_strip.y, card_w, inner_strip.h)
            content = er.inflate(-8, -8)
            pygame.draw.rect(s, UI_THEME["deep_purple"], content, border_radius=13)
            pygame.draw.rect(s, UI_THEME["accent_violet"], content, 2, border_radius=13)

            ratio = max(0, e.hp) / max(1, e.max_hp)
            avatar_min_w = 300 if enemy_count == 1 else 170
            info_ratio = 0.40 if enemy_count == 1 else 0.46
            info_cap = max(180, int(content.w - avatar_min_w - 56))
            info_col_w = max(220, min(int(content.w * info_ratio), info_cap))
            info_col = pygame.Rect(content.x + 20, content.y + 12, info_col_w, content.h - 24)
            avatar_w = max(avatar_min_w, content.right - (info_col.right + 30))
            avatar_rect = pygame.Rect(content.right - avatar_w - 12, content.y + 16, avatar_w, content.h - 32)
            title = pygame.Rect(info_col.x, info_col.y, info_col.w, 28)
            hp_label = pygame.Rect(info_col.x, title.bottom + 2, info_col.w, 36)
            intent_line = pygame.Rect(info_col.x, hp_label.bottom + 6, info_col.w, 48)
            block_line = pygame.Rect(info_col.x, intent_line.bottom + 5, info_col.w, 30)
            status_line = pygame.Rect(info_col.x, block_line.bottom + 4, info_col.w, 22)
            hp_bar = pygame.Rect(info_col.x, info_col.bottom - 14, info_col.w, 8)
            counters = pygame.Rect(info_col.x, info_col.bottom - 34, info_col.w, 16)

            enemy_name = str(e.name_key)
            intent_name = str(e.current_intent().get("label", "..."))
            s.blit(self.app.small_font.render(enemy_name, True, UI_THEME["text"]), (title.x, title.y))
            hp_txt = self.app.big_font.render(f"{e.hp}/{e.max_hp}", True, UI_THEME["hp"])
            s.blit(hp_txt, (hp_label.x, hp_label.y - 2))

            intent_col = self._intent_led_color(e)
            intent_value = self._intent_value_text(e)
            enemy_block = max(0, int(getattr(e, "block", 0) or 0))
            intent_chip = pygame.Rect(intent_line.x, intent_line.y, info_col.w, intent_line.h)
            if i == 0:
                self._tutorial_targets["enemy_intent"] = pygame.Rect(intent_chip)

            chip_glow = pygame.Surface((intent_chip.w + 12, intent_chip.h + 10), pygame.SRCALPHA)
            pygame.draw.rect(chip_glow, (*intent_col, 84), chip_glow.get_rect(), border_radius=14)
            s.blit(chip_glow, (intent_chip.x - 6, intent_chip.y - 5))
            pygame.draw.rect(s, (24, 22, 34), intent_chip, border_radius=12)
            pygame.draw.rect(s, intent_col, intent_chip, 2, border_radius=12)
            kind = str(e.current_intent().get("intent", "")).lower()
            icon_name = "damage" if kind == "attack" else "block" if kind == "defend" else "ritual"
            val_num = 0
            vraw = e.current_intent().get("value", 0)
            if isinstance(vraw, list) and vraw:
                val_num = int(vraw[-1] or 0)
            else:
                val_num = int(vraw or 0)
            draw_icon_with_value(s, icon_name, val_num, intent_col, self.app.small_font, intent_chip.x + 10, intent_chip.y + 7, size=2)
            intent_line_text = self._wrap_panel_text(intent_name, intent_chip.w - 24, max_lines=1)[0]
            intent_name_txt = self.app.tiny_font.render(intent_line_text, True, UI_THEME["text"])
            s.blit(intent_name_txt, (intent_chip.x + 14, intent_chip.bottom - 14))
            blk_col = UI_THEME["block"] if enemy_block > 0 else UI_THEME["muted"]
            block_chip = pygame.Rect(block_line.x, block_line.y, max(132, int(block_line.w * 0.46)), block_line.h)
            pygame.draw.rect(s, (24, 22, 34), block_chip, border_radius=10)
            pygame.draw.rect(s, blk_col, block_chip, 2, border_radius=10)
            draw_icon_with_value(s, "block", enemy_block, blk_col, self.app.tiny_font, block_chip.x + 8, block_chip.y + 6, size=1)

            status_tokens = self._enemy_major_statuses(e)
            sx = status_line.x
            for icon_id, val in status_tokens:
                ww = 78
                rr = pygame.Rect(sx, status_line.y + 1, ww, 19)
                pygame.draw.rect(s, (28, 24, 40), rr, border_radius=7)
                pygame.draw.rect(s, UI_THEME["accent_violet"], rr, 1, border_radius=7)
                draw_icon_with_value(s, icon_id, val, UI_THEME["text"], self.app.tiny_font, rr.x + 4, rr.y + 2, size=1)
                sx += ww + 6

            pattern_len = max(1, len(getattr(e, "pattern", []) or []))
            deck_est = max(0, pattern_len - ((getattr(e, "intent_index", 0) + 1) % pattern_len))
            discard_est = min(pattern_len, getattr(e, "intent_index", 0))
            cx = counters.x
            cy = counters.y
            cx = draw_icon_with_value(s, 'deck', deck_est, UI_THEME['muted'], self.app.tiny_font, cx, cy, size=1)
            cx = draw_icon_with_value(s, 'hand', 1, UI_THEME['muted'], self.app.tiny_font, cx, cy, size=1)
            _ = draw_icon_with_value(s, 'discard', discard_est, UI_THEME['muted'], self.app.tiny_font, cx, cy, size=1)
            variant = self._enemy_presence_variant(e)
            boss_factor = 1.52 if (self.is_boss or str(getattr(e, "tier", "")).lower() == "boss") else 1.0

            # Aura and geometry stay contained in enemy panel and behind avatar.
            self._draw_enemy_aura(s, avatar_rect, intent_col, boss_factor, variant, t + i * 0.27, clip_rect=content)

            avatar_frame = avatar_rect.inflate(10, 10)
            pygame.draw.rect(s, (18, 16, 26), avatar_frame, border_radius=14)
            pygame.draw.rect(s, (*intent_col, int(98 * boss_factor)), avatar_frame, 2, border_radius=14)

            sprite = self.app.assets.sprite("enemies", e.id, (avatar_rect.w, avatar_rect.h), fallback=(100, 60, 90))
            sprite_box = sprite.get_rect(center=(avatar_rect.centerx, avatar_rect.centery + 2))
            shadow = pygame.Surface((avatar_rect.w + 20, avatar_rect.h + 20), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 118), shadow.get_rect())
            s.blit(shadow, (avatar_rect.x - 10, avatar_rect.y + 6))
            s.blit(sprite, sprite_box.topleft)
            overlay_kind = "archon" if boss_factor > 1.2 else ("celestial" if "angel" in variant else "guardian" if "nephilim" in variant else "void")
            sacred = self.app.assets.sprite("overlays", overlay_kind, (avatar_rect.w, avatar_rect.h), fallback=(0, 0, 0))
            sacred.set_alpha(84 if boss_factor > 1.2 else 52)
            s.blit(sacred, avatar_rect.topleft)

            self._draw_enemy_geometry_overlay(s, avatar_rect, intent_col, variant, boss_factor, t + i * 0.31)

            pygame.draw.rect(s, (28, 22, 36), hp_bar, border_radius=5)
            pygame.draw.rect(s, UI_THEME["hp"], pygame.Rect(hp_bar.x, hp_bar.y, int(hp_bar.w * ratio), hp_bar.h), border_radius=5)

            if boss_factor > 1.2:
                wobble_w = int(avatar_rect.w * (0.84 + 0.10 * math.sin((t + i) * 2.6)))
                wobble = pygame.Surface((wobble_w, 8), pygame.SRCALPHA)
                wobble.fill((*intent_col, 84))
                s.blit(wobble, (avatar_rect.centerx - wobble_w // 2, avatar_rect.bottom - 4))

        narrative_rect = self.layout.voices_rect
        UIPanel(narrative_rect).draw(s)
        e_line = self.dialog_enemy.current or "(el enemigo contiene la respiracion...)"
        h_line = self.dialog_hero.current or "(Chakana escucha la Trama...)"
        line_w = narrative_rect.w - 34
        enemy_lines = wrap_text(self.app.small_font, e_line, line_w, max_lines=1)
        hero_lines = wrap_text(self.app.small_font, h_line, line_w, max_lines=1)
        row_h = (narrative_rect.h - 20) // 2
        line_rows = [
            pygame.Rect(narrative_rect.x + 10, narrative_rect.y + 8, narrative_rect.w - 20, row_h),
            pygame.Rect(narrative_rect.x + 10, narrative_rect.y + 8 + row_h, narrative_rect.w - 20, row_h - 2),
        ]
        row_cols = [(58, 34, 52), (36, 52, 46)]
        row_lines = [enemy_lines, hero_lines]
        threat = 3 if any(k in str(self.last_trigger) for k in ["attack", "defeat", "low"]) else 0
        offx = threat if (pygame.time.get_ticks() // 40) % 2 == 0 else -threat
        for ridx, row in enumerate(line_rows):
            pygame.draw.rect(s, row_cols[ridx], row, border_radius=8)
            lines = row_lines[ridx]
            if ridx == 0:
                s.blit(self.app.tiny_font.render(self.enemy_voice_label, True, (245, 150, 166)), (row.x + 10, row.y + 4))
            elif ridx == 1:
                s.blit(self.app.tiny_font.render(self.chakana_voice_label, True, (166, 240, 190)), (row.x + 10, row.y + 4))
            yy = row.y + max(18, (row.h - 16 * max(1, len(lines))) // 2)
            for ln in lines:
                dx = offx if ridx == 0 else 0
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (row.x + 10 + dx, yy))
                yy += 16

        # LAYER 3-4: hud and cards (Layers.LAYER_HUD, Layers.LAYER_CARDS)
        hand = self.c.hand[:6]
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card_index = None
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                self.hover_card_index = i
        self.ctrl.on_hover(self.hover_card_index)
        for idx in range(len(hand)):
            tgt = 1.0 if idx == self.hover_card_index else 0.0
            cur = float(self.hover_anim.get(idx, 0.0))
            self.hover_anim[idx] = cur + (tgt - cur) * 0.22

        detail_rect = self.layout.card_detail
        UIPanel(detail_rect, variant="alt").draw(s)
        panel_x = detail_rect.x + 14
        panel_y = detail_rect.y + 14
        panel_w = detail_rect.w - 26
        entries = list(self.actions_log[-3:])
        if self._status_line and len(entries) < 3:
            entries.append(f"Estado: {self._status_line}")
        if not entries:
            entries = ["Sin acciones recientes."]
        for item in reversed(entries[:3]):
            for ln in self._wrap_panel_text(f"- {item}", panel_w, max_lines=1):
                if panel_y > detail_rect.bottom - 24:
                    break
                s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (panel_x, panel_y))
                panel_y += 16
            if panel_y > detail_rect.bottom - 24:
                break

        UIPanel(self.layout.hand_rect).draw(s)
        self._tutorial_targets["hand"] = pygame.Rect(self.layout.hand_rect)

        hand_inner = self.layout.hand_rect.inflate(-8, -8)
        pygame.draw.rect(s, UI_THEME["panel"], hand_inner, border_radius=10)

        old_clip = s.get_clip()
        s.set_clip(self.layout.hand_rect)
        for i, card in enumerate(hand):
            if i == self.hover_card_index:
                continue
            base, angle = self._card_pose(i, len(hand))
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, base, card, selected=(i == self.ctrl.selected_index), family=fam, hovered=(i == self.hover_card_index), angle=angle)
        s.set_clip(old_clip)

        hover_payload = None
        if self.hover_card_index is not None and self.hover_card_index < len(hand):
            i = self.hover_card_index
            card = hand[i]
            base_hover, _angle = self._card_pose(i, len(hand))
            # Hover: lift + scale + center for readability, keeping safe UI bounds.
            ww = int(base_hover.w * 1.35)
            hh = int(base_hover.h * 1.35)
            rr = pygame.Rect(0, 0, ww, hh)
            hover_t = min(1.0, max(0.0, self.hover_anim.get(i, 0.0)))
            eased = 1.0 - ((1.0 - hover_t) ** 3)
            rr.centerx = s.get_width() // 2
            rr.centery = int(s.get_height() * (0.50 - 0.04 * eased))
            safe_overlay = pygame.Rect(
                self.layout.hand_rect.x + 4,
                self.layout.topbar_rect.bottom + 8,
                self.layout.hand_rect.w - 8,
                self.layout.hand_rect.bottom - (self.layout.topbar_rect.bottom + 8),
            )
            rr.x = max(safe_overlay.x, min(safe_overlay.right - rr.w, rr.x))
            rr.y = max(safe_overlay.y, min(safe_overlay.bottom - rr.h, rr.y))
            end_guard = self.end_turn_rect.inflate(24, 24)
            if rr.colliderect(end_guard):
                rr.y = max(safe_overlay.y, end_guard.y - rr.h - 12)
            hover_payload = (i, card, rr)

        UIPanel(self.layout.playerhud_rect).draw(s)
        p = self.c.player
        pc = self._pile_counts()
        draw_n = pc["draw"]
        hand_n = pc["hand"]
        disc_n = pc["discard"]
        energy_now = int(p.get("energy", 0) or 0)
        player_block = max(0, int(p.get("block", 0) or 0))
        tpal = self.app.typography.palette

        # Final locked Chakana player HUD: 3 rows max + integrated larger portrait.
        ph = self.layout.playerhud_rect
        portrait_rect = pygame.Rect(ph.x + 12, ph.y + 10, 122, ph.h - 20)
        stats_rect = pygame.Rect(portrait_rect.right + 10, ph.y + 10, ph.w - portrait_rect.w - 34, ph.h - 20)

        pygame.draw.rect(s, (14, 12, 20), portrait_rect, border_radius=11)
        pygame.draw.rect(s, UI_THEME["gold"], portrait_rect, 2, border_radius=11)
        portrait_kind = "chakana_mage_hologram"
        avatar = self.app.assets.sprite("avatar", portrait_kind, (portrait_rect.w - 10, portrait_rect.h - 22), fallback=(86, 56, 132))
        av_rect = avatar.get_rect(center=(portrait_rect.centerx, portrait_rect.centery - 2))
        s.blit(avatar, av_rect.topleft)
        s.blit(self.app.tiny_font.render("CHAKANA", True, UI_THEME["gold"]), (portrait_rect.x + 26, portrait_rect.bottom - 18))

        row_gap = 6
        row1_h = 44
        row2_h = 40
        row3_h = stats_rect.h - row1_h - row2_h - row_gap * 2
        row1 = pygame.Rect(stats_rect.x, stats_rect.y, stats_rect.w, row1_h)
        row2 = pygame.Rect(stats_rect.x, row1.bottom + row_gap, stats_rect.w, row2_h)
        row3 = pygame.Rect(stats_rect.x, row2.bottom + row_gap, stats_rect.w, row3_h)

        def _value_chip(rect, title, value, col):
            pygame.draw.rect(s, UI_THEME["panel_2"], rect, border_radius=8)
            pygame.draw.rect(s, col, rect, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(title, True, tpal.muted), (rect.x + 8, rect.y + 4))
            s.blit(self.app.small_font.render(str(value), True, col), (rect.x + 8, rect.y + 18))

        # ROW 1: Vitalidad / Bloqueo / Turno (primary at-a-glance read)
        r1_gap = 8
        r1_w = (row1.w - r1_gap * 2) // 3
        vit = pygame.Rect(row1.x, row1.y, r1_w, row1.h)
        blk = pygame.Rect(vit.right + r1_gap, row1.y, r1_w, row1.h)
        trn = pygame.Rect(blk.right + r1_gap, row1.y, row1.w - (r1_w * 2 + r1_gap * 2), row1.h)
        _value_chip(vit, "Vitalidad", f"{p['hp']}/{p['max_hp']}", UI_THEME["hp"])
        _value_chip(blk, "Bloqueo", f"{player_block}", tpal.hud_block if player_block > 0 else tpal.muted)
        _value_chip(trn, "Turno", f"{self.c.turn}", tpal.hud_gold)
        self._tutorial_targets["player_block"] = pygame.Rect(blk)

        # ROW 2: Energy orbs (primary visual) + numeric support
        pygame.draw.rect(s, UI_THEME["panel_2"], row2, border_radius=8)
        pygame.draw.rect(s, UI_THEME["energy"], row2, 1, border_radius=8)
        s.blit(self.app.tiny_font.render("Energia", True, tpal.muted), (row2.x + 8, row2.y + 3))

        base_energy = int(getattr(self.c, "energy_per_turn", 3) or 3)
        energized_bonus = 1 if int((p.get("statuses", {}) or {}).get("energized", 0) or 0) > 0 else 0
        energy_cap = max(3, base_energy + energized_bonus, energy_now)
        orb_cap = max(3, min(8, energy_cap))
        energy_buffed = energy_now > (base_energy + energized_bonus) or energized_bonus > 0
        self.mana_orbs.update(energy_now)
        start_x = row2.x + 16
        orb_y = row2.y + 26
        self.mana_orbs.draw(s, start_x, orb_y, energy_now, max_mana=orb_cap, buffed=energy_buffed)
        energy_num = self.app.small_font.render(f"{energy_now}/{orb_cap}", True, UI_THEME["energy"])
        s.blit(energy_num, (row2.right - energy_num.get_width() - 10, row2.y + 14))

        # ROW 3: Harmony/Umbral + secondary piles (Mazo/Mano/Ecos)
        pygame.draw.rect(s, UI_THEME["panel_2"], row3, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], row3, 1, border_radius=8)
        h_cur = int(p.get("harmony_current", 0) or 0)
        h_max = max(1, int(p.get("harmony_max", 10) or 10))
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        ready = h_cur >= h_thr
        self._tutorial_targets["harmony"] = pygame.Rect(row3)

        h_col = UI_THEME["gold"] if ready else UI_THEME["text"]
        draw_icon_with_value(s, 'harmony', h_cur, h_col, self.app.tiny_font, row3.x + 8, row3.y + 4, size=1)
        s.blit(self.app.tiny_font.render(f'/{h_max}  Umbral {h_thr}', True, h_col), (row3.x + 60, row3.y + 7))
        bar = pygame.Rect(row3.x + 8, row3.y + 20, row3.w - 16, 8)
        pygame.draw.rect(s, (28, 24, 40), bar, border_radius=5)
        pygame.draw.rect(s, UI_THEME["good"] if ready else UI_THEME["accent_violet"], pygame.Rect(bar.x, bar.y, int(bar.w * (h_cur / max(1, h_max))), bar.h), border_radius=5)

        px = row3.x + 8
        py = row3.bottom - 18
        px = draw_icon_with_value(s, 'deck', draw_n, tpal.muted, self.app.tiny_font, px, py, size=1)
        px = draw_icon_with_value(s, 'hand', hand_n, tpal.muted, self.app.tiny_font, px, py, size=1)
        _ = draw_icon_with_value(s, 'discard', disc_n, tpal.muted, self.app.tiny_font, px, py, size=1)

        # Compact active relic visibility with hover tooltip.
        self._relic_chip_rects = []
        owned_relics = list((self.app.run_state or {}).get("relics", []) or [])
        if owned_relics:
            relic_by_id = {str(r.get("id")): r for r in list(getattr(self.app, "relics_data", []) or []) if isinstance(r, dict) and r.get("id")}
            rx = row3.right - 26
            for rid in reversed(owned_relics[-4:]):
                slot = pygame.Rect(rx, row3.bottom - 24, 20, 20)
                pygame.draw.rect(s, (26, 20, 36), slot, border_radius=6)
                pygame.draw.rect(s, UI_THEME["gold"], slot, 1, border_radius=6)
                icon = self.app.assets.sprite("relics", str(rid), (16, 16), fallback=(96, 76, 124))
                s.blit(icon, (slot.x + 2, slot.y + 2))
                relic = relic_by_id.get(str(rid), {})
                rname = self.app.loc.t(relic.get("name_key")) if relic.get("name_key") else str(rid).replace("_", " ").title()
                rdesc = self.app.loc.t(relic.get("text_key")) if relic.get("text_key") else "Reliquia activa."
                tip = self._wrap_panel_text(f"{rname}: {rdesc}", 340, max_lines=1)[0]
                self._relic_chip_rects.append((slot, tip))
                rx -= 24
        # Harmony core (bottom-center): dedicated visual mechanic with orb/glow readiness.
        UIPanel(self.layout.harmony_rect, variant="alt").draw(s)
        hr = self.layout.harmony_rect
        h_cur = int(p.get("harmony_current", 0) or 0)
        h_max = max(1, int(p.get("harmony_max", 10) or 10))
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        ready = h_cur >= h_thr
        self._tutorial_targets["harmony"] = pygame.Rect(hr)

        title_col = UI_THEME["gold"] if ready else UI_THEME["text"]
        s.blit(self.app.small_font.render("NUCLEO DE ARMONIA", True, title_col), (hr.x + 14, hr.y + 10))

        orb_slots = min(8, max(5, h_thr))
        ox = hr.centerx - ((orb_slots - 1) * 22) // 2
        oy = hr.y + 48
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
        near_ready = (not ready) and h_cur >= max(0, h_thr - 1)
        pulse_core = pulse if (ready or near_ready) else 0.0
        for i in range(orb_slots):
            filled = i < min(h_cur, orb_slots)
            col = UI_THEME["gold"] if (ready and filled) else (UI_THEME["violet"] if filled else (70, 62, 90))
            rr = 8 if (ready and filled) else 7
            if (ready or near_ready) and filled:
                glow = pygame.Surface((24, 24), pygame.SRCALPHA)
                glow_alpha = int(66 + 82 * pulse_core)
                glow_col = UI_THEME["gold"] if ready else UI_THEME["accent_violet"]
                pygame.draw.circle(glow, (*glow_col, glow_alpha), (12, 12), 11)
                s.blit(glow, (ox + i * 22 - 12, oy - 12))
            pygame.draw.circle(s, col, (ox + i * 22, oy), rr)
            pygame.draw.circle(s, (20, 16, 28), (ox + i * 22, oy), rr, 1)

        meter = pygame.Rect(hr.x + 16, hr.bottom - 34, hr.w - 32, 10)
        pygame.draw.rect(s, (30, 24, 40), meter, border_radius=5)
        meter_col = UI_THEME["good"] if ready else UI_THEME["accent_violet"]
        pygame.draw.rect(s, meter_col, pygame.Rect(meter.x, meter.y, int(meter.w * (h_cur / max(1, h_max))), meter.h), border_radius=5)
        if near_ready:
            pygame.draw.rect(s, UI_THEME["gold"], meter, 1, border_radius=5)
        s.blit(self.app.tiny_font.render(f"Armonia {h_cur}/{h_max}  Umbral {h_thr}", True, UI_THEME["text"]), (meter.x, meter.y - 15))

        if ready:
            self.harmony_seal_rect = pygame.Rect(hr.centerx - 64, hr.bottom - 22, 128, 18)
            pygame.draw.rect(s, UI_THEME["violet"], self.harmony_seal_rect, border_radius=7)
            pygame.draw.rect(s, UI_THEME["gold"], self.harmony_seal_rect, 1, border_radius=7)
            s.blit(self.app.tiny_font.render("SELLO LISTO", True, UI_THEME["text"]), (self.harmony_seal_rect.x + 26, self.harmony_seal_rect.y + 2))
        else:
            self.harmony_seal_rect = pygame.Rect(hr.centerx - 50, hr.bottom - 22, 100, 18)
            pygame.draw.rect(s, UI_THEME["panel_2"], self.harmony_seal_rect, border_radius=7)
            s.blit(self.app.tiny_font.render("SELLO", True, UI_THEME["muted"]), (self.harmony_seal_rect.x + 31, self.harmony_seal_rect.y + 2))

        UIPanel(self.layout.actions_rect).draw(s)
        state, label, disabled, _reason = self._resolve_action_state()
        state_ui = {
            "EXECUTE": ("EJECUTAR CARTA", UColors.ROLE["execute"], (255, 88, 146), UI_THEME["text"]),
            "RELEASE_SEAL": ("SELLO LISTO", UColors.ROLE["seal"], (246, 206, 112), UI_THEME["text"]),
            "END_TURN": ("FIN DEL TURNO", UColors.ROLE["end_turn"], (244, 220, 154), UI_THEME["text_dark"]),
            "INVALID": ("ACCION INVALIDA", UColors.ROLE["invalid"], (144, 126, 162), UI_THEME["text"]),
        }
        state_label, base_col, glow_col, text_col = state_ui.get(state, state_ui["END_TURN"])

        if self.ctrl.pressed_on_button_id == "action" and not disabled:
            base_col = tuple(max(0, min(255, int(ch * 0.88))) for ch in base_col)

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
        near_ready = (not ready) and h_cur >= max(0, h_thr - 1)
        glow_pad = 22
        glow = pygame.Surface((self.end_turn_rect.w + glow_pad * 2, self.end_turn_rect.h + glow_pad * 2), pygame.SRCALPHA)
        gold_alpha = 88 + int(84 * pulse)
        pygame.draw.rect(glow, (*UI_THEME["gold"], gold_alpha), glow.get_rect(), border_radius=24)
        tint_alpha = 54 + int(62 * pulse)
        if state == "INVALID":
            tint_alpha = 38
        pygame.draw.rect(glow, (*glow_col, tint_alpha), glow.get_rect(), border_radius=24)
        s.blit(glow, (self.end_turn_rect.x - glow_pad, self.end_turn_rect.y - glow_pad))

        pygame.draw.rect(s, base_col, self.end_turn_rect, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], self.end_turn_rect, 2, border_radius=18)

        txt = self.app.big_font.render(state_label, True, text_col)
        s.blit(txt, (self.end_turn_rect.centerx - txt.get_width() // 2, self.end_turn_rect.centery - txt.get_height() // 2 + 2))
        self._tutorial_targets["action_button"] = pygame.Rect(self.end_turn_rect)
        if state == "RELEASE_SEAL":
            rune = self.app.tiny_font.render("*", True, UI_THEME["gold"])
            s.blit(rune, (self.end_turn_rect.x + 10, self.end_turn_rect.y + 24))
            s.blit(rune, (self.end_turn_rect.right - 16, self.end_turn_rect.y + 24))

        if pygame.time.get_ticks() < self._invalid_feedback_until_ms:
            msg = self._invalid_feedback_msg or "Accion invalida"
            feedback_rect = pygame.Rect(self.layout.actions_rect.centerx - 260, self.layout.actions_rect.bottom - 24, 520, 18)
            pygame.draw.rect(s, (48, 30, 44), feedback_rect, border_radius=6)
            pygame.draw.rect(s, (190, 116, 146), feedback_rect, 1, border_radius=6)
            line = msg
            while self.app.tiny_font.size(line)[0] > feedback_rect.w - 10 and len(line) > 4:
                line = line[:-4] + "..."
            s.blit(self.app.tiny_font.render(line, True, (242, 188, 202)), (feedback_rect.x + 6, feedback_rect.y + 2))
        # LAYER 5-6: overlays/tooltips (Layers.LAYER_MODALS, Layers.LAYER_TOOLTIPS)
        if hover_payload is not None:
            i, card, rr = hover_payload
            shadow_rect = rr.inflate(18, 18)
            shadow = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 132), shadow.get_rect(), border_radius=22)
            s.blit(shadow, shadow_rect.topleft)
            hover_glow = pygame.Surface((rr.w + 12, rr.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(hover_glow, (232, 198, 255, 88), hover_glow.get_rect(), border_radius=16)
            s.blit(hover_glow, (rr.x - 6, rr.y - 6))

            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, rr, card, selected=(i == self.ctrl.selected_index), family=fam, hovered=True)
            pygame.draw.rect(s, (236, 220, 255), rr.inflate(8, 8), 2, border_radius=15)

            summary = summarize_card_effect(card.definition, card_instance=card, ctx=self.c)
            tip = str(summary.get("header") or "Efecto")
            tip_w = min(360, max(220, rr.w - 24))
            tip_rect = pygame.Rect(rr.centerx - tip_w // 2, rr.y - 34, tip_w, 28)
            if tip_rect.y < self.layout.topbar_rect.bottom + 8:
                tip_rect.y = rr.bottom + 6
            tip = tip or "Efecto"
            UITooltip(tip_rect, tip).draw(s, self.app.tiny_font)

        relic_tip = ""
        for rr, txt_tip in self._relic_chip_rects:
            if rr.collidepoint(self.app.renderer.map_mouse(pygame.mouse.get_pos())):
                relic_tip = txt_tip
                break
        if relic_tip:
            tip_rect = pygame.Rect(self.layout.playerhud_rect.right - 360, self.layout.playerhud_rect.y - 30, 348, 24)
            UITooltip(tip_rect, relic_tip).draw(s, self.app.tiny_font)

        self._render_tutorial_overlay(s)

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

            options = [("continue", "Continuar", panel.y + 84), ("map", "Salir al mapa", panel.y + 170), ("menu", "Salir al menu principal", panel.y + 256)]
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







