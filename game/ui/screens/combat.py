from __future__ import annotations

import math
from pathlib import Path

import pygame

from game.art.gen_avatar_chakana import render_avatar
from game.art.gen_card_art32 import GEN_CARD_ART_VERSION
from game.core.paths import data_dir
from game.core.safe_io import load_json
from game.ui.anim import TypewriterBanner
from game.ui.components.mana_orbs import ManaOrbsWidget
from game.ui.controllers.card_interaction import CardInteractionController
from game.ui.layouts.combat_layout import CombatLayout
from game.ui.theme import UI_THEME


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
        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self.pause_open = False
        self.exit_confirm = False
        self.hover_card_index = None
        self.dialog_debug_overlay = False
        self.art_debug_overlay = False
        self.last_trigger = "combat_start"
        self.hover_anim = {}
        self._combat_triggers = ["combat_start", "player_turn_start", "enemy_turn_start", "enemy_big_attack", "player_low_hp", "enemy_low_hp", "victory"]
        self._art_manifest = load_json(data_dir() / "art_manifest.json", default={})
        self._card_prompts = load_json(data_dir() / "card_prompts.json", default={})
        self.turn_timer_enabled = bool(self.app.user_settings.get("turn_timer_enabled", False))
        self.turn_timer_limit = float(max(3, int(self.app.user_settings.get("turn_timer_seconds", 20))))
        self.turn_timer_left = self.turn_timer_limit
        self.layout = CombatLayout.from_size(1920, 1080)
        self.end_turn_rect = pygame.Rect(0, 0, 1, 1)
        self._trigger_dialog("combat_start")

    def on_leave(self):
        self.ctrl.clear_selection("screen_change")

    def _refresh_layout(self, surface: pygame.Surface):
        self.layout = CombatLayout.from_size(surface.get_width(), surface.get_height())
        btn_w = max(220, int(self.layout.actions_rect.w * 0.18))
        btn_h = max(52, int(self.layout.actions_rect.h * 0.48))
        self.end_turn_rect = pygame.Rect(self.layout.actions_rect.right - btn_w - 24, self.layout.actions_rect.y + (self.layout.actions_rect.h - btn_h) // 2, btn_w, btn_h)

    def _card_playable(self, card) -> bool:
        mana = int(self.c.player.get("energy", 0))
        if card is None or card.cost > mana:
            return False
        pred = getattr(card, "is_playable", None)
        if callable(pred):
            try:
                return bool(pred(self.c))
            except Exception:
                return card.cost <= mana
        return True

    def _playable_cards(self):
        return [c for c in self.c.hand if self._card_playable(c)]

    def _compute_action_button(self):
        if self.resolving_t > 0:
            return "...", True
        idx = self.ctrl.selected_index
        if idx is not None and idx < len(self.c.hand):
            card = self.c.hand[idx]
            if card in self._playable_cards():
                return "Ejecutar", False
            return "Sin Maná", True
        return "Fin de Turno", False

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        enemy_line, hero_line = self.app.lore_engine.get_combat_lines(enemy_id, trigger)
        self.dialog_enemy.set(enemy_line or "...", 1.2)
        self.dialog_hero.set(hero_line or "...", 1.2)
        self.enemy_line_fx = 0.24
        self.hero_line_fx = 0.22
        self.dialog_cd = 1.4
        self.last_trigger = trigger

    def _execute_selected(self):
        idx = self.ctrl.selected_index
        if idx is None or idx >= len(self.c.hand):
            return
        card = self.c.hand[idx]
        if not self._card_playable(card):
            return
        self.resolving_t = 0.15
        target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
        before = len(self.c.hand)
        self.c.play_card(idx, target_idx)
        if len(self.c.hand) < before:
            self.ctrl.clear_selection("card_played")

    def _activate_action_button(self):
        label, disabled = self._compute_action_button()
        if disabled:
            return
        if label == "Ejecutar":
            self._execute_selected()
        else:
            self._trigger_dialog("enemy_turn_start")
            self.c.end_turn()
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
            prompts = self._card_prompts.get(cid, "") if isinstance(self._card_prompts, dict) else ""
            prompt = str(prompts.get("prompt_text", "") if isinstance(prompts, dict) else prompts)[:80]
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

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pause_open = not self.pause_open
            if self.pause_open:
                self.ctrl.clear_selection("pause_open")
            self.exit_confirm = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            self.dialog_debug_overlay = not self.dialog_debug_overlay
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            idx = (self._combat_triggers.index(self.last_trigger) + 1) % len(self._combat_triggers) if self.last_trigger in self._combat_triggers else 0
            self._trigger_dialog(self._combat_triggers[idx])
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
            self.art_debug_overlay = not self.art_debug_overlay
            return

        if self.pause_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.app.renderer.map_mouse(event.pos)
                options = {"continue": pygame.Rect(760, 410, 400, 64), "options": pygame.Rect(760, 492, 400, 64), "menu": pygame.Rect(760, 574, 400, 64), "quit": pygame.Rect(760, 656, 400, 64)}
                for k, r in options.items():
                    if r.collidepoint(pos):
                        if k == "continue":
                            self.pause_open = False
                        elif k == "options":
                            self.pause_open = False
                            self.app.goto_settings()
                        elif k == "menu":
                            if self.exit_confirm:
                                self.pause_open = False
                                self.app.goto_menu()
                            else:
                                self.exit_confirm = True
                        elif k == "quit":
                            self.app.running = False
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

    def _draw_card(self, s, rect, card, selected=False, family="violet_arcane"):
        accent = {"crimson_chaos": (220, 108, 84), "emerald_spirit": (88, 198, 154), "azure_cosmic": (112, 152, 228), "violet_arcane": (176, 126, 240), "solar_gold": (226, 190, 112)}.get(family, (176, 126, 240))
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, accent, rect, 3, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 14, int(rect.h * 0.56)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 7, rect.y + 30))
        s.blit(self.app.tiny_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 8, rect.y + 6))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 16, rect.y + 16), 12)
        s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 20, rect.y + 9))
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
                self.ctrl.clear_selection("timer_end_turn")
                self.ctrl.clear_hover()
                self.turn_timer_left = self.turn_timer_limit

        if self.last_turn != self.c.turn:
            self.last_turn = self.c.turn
            self.turn_timer_left = self.turn_timer_limit
            self.ctrl.clear_selection("turn_changed")
            self._trigger_dialog("player_turn_start")

        for ev in self.c.pop_events():
            if ev.get("type") == "damage" and ev.get("target") == "player" and ev.get("amount", 0) >= 8:
                self._trigger_dialog("enemy_big_attack")

        if self.c.player["hp"] <= max(10, self.c.player["max_hp"] * 0.3):
            self._trigger_dialog("player_low_hp")
        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("enemy_low_hp")

        self.ctrl.validate_selection(len(self.c.hand))
        if self.c.result == "victory":
            self._trigger_dialog("victory")
            self.ctrl.clear_selection("victory")
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.ctrl.clear_selection("defeat")
            self.app.goto_menu()

    def render(self, s):
        self._refresh_layout(s)
        self.app.bg_gen.render_parallax(s, self.selected_biome, self.bg_seed, pygame.time.get_ticks() * 0.02, clip_rect=pygame.Rect(0, 0, s.get_width(), self.layout.voices_rect.bottom + 12), particles_on=self.app.user_settings.get("fx_particles", True))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.topbar_rect)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.topbar_rect, 2)
        s.blit(self.app.small_font.render(f"Turno {self.c.turn}", True, UI_THEME["gold"]), (self.layout.topbar_rect.x + 16, self.layout.topbar_rect.y + 16))
        if self.turn_timer_enabled:
            timer_label = f"Tiempo {self.turn_timer_left:04.1f}s"
            tw = self.app.small_font.size(timer_label)[0]
            s.blit(self.app.small_font.render(timer_label, True, UI_THEME["text"]), (self.layout.topbar_rect.right - tw - 20, self.layout.topbar_rect.y + 16))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.enemy_strip_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.enemy_strip_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Enemigos", True, UI_THEME["gold"]), (self.layout.enemy_strip_rect.x + 12, self.layout.enemy_strip_rect.y + 8))

        enemy_count = max(1, len(self.c.enemies))
        inner_strip = self.layout.enemy_strip_rect.inflate(-28, -46)
        card_w = (inner_strip.w - (enemy_count - 1) * 16) // enemy_count
        t = pygame.time.get_ticks() / 1000.0
        biome_col = {"kaypacha": (68, 150, 118), "hanan": (106, 126, 238), "ukhu": (126, 82, 150)}.get(self.selected_biome.lower(), (108, 86, 182))

        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(inner_strip.x + i * (card_w + 16), inner_strip.y, card_w, inner_strip.h)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=10)
            intent_col = self._intent_led_color(e)
            led_w = max(18, er.w // 16)
            for side_x in (er.x + 8, er.right - led_w - 8):
                led = pygame.Rect(side_x, er.y + 10, led_w, er.h - 20)
                pygame.draw.rect(s, (20, 20, 24), led, border_radius=6)
                alpha = 45 + int(35 * (0.5 + 0.5 * math.sin(t * 2.4 + i)))
                glow = pygame.Surface((led.w, led.h), pygame.SRCALPHA)
                glow.fill((*biome_col, alpha))
                s.blit(glow, led.topleft)
                for sy in range(led.y + 2, led.bottom, 6):
                    pygame.draw.line(s, (*intent_col, 90), (led.x + 2, sy), (led.right - 2, sy), 1)

            portrait_w = min(180, er.w // 3)
            portrait_h = min(180, er.h - 58)
            s.blit(self.app.assets.sprite("enemies", e.id, (portrait_w, portrait_h), fallback=(100, 60, 90)), (er.x + led_w + 18, er.y + 24))
            tx = er.x + led_w + 28 + portrait_w
            s.blit(self.app.small_font.render(str(e.name_key), True, UI_THEME["text"]), (tx, er.y + 24))
            intent_txt = e.current_intent().get("label", "Preparando")
            s.blit(self.app.small_font.render(f"Intento: {intent_txt}", True, UI_THEME["gold"]), (tx, er.y + 56))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            hp_bar = pygame.Rect(tx, er.y + 96, max(90, er.right - tx - 16), 16)
            pygame.draw.rect(s, (35, 24, 50), hp_bar, border_radius=6)
            pygame.draw.rect(s, UI_THEME["hp"], pygame.Rect(hp_bar.x, hp_bar.y, int(hp_bar.w * ratio), hp_bar.h), border_radius=6)
            s.blit(self.app.tiny_font.render(f"HP {e.hp}/{e.max_hp}", True, UI_THEME["text"]), (tx, er.y + 120))
            guard = getattr(e, "block", 0)
            rupt = getattr(e, "statuses", {}).get("rupture", 0)
            s.blit(self.app.tiny_font.render(f"Bloqueo {guard}  Ruptura {rupt}", True, UI_THEME["muted"]), (tx, er.y + 144))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.voices_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.voices_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Voces", True, UI_THEME["gold"]), (self.layout.voices_rect.x + 12, self.layout.voices_rect.y + 8))
        e_line = self.dialog_enemy.current or "(enemigo en silencio)"
        h_line = self.dialog_hero.current or "(chakana en silencio)"
        enemy_lines = wrap_text(self.app.font, e_line, self.layout.voices_rect.w - 32, max_lines=2)
        hero_lines = wrap_text(self.app.font, h_line, self.layout.voices_rect.w - 32, max_lines=2)
        y = self.layout.voices_rect.y + 34
        for ln in enemy_lines:
            s.blit(self.app.font.render(ln, True, (245, 132, 142)), (self.layout.voices_rect.x + 16, y))
            y += 24
        y += 4
        for ln in hero_lines:
            s.blit(self.app.font.render(ln, True, (166, 240, 190)), (self.layout.voices_rect.x + 16, y))
            y += 24

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.hand_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.hand_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Mano", True, UI_THEME["gold"]), (self.layout.hand_rect.x + 12, self.layout.hand_rect.y + 8))

        hand = self.c.hand[:6]
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

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.playerhud_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.playerhud_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Chakana", True, UI_THEME["gold"]), (self.layout.playerhud_rect.x + 12, self.layout.playerhud_rect.y + 8))
        p = self.c.player
        s.blit(self.app.font.render(f"Vida {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (self.layout.playerhud_rect.x + 18, self.layout.playerhud_rect.y + 38))
        s.blit(self.app.mono_font.render(f"Bloqueo {p['block']}", True, UI_THEME["block"]), (self.layout.playerhud_rect.x + 18, self.layout.playerhud_rect.y + 72))
        s.blit(self.app.mono_font.render(f"Ruptura {p['rupture']}", True, UI_THEME["rupture"]), (self.layout.playerhud_rect.x + 18, self.layout.playerhud_rect.y + 104))
        self.mana_orbs.update(int(p.get("energy", 0)))
        self.mana_orbs.draw(s, self.layout.playerhud_rect.x + 18, self.layout.playerhud_rect.y + self.layout.playerhud_rect.h - 52, int(p.get("energy", 0)), 6)
        avatar = render_avatar(pygame.time.get_ticks() / 1000.0, min(96, self.layout.playerhud_rect.h - 40))
        s.blit(avatar, (self.layout.playerhud_rect.right - avatar.get_width() - 16, self.layout.playerhud_rect.y + 20))

        pygame.draw.rect(s, UI_THEME["panel"], self.layout.actions_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.layout.actions_rect, 2, border_radius=12)
        s.blit(self.app.small_font.render("Acciones", True, UI_THEME["gold"]), (self.layout.actions_rect.x + 12, self.layout.actions_rect.y + 8))
        label, disabled = self._compute_action_button()
        bcol = (88, 84, 102) if disabled else (116, 86, 184) if self.ctrl.pressed_on_button_id == "action" else UI_THEME["violet"]
        pygame.draw.rect(s, bcol, self.end_turn_rect, border_radius=12)
        txt = self.app.font.render(label, True, UI_THEME["text"])
        s.blit(txt, (self.end_turn_rect.centerx - txt.get_width() // 2, self.end_turn_rect.centery - txt.get_height() // 2))

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
            for lbl, y in [("Continuar", panel.y + 70), ("Opciones", panel.y + 152), ("Salir al Menú", panel.y + 234), ("Salir del Juego", panel.y + 316)]:
                r = pygame.Rect(panel.x + 80, y, 400, 64)
                pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=10)
                s.blit(self.app.font.render(lbl, True, UI_THEME["text"]), (r.x + 110, r.y + 18))
