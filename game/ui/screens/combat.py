from __future__ import annotations

import math
from pathlib import Path

import pygame

from game.art.gen_avatar_chakana import render_avatar
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.combat.play_validation import can_play_card
from game.ui.anim import TypewriterBanner
from game.ui.components.card_detail_panel import CardDetailPanel
from game.ui.components.card_effect_summary import summarize_card_effect
from game.ui.components.mana_orbs import ManaOrbsWidget
from game.ui.components.modal_card_picker import ModalCardPicker
from game.ui.controllers.card_interaction import CardInteractionController
from game.ui.controllers.combat_dialogue_controller import CombatDialogueController
from game.ui.layout.combat_layout import build_combat_layout
from game.ui.theme import UI_THEME
from game.ui.components.topbar import CombatTopBar


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
        self.detail_panel = CardDetailPanel(app)
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
        self.dialogue_ctrl = CombatDialogueController(self.app.lore_engine, self._set_dialogue_lines)
        self.last_enemy_line = ""
        self.last_player_line = ""
        self.dialogue_cooldown_ms = 800
        self.dialogue_last_ms = 0
        self.dialogue_fallback_idx = {}
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
        btn_w = max(220, int(self.layout.actions_rect.w * 0.18))
        btn_h = max(52, int(self.layout.actions_rect.h * 0.48))
        self.end_turn_rect = pygame.Rect(self.layout.actions_rect.right - btn_w - 24, self.layout.actions_rect.y + (self.layout.actions_rect.h - btn_h) // 2, btn_w, btn_h)
        self.harmony_seal_rect = pygame.Rect(self.layout.playerhud_rect.right - 112, self.layout.playerhud_rect.y + 170, 96, 28)

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
        ctx = ctx or {}
        now = pygame.time.get_ticks()
        forced = trigger in {"combat_start", "victory", "defeat"}
        if not forced and now - self.dialogue_last_ms < self.dialogue_cooldown_ms:
            return
        intent_hint = str(ctx.get("intent", "")).lower()
        mapped_trigger = trigger
        if trigger == "turn_start" and intent_hint:
            if "ata" in intent_hint:
                mapped_trigger = "enemy_attack"
            elif "def" in intent_hint or "blo" in intent_hint:
                mapped_trigger = "enemy_defend"
        enemy_line, hero_line, src = self._dialogue_lookup(enemy_id, mapped_trigger)
        fallbacks = {
            "combat_start": ("La Trama se abre ante ti.", "Escucho el pulso de la Chakana."),
            "turn_start": ("El aire cambia antes del golpe.", "Leeré tu intención antes de actuar."),
            "card_played_attack": ("Una chispa no basta para vencer.", "Cada corte abre un destino."),
            "card_played_defense": ("Tu muro tiembla igual.", "Bloqueo ahora, contraataco después."),
            "card_played_utility": ("Manipulas el hilo, no su final.", "Ordeno la Trama a mi favor."),
            "enemy_attack": ("Siente el peso de mi embate.", "Tu fuerza no quebrará mi centro."),
            "enemy_defend": ("Me cubro hasta encontrar tu error.", "Entonces abriré tu guardia."),
            "harmony_ready": ("Tu pulso cambia...", "Armonía lista: la Chakana responde."),
            "low_hp_player": ("Te apagas.", "Sigo de pie. Aún no termina."),
            "victory": ("No era tu final...", "La Trama se inclina a mi paso."),
            "defeat": ("Tu hilo se corta aquí.", "Aprenderé de esta caída."),
        }
        if not enemy_line.strip() or not hero_line.strip():
            arr = [fallbacks.get(mapped_trigger, ("(el enemigo contiene la respiración...)", "(Chakana escucha la Trama...)")),
                   ("(el enemigo contiene la respiración...)", "(Chakana escucha la Trama...)")]
            idx = self.dialogue_fallback_idx.get(mapped_trigger, 0) % len(arr)
            enemy_line, hero_line = arr[idx]
            self.dialogue_fallback_idx[mapped_trigger] = idx + 1
        if enemy_line == self.last_enemy_line and hero_line == self.last_player_line:
            enemy_line = "(el enemigo contiene la respiración...)"
            hero_line = "(Chakana escucha la Trama...)"
        self._set_dialogue_lines(enemy_line, hero_line, mapped_trigger)
        self.last_enemy_line, self.last_player_line = enemy_line, hero_line
        self.dialogue_last_ms = now
        print(f"[dlg] trigger={mapped_trigger} enemy={enemy_id} line_id={src} ctx={ctx}")

    def _card_playable(self, card) -> bool:
        ok, _reason = can_play_card(card, self.c.player, self.c)
        return bool(ok)

    def _selected_card_play_state(self):
        idx = self.ctrl.selected_index
        if idx is None or idx >= len(self.c.hand):
            return False, "Sin selección"
        return can_play_card(self.c.hand[idx], self.c.player, self.c)

    def _playable_cards(self):
        return [c for c in self.c.hand if self._card_playable(c)]

    def _resolve_action_state(self):
        if self.resolving_t > 0:
            state, reason, label, disabled = "PLAY_CARD", "resolving", "...", True
        else:
            idx = self.ctrl.selected_index
            if idx is not None and idx < len(self.c.hand):
                card = self.c.hand[idx]
                ok, reason = can_play_card(card, self.c.player, self.c)
                if ok:
                    state, reason, label, disabled = "PLAY_CARD", "selected_playable", "Ejecutar", False
                else:
                    state, reason, label, disabled = "END_TURN", reason or "selected_not_playable", "Fin de Turno", False
            else:
                state, reason, label, disabled = "END_TURN", "default", "Fin de Turno", False
        if DEBUG_UI and (state != self._action_state or reason != self._action_state_reason):
            print(f"[ui] action_state={state} reason={reason}")
        self._action_state = state
        self._action_state_reason = reason
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
        ok, reason = can_play_card(card, self.c.player, self.c)
        if not ok:
            self._push_log(f"No se puede jugar: {reason}")
            try:
                self.app.sfx.play("deny")
            except Exception:
                pass
            return
        self.resolving_t = 0.15
        target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
        self.c.play_card(idx, target_idx)
        tags = set(getattr(card.definition, "tags", []) or [])
        trig = "card_played_attack" if "attack" in tags else "card_played_defense" if ("skill" in tags or "defense" in tags) else "card_played_utility"
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        self.set_dialogue(trig, enemy_id, {"card_id": card.definition.id})
        self._push_log(f"Jugada: {getattr(card.definition, 'name_key', 'Carta')}")
        self.ctrl.clear_selection("card_played")

    def _activate_action_button(self):
        state, _label, disabled, _reason = self._resolve_action_state()
        if disabled:
            return
        if state == "PLAY_CARD":
            self._execute_selected()
            return
        if state == "END_TURN":
            self._trigger_dialog("enemy_turn_start")
            self.c.end_turn()
            self._push_log("Jugada: Fin de turno")
            self.ctrl.clear_selection("end_turn")
            self.ctrl.clear_hover()

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
            icons.append("⚔")
        if "skill" in tags or any(str(e.get("type", "")) in {"block", "gain_block"} for e in effects if isinstance(e, dict)):
            icons.append("🛡")
        if "ritual" in tags:
            icons.append("✦")
        if any(str(e.get("type", "")) == "scry" for e in effects if isinstance(e, dict)):
            icons.append("👁")
        if any(str(e.get("type", "")) == "draw" for e in effects if isinstance(e, dict)):
            icons.append("⟳")
        if any(str(e.get("type", "")) in {"rupture", "apply_break"} for e in effects if isinstance(e, dict)):
            icons.append("☠")
        if any(str(e.get("type", "")) in {"energy", "gain_mana"} for e in effects if isinstance(e, dict)):
            icons.append("⚡")
        return icons

    def _draw_card(self, s, rect, card, selected=False, family="violet_arcane"):
        accent = {"crimson_chaos": (220, 108, 84), "emerald_spirit": (88, 198, 154), "azure_cosmic": (112, 152, 228), "violet_arcane": (176, 126, 240), "solar_gold": (226, 190, 112)}.get(family, (176, 126, 240))
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, accent, rect, 3, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 14, int(rect.h * 0.56)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 7, rect.y + 30))
        s.blit(self.app.tiny_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 8, rect.y + 6))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 16, rect.y + 16), 12)
        s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 20, rect.y + 9))
        icon_row = " ".join(self._card_icons(card)[:4])
        if icon_row:
            s.blit(self.app.tiny_font.render(icon_row, True, UI_THEME["gold"]), (rect.x + 8, rect.bottom - 24))
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
                self.set_dialogue("turn_start", enemy.id, {"intent": enemy.current_intent().get("label", "")})

        for ev in self.c.pop_events():
            if ev.get("type") == "damage" and ev.get("target") == "player" and ev.get("amount", 0) >= 8:
                self._trigger_dialog("enemy_big_attack")
                self._push_log(f"Daño recibido: {ev.get('amount',0)}")
            if ev.get("type") == "card_played":
                enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
                card_id = str(ev.get("card_id", ""))
                card_def = next((c for c in self.app.cards_data if c.get("id") == card_id), {}) if card_id else {}
                tags = set(card_def.get("tags", []) if isinstance(card_def, dict) else [])
                trig = "card_played_attack" if "attack" in tags else "card_played_defense" if ("skill" in tags or "defense" in tags) else "card_played_utility"
                self.set_dialogue(trig, enemy_id, {"card_id": card_id})
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
            self._trigger_dialog("enemy_low_hp")

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
        self.app.bg_gen.render_parallax(s, self.selected_biome, self.bg_seed, pygame.time.get_ticks() * 0.02, clip_rect=pygame.Rect(0, 0, s.get_width(), self.layout.voices_rect.bottom + 12), particles_on=self.app.user_settings.get("fx_particles", True))

        left, center, subtitle, timer_text, turn_text = self._topbar_narrative()
        self.topbar.render(s, self.app, self.layout, left, center, subtitle, timer_text, turn_text)

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.enemy_strip_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.enemy_strip_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Enemigos", True, UI_THEME["gold"]), (self.layout.enemy_strip_rect.x + 12, self.layout.enemy_strip_rect.y + 8))

        enemy_count = max(1, len(self.c.enemies))
        inner_strip = self.layout.enemy_strip_rect.inflate(-28, -46)
        card_w = (inner_strip.w - (enemy_count - 1) * 16) // enemy_count
        t = pygame.time.get_ticks() / 1000.0
        biome_col = {"kaypacha": (68, 150, 118), "hanan": (106, 126, 238), "ukhu": (126, 82, 150)}.get(self.selected_biome.lower(), (108, 86, 182))

        if self.is_boss and self.c.enemies:
            boss = self.c.enemies[0]
            br = pygame.Rect(inner_strip.x + 10, inner_strip.y + 4, inner_strip.w - 20, 14)
            ratio_b = max(0, boss.hp) / max(1, boss.max_hp)
            pygame.draw.rect(s, (32, 20, 24), br, border_radius=6)
            pygame.draw.rect(s, (220, 88, 110), pygame.Rect(br.x, br.y, int(br.w * ratio_b), br.h), border_radius=6)
            s.blit(self.app.tiny_font.render(f"JEFE {boss.name_key} {boss.hp}/{boss.max_hp}", True, UI_THEME["text"]), (br.x + 8, br.y - 16))

        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(inner_strip.x + i * (card_w + 16), inner_strip.y, card_w, inner_strip.h)
            intent_col = self._intent_led_color(e)
            slot_pad = 8
            led_w = max(16, er.w // 18)
            left_led = pygame.Rect(er.x + slot_pad, er.y + slot_pad, led_w, er.h - slot_pad * 2)
            right_led = pygame.Rect(er.right - slot_pad - led_w, er.y + slot_pad, led_w, er.h - slot_pad * 2)

            # enemy rgb leds (behind panel)
            for led in (left_led, right_led):
                pygame.draw.rect(s, (18, 18, 22), led, border_radius=6)
                alpha = 42 + int(34 * (0.5 + 0.5 * math.sin(t * 2.4 + i)))
                glow = pygame.Surface((led.w, led.h), pygame.SRCALPHA)
                glow.fill((*biome_col, alpha))
                s.blit(glow, led.topleft)
                for sy in range(led.y + 2, led.bottom, 6):
                    pygame.draw.line(s, (*intent_col, 90), (led.x + 2, sy), (led.right - 2, sy), 1)

            # enemy panel frame in the center lane so leds remain visible
            content = er.inflate(-slot_pad * 2, -slot_pad * 2)
            content.left = left_led.right + 10
            content.width = max(100, right_led.left - 10 - content.left)
            pygame.draw.rect(s, UI_THEME["deep_purple"], content, border_radius=10)
            pygame.draw.rect(s, UI_THEME["accent_violet"], content, 2, border_radius=10)

            portrait_w = min(120, int(content.w * 0.44))
            portrait_h = min(146, int(content.h * 0.82))
            portrait_rect = pygame.Rect(0, 0, portrait_w, portrait_h)
            portrait_rect.midleft = (content.x + 2, content.y + content.h // 2)

            text_x = portrait_rect.right + 10
            text_w = max(70, content.right - text_x - 6)
            intent_txt = str(e.current_intent().get("label", "Preparando"))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            hp_bar = pygame.Rect(text_x, content.y + 72, text_w, 14)

            # hp bar before sprite
            pygame.draw.rect(s, (35, 24, 50), hp_bar, border_radius=6)
            pygame.draw.rect(s, UI_THEME["hp"], pygame.Rect(hp_bar.x, hp_bar.y, int(hp_bar.w * ratio), hp_bar.h), border_radius=6)

            # sprite
            sprite = self.app.assets.sprite("enemies", e.id, (portrait_rect.w, portrait_rect.h), fallback=(100, 60, 90))
            s.blit(sprite, portrait_rect.topleft)

            # text on top
            guard = int(getattr(e, "block", 0))
            rupt = int(getattr(e, "statuses", {}).get("rupture", 0))
            s.blit(self.app.small_font.render(str(e.name_key), True, UI_THEME["text"]), (text_x, content.y + 10))
            s.blit(self.app.small_font.render(f"Intención: {intent_txt}", True, UI_THEME["gold"]), (text_x, content.y + 36))
            s.blit(self.app.tiny_font.render(f"HP {e.hp}/{e.max_hp}", True, UI_THEME["text"]), (text_x, hp_bar.bottom + 6))
            s.blit(self.app.tiny_font.render(f"Guardia {guard}  Ruptura {rupt}", True, UI_THEME["muted"]), (text_x, hp_bar.bottom + 24))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.voices_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.voices_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Voces del combate", True, UI_THEME["gold"]), (self.layout.voices_rect.x + 12, self.layout.voices_rect.y + 8))
        e_line = self.dialog_enemy.current or "(el enemigo contiene la respiración...)"
        h_line = self.dialog_hero.current or "(Chakana escucha la Trama...)"
        line_w = self.layout.voices_rect.w - 44
        enemy_lines = wrap_text(self.app.font, e_line, line_w, max_lines=2)
        hero_lines = wrap_text(self.app.font, h_line, line_w, max_lines=2)
        enemy_box = pygame.Rect(self.layout.voices_rect.x + 12, self.layout.voices_rect.y + 34, self.layout.voices_rect.w - 24, 40)
        hero_box = pygame.Rect(self.layout.voices_rect.x + 12, self.layout.voices_rect.y + 78, self.layout.voices_rect.w - 24, 40)
        pygame.draw.rect(s, (58, 34, 52), enemy_box, border_radius=8)
        pygame.draw.rect(s, (36, 52, 46), hero_box, border_radius=8)
        s.blit(self.app.tiny_font.render("ENEMIGO", True, (245, 132, 142)), (enemy_box.x + 8, enemy_box.y + 4))
        s.blit(self.app.tiny_font.render("CHAKANA", True, (166, 240, 190)), (hero_box.x + 8, hero_box.y + 4))
        threat = 3 if any(k in str(self.last_trigger) for k in ["attack", "defeat", "low"]) else 0
        offx = threat if (pygame.time.get_ticks() // 40) % 2 == 0 else -threat
        y = enemy_box.y + 18
        for ln in enemy_lines:
            s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (enemy_box.x + 10 + offx, y))
            y += 16
        y = hero_box.y + 18
        for ln in hero_lines:
            s.blit(self.app.tiny_font.render(ln, True, UI_THEME["text"]), (hero_box.x + 10, y))
            y += 16

        hand = self.c.hand[:6]
        detail_rect = self.layout.card_detail
        current_idx = self.hover_card_index if self.hover_card_index is not None else self.ctrl.selected_index
        current_card = hand[current_idx] if current_idx is not None and current_idx < len(hand) else None
        last_played = self.actions_log[-1] if self.actions_log else None
        self.detail_panel.render(
            s,
            detail_rect,
            current_card,
            placeholder_text="Selecciona una carta para ver sus detalles.",
            last_played=last_played,
        )

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.hand_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.hand_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Mano", True, UI_THEME["gold"]), (self.layout.hand_rect.x + 12, self.layout.hand_rect.y + 8))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card_index = None
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                self.hover_card_index = i
        self.ctrl.on_hover(self.hover_card_index)

        old_clip = s.get_clip()
        s.set_clip(self.layout.hand_rect)
        for i, card in enumerate(hand):
            base = self._card_rect(i, len(hand))
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, base, card, selected=(i == self.ctrl.selected_index), family=fam)
        s.set_clip(old_clip)

        if self.hover_card_index is not None and self.hover_card_index < len(hand):
            i = self.hover_card_index
            card = hand[i]
            key = card.definition.id
            cur = self.hover_anim.get(key, 0.0)
            cur = cur + (1.0 - cur) * 0.32
            self.hover_anim[key] = cur
            rr = self._card_rect(i, len(hand)).move(0, int(-14 * cur)).inflate(int(10 * cur), int(10 * cur))
            rr.clamp_ip(self.layout.hand_rect.inflate(-12, -12))
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, rr, card, selected=(i == self.ctrl.selected_index), family=fam)
            pygame.draw.rect(s, (220, 198, 255), rr.inflate(8, 8), 2, border_radius=14)
            summary = summarize_card_effect(card.definition, card_instance=card, ctx=self.c)
            tip = str(summary.get("header") or "Efecto: Ritual")
            tip_rect = pygame.Rect(rr.x, max(120, rr.y - 36), min(360, self.layout.hand_rect.w - 20), 28)
            pygame.draw.rect(s, UI_THEME["deep_purple"], tip_rect, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], tip_rect, 1, border_radius=8)
            line = tip
            while self.app.tiny_font.size(line)[0] > tip_rect.w - 12 and len(line) > 4:
                line = line[:-4] + "..."
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (tip_rect.x + 6, tip_rect.y + 6))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.playerhud_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.playerhud_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Chakana • Estado", True, UI_THEME["gold"]), (self.layout.playerhud_rect.x + 12, self.layout.playerhud_rect.y + 8))
        p = self.c.player
        left_x = self.layout.playerhud_rect.x + 16
        top_y = self.layout.playerhud_rect.y + 38
        s.blit(self.app.tiny_font.render(f"HP", True, UI_THEME["muted"]), (left_x, top_y))
        s.blit(self.app.font.render(f"{p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (left_x + 34, top_y - 6))
        s.blit(self.app.tiny_font.render(f"Bloqueo {p['block']}", True, UI_THEME["block"]), (left_x, top_y + 28))
        s.blit(self.app.tiny_font.render(f"Ruptura {p['rupture']}", True, UI_THEME["rupture"]), (left_x, top_y + 48))

        draw_n = len(getattr(self.c, "draw_pile", []))
        hand_n = len(getattr(self.c, "hand", []))
        disc_n = len(getattr(self.c, "discard_pile", []))
        ex_n = len(getattr(self.c, "exhaust_pile", []))
        s.blit(self.app.tiny_font.render(f"Draw {draw_n} • Mano {hand_n} • Discarte {disc_n} • Exhaust {ex_n}", True, UI_THEME["muted"]), (left_x, top_y + 70))

        h_cur = int(p.get("harmony_current", 0) or 0)
        h_max = max(1, int(p.get("harmony_max", 10) or 10))
        h_thr = max(1, int(p.get("harmony_ready_threshold", 6) or 6))
        ready = h_cur >= h_thr
        hy = top_y + 96
        bar = pygame.Rect(left_x, hy + 18, self.layout.playerhud_rect.w - 156, 14)
        pygame.draw.rect(s, (28, 26, 40), bar, border_radius=6)
        pygame.draw.rect(s, UI_THEME["good"], pygame.Rect(bar.x, bar.y, int(bar.w * (h_cur / max(1, h_max))), bar.h), border_radius=6)
        s.blit(self.app.tiny_font.render(f"Armonía {h_cur}/{h_max}  umbral {h_thr}", True, UI_THEME["good"] if ready else UI_THEME["text"]), (left_x, hy))
        if ready:
            pulse = 120 + int(80 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)))
            glow = pygame.Surface((92, 20), pygame.SRCALPHA)
            glow.fill((160, 245, 180, pulse))
            s.blit(glow, (bar.right + 6, hy + 14))
            s.blit(self.app.tiny_font.render("LISTA", True, UI_THEME["good"]), (bar.right + 14, hy + 16))
            pygame.draw.rect(s, UI_THEME["violet"], self.harmony_seal_rect, border_radius=8)
            pygame.draw.rect(s, UI_THEME["gold"], self.harmony_seal_rect, 1, border_radius=8)
            s.blit(self.app.tiny_font.render("SELLO", True, UI_THEME["text"]), (self.harmony_seal_rect.x + 22, self.harmony_seal_rect.y + 6))
        else:
            pygame.draw.rect(s, UI_THEME["panel_2"], self.harmony_seal_rect, border_radius=8)
            s.blit(self.app.tiny_font.render("SELLO", True, UI_THEME["muted"]), (self.harmony_seal_rect.x + 22, self.harmony_seal_rect.y + 6))

        self.mana_orbs.update(int(p.get("energy", 0)))
        self.mana_orbs.draw(s, left_x, self.layout.playerhud_rect.y + self.layout.playerhud_rect.h - 52, int(p.get("energy", 0)), 6)
        avatar = render_avatar(pygame.time.get_ticks() / 1000.0, min(84, self.layout.playerhud_rect.h - 40))
        s.blit(avatar, (self.layout.playerhud_rect.right - avatar.get_width() - 14, self.layout.playerhud_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.actions_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.actions_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Acciones", True, UI_THEME["gold"]), (self.layout.actions_rect.x + 12, self.layout.actions_rect.y + 8))
        _state, label, disabled, _reason = self._resolve_action_state()
        bcol = (88, 84, 102) if disabled else (116, 86, 184) if self.ctrl.pressed_on_button_id == "action" else UI_THEME["violet"]
        pygame.draw.rect(s, bcol, self.end_turn_rect, border_radius=12)
        txt = self.app.font.render(label, True, UI_THEME["text"])
        s.blit(txt, (self.end_turn_rect.centerx - txt.get_width() // 2, self.end_turn_rect.centery - txt.get_height() // 2))
        content_rect = self.layout.actions_rect.inflate(-16, -10)
        clip_prev = s.get_clip()
        s.set_clip(content_rect)
        log_x = content_rect.x
        log_y = self.layout.actions_rect.y + 34
        max_w = max(40, content_rect.w - 6)
        max_bottom = content_rect.bottom

        tail = self.actions_log[-6:]
        last = tail[-1] if tail else "-"
        y = log_y
        for line in self._wrap_panel_text(f"Última jugada: {last}", max_w, max_lines=1):
            if y + 16 > max_bottom:
                break
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["muted"]), (log_x, y))
            y += 16

        enemy_int = self.c.enemies[0].current_intent().get("label", "-") if self.c.enemies else "-"
        for line in self._wrap_panel_text(f"Turno actual: {self.c.turn}  Intención enemiga: {enemy_int}", max_w, max_lines=2):
            if y + 16 > max_bottom:
                break
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (log_x, y))
            y += 16

        y += 4
        for line in reversed(tail):
            wrapped = self._wrap_panel_text(f"• {line}", max_w, max_lines=2)
            for wline in wrapped:
                if y + 16 > max_bottom:
                    break
                s.blit(self.app.tiny_font.render(wline, True, UI_THEME["text"]), (log_x, y))
                y += 16
            if y + 16 > max_bottom:
                break

        s.set_clip(clip_prev)

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
                f"draw/hand/discard: {len(self.c.draw_pile)}/{len(self.c.hand)}/{len(self.c.discard_pile)}",
                f"harmony: {p.get('harmony_current',0)}/{p.get('harmony_max',10)} thr={p.get('harmony_ready_threshold',6)}",
                f"last_trigger: {self.last_trigger}",
            ]
            ok, reason = self._selected_card_play_state()
            info_lines.append(f"can_play={ok} reason={reason}")
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
