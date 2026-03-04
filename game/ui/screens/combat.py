import math
import pygame

from game.settings import INTERNAL_WIDTH
from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME
from game.art.gen_art32 import chakana_points


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
        if lines[-1] and not lines[-1].endswith("..."):
            lines[-1] = (lines[-1][: max(1, len(lines[-1]) - 3)] + "...")
    return lines


class CombatScreen:
    TOPBAR = pygame.Rect(0, 0, 1920, 100)
    ENEMY_PANEL = pygame.Rect(40, 110, 1840, 340)
    DIALOGUE_PANEL = pygame.Rect(220, 460, 1480, 140)
    CARD_AREA = pygame.Rect(40, 620, 1160, 250)
    PLAYER_HUD = pygame.Rect(1220, 620, 660, 250)
    ACTION_BAR = pygame.Rect(40, 890, 1840, 170)
    PLAYFIELD = pygame.Rect(0, 0, 1920, 610)

    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.selected_card_index = None
        self.scry_selected = None
        self.log_lines = []
        self.banner = TypewriterBanner()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0.0
        self.enemy_line_fx = 0.0
        self.hero_line_fx = 0.0
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        self.ui_state = "IDLE"
        self.resolving_t = 0.0
        self.last_turn = self.c.turn
        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self.end_turn_rect = pygame.Rect(self.ACTION_BAR.right - 330, self.ACTION_BAR.y + 52, 300, 78)
        self.status_rect = pygame.Rect(self.ACTION_BAR.right - 670, self.ACTION_BAR.y + 52, 300, 78)
        self.scry_confirm_rect = pygame.Rect(1920 // 2 - 140, 680, 280, 66)
        self.action_pressed = False
        self.pause_open = False
        self.pause_sel = None
        self.exit_confirm = False
        self.hover_card_index = None
        self.detail_panel_on = self.app.user_settings.get("detail_panel", True)
        self._trigger_dialog("combat_start")

    def _card_playable(self, card) -> bool:
        if card is None:
            return False
        mana = int(self.c.player.get("energy", 0))
        if card.cost > mana:
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
        playable_cards = self._playable_cards()
        if self.resolving_t > 0:
            return "...", True
        if self.selected_card_index is not None and self.selected_card_index < len(self.c.hand):
            card = self.c.hand[self.selected_card_index]
            if self._card_playable(card):
                return "Ejecutar", False
            return "Sin Maná", True
        if len(playable_cards) == 0:
            return "Fin de Turno", False
        return "Fin de Turno", False

    def _update_ui_state(self):
        label, disabled = self._compute_action_button()
        if self.resolving_t > 0:
            self.ui_state = "RESOLVING"
        elif label == "Ejecutar":
            self.ui_state = "SELECTED_PLAYABLE"
        elif label == "Sin Maná":
            self.ui_state = "SELECTED_NOT_PLAYABLE"
        else:
            self.ui_state = "IDLE"

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
        enemy_line, hero_line = self.app.lore_service.emit(trigger, enemy_id, {"turn": self.c.turn})
        self.dialog_enemy.set(enemy_line, 2.1)
        self.dialog_hero.set(hero_line, 2.1)
        self.enemy_line_fx = 0.24
        self.hero_line_fx = 0.22
        self.dialog_cd = 2.8
        self.app.sfx.play("whisper")
        self.app.sfx.play("chime")

    def _execute_selected(self):
        self._update_ui_state()
        if self.ui_state != "SELECTED_PLAYABLE":
            return
        self.resolving_t = 0.15
        target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
        before_hand = len(self.c.hand)
        self.c.play_card(self.selected_card_index, target_idx)
        if len(self.c.hand) < before_hand:
            self.selected_card_index = None
        self._update_ui_state()

    def on_leave(self):
        self.selected_card_index = None

    def _activate_action_button(self):
        label, disabled = self._compute_action_button()
        if disabled:
            return
        if label == "Ejecutar":
            self._execute_selected()
        else:
            self.c.end_turn()
            self.selected_card_index = None
            self._update_ui_state()

    def _handle_pause(self, pos):
        if not self.pause_open:
            return False
        btns = {
            "continue": pygame.Rect(760, 410, 400, 64),
            "options": pygame.Rect(760, 492, 400, 64),
            "menu": pygame.Rect(760, 574, 400, 64),
            "quit": pygame.Rect(760, 656, 400, 64),
        }
        for k, r in btns.items():
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
                return True
        return True

    def _handle_scry_event(self, event):
        cards = self.c.scry_pending
        rects = [pygame.Rect(360 + i * 250, 320, 220, 320) for i in range(len(cards))]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(rects):
                if r.collidepoint(pos):
                    self.scry_selected = i
                    return True
            if self.scry_confirm_rect.collidepoint(pos) and self.scry_selected is not None:
                self.c.apply_scry_order(cards)
                self.scry_selected = None
                return True
        return True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pause_open = not self.pause_open
            if self.pause_open:
                self.selected_card_index = None
            self.exit_confirm = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            seq = ["combat_start", "enemy_big_attack", "enemy_low_hp", "player_low_hp", "boss_phase", "victory"]
            idx = (seq.index(getattr(self, "_dbg_trigger", "combat_start")) + 1) % len(seq) if hasattr(self, "_dbg_trigger") else 0
            self._dbg_trigger = seq[idx]
            self._trigger_dialog(self._dbg_trigger)
            return
        if self.pause_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.app.renderer.map_mouse(event.pos)
                self._handle_pause(pos)
            return
        if self.c.scry_pending and self._handle_scry_event(event):
            return
        if self.ui_state == "RESOLVING":
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self.action_pressed = True
                return
            for i, _ in enumerate(self.c.hand[:6]):
                if self._card_rect(i, min(6, len(self.c.hand))).collidepoint(pos):
                    self.selected_card_index = i
                    self._update_ui_state()
                    self.app.sfx.play("card_pick")
                    return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.action_pressed and self.end_turn_rect.collidepoint(pos):
                self._activate_action_button()
            self.action_pressed = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._execute_selected()

    def update(self, dt):
        self.c.update(dt)
        self.resolving_t = max(0, self.resolving_t - dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        self.enemy_line_fx = max(0, self.enemy_line_fx - dt)
        self.hero_line_fx = max(0, self.hero_line_fx - dt)
        if self.last_turn != self.c.turn:
            self.last_turn = self.c.turn
            self.selected_card_index = None
        for ev in self.c.pop_events():
            if ev.get("type") == "damage":
                self.log_lines.insert(0, f"{ev['target']}: -{ev['amount']} Vida")
                if ev.get("target") == "player" and ev.get("amount", 0) >= 8:
                    self._trigger_dialog("enemy_big_attack")
            if ev.get("type") == "block":
                self.log_lines.insert(0, f"{ev['target']}: +{ev['amount']} Guardia")
        if self.c.player["hp"] <= max(10, self.c.player["max_hp"] * 0.3):
            self._trigger_dialog("player_low_hp")
        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("enemy_low_hp")
        if self.is_boss and self.c.turn % 4 == 0:
            self._trigger_dialog("boss_phase")
        self.log_lines = self.log_lines[:8]
        self._update_ui_state()
        if self.c.result == "victory":
            self._trigger_dialog("victory")
            self.selected_card_index = None
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.selected_card_index = None
            self.app.goto_menu()

    def _card_rect(self, i, total, hovered=False):
        w, h, g = 180, 250, 14
        tw = total * w + max(0, total - 1) * g
        x = self.CARD_AREA.x + (self.CARD_AREA.w - tw) // 2 + i * (w + g)
        r = pygame.Rect(x, self.CARD_AREA.y + 8, w, h)
        return r.inflate(16, 8) if hovered else r

    def _draw_panel(self, s, rect, title):
        pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        s.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))

    def _draw_card(self, s, rect, card, selected=False):
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_border"], rect, 2, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 14, int(rect.h * 0.56)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 7, rect.y + 30))
        s.blit(self.app.tiny_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 8, rect.y + 6))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 16, rect.y + 16), 12)
        s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 20, rect.y + 9))
        if selected:
            pygame.draw.rect(s, UI_THEME["gold"], rect.inflate(8, 8), 3, border_radius=14)

    def _draw_pause(self, s):
        ov = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150)); s.blit(ov, (0, 0))
        panel = pygame.Rect(680, 340, 560, 420)
        pygame.draw.rect(s, UI_THEME["deep_purple"], panel, border_radius=16)
        pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=16)
        s.blit(self.app.big_font.render("PAUSA", True, UI_THEME["gold"]), (880, 364))
        btns = [("Continuar", 410), ("Opciones", 492), ("Salir al Menú", 574), ("Salir del Juego", 656)]
        for lbl, y in btns:
            r = pygame.Rect(760, y, 400, 64)
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=10)
            s.blit(self.app.font.render(lbl, True, UI_THEME["text"]), (r.x + 110, r.y + 18))
        if self.exit_confirm:
            s.blit(self.app.tiny_font.render("Click otra vez en 'Salir al Menú' para confirmar", True, UI_THEME["bad"]), (750, 736))

    def render(self, s):
        t = pygame.time.get_ticks() * 0.02
        self.app.bg_gen.render_parallax(s, self.selected_biome, self.bg_seed, t, clip_rect=self.PLAYFIELD, particles_on=self.app.user_settings.get("fx_particles", True))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card_index = None

        for rect, title in [(self.TOPBAR, "Trama"), (self.ENEMY_PANEL, "Enemigo"), (self.DIALOGUE_PANEL, "Voces"), (self.PLAYER_HUD, "Chakana"), (self.CARD_AREA, "Mano"), (self.ACTION_BAR, "Acciones")]:
            self._draw_panel(s, rect, title)

        ejit = int(math.sin(pygame.time.get_ticks() * 0.04)) if self.enemy_line_fx > 0 else 0
        esc = 1.03 if self.hero_line_fx > 0 else 1.0
        e_line = self.dialog_enemy.current
        h_line = self.dialog_hero.current
        s.blit(self.app.font.render(e_line, True, UI_THEME["bad"]), (self.DIALOGUE_PANEL.centerx - self.app.font.size(e_line)[0] // 2 + ejit, self.DIALOGUE_PANEL.y + 30))
        hf = self.app.font.render(h_line, True, UI_THEME["good"])
        hf = pygame.transform.rotozoom(hf, 0, esc)
        s.blit(hf, (self.DIALOGUE_PANEL.centerx - hf.get_width() // 2, self.DIALOGUE_PANEL.y + 80))

        p = self.c.player
        s.blit(self.app.font.render(f"Vida {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (self.PLAYER_HUD.x + 22, self.PLAYER_HUD.y + 38))
        s.blit(self.app.mono_font.render(f"Guardia {p['block']}", True, UI_THEME["block"]), (self.PLAYER_HUD.x + 22, self.PLAYER_HUD.y + 78))
        s.blit(self.app.mono_font.render(f"Quiebre {p['rupture']}", True, UI_THEME["rupture"]), (self.PLAYER_HUD.x + 260, self.PLAYER_HUD.y + 38))
        center = (self.PLAYER_HUD.x + 545, self.PLAYER_HUD.y + 88)
        pts = chakana_points(center, int(42 * (1.0 + 0.03 * math.sin(pygame.time.get_ticks() / 280.0))), 0.35)
        pygame.draw.polygon(s, (182, 154, 240), pts, 2)

        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(self.ENEMY_PANEL.x + 24 + i * 600, self.ENEMY_PANEL.y + 36, 560, 286)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=12)
            s.blit(self.app.assets.sprite("enemies", e.id, (180, 180), fallback=(100, 60, 90)), (er.x + 18, er.y + 28))
            intent = e.current_intent().get("label", "Preparando")
            s.blit(self.app.small_font.render(str(e.name_key), True, UI_THEME["text"]), (er.x + 260, er.y + 46))
            s.blit(self.app.small_font.render(intent, True, UI_THEME["gold"]), (er.x + 260, er.y + 86))

        hand = self.c.hand[:6]
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                self.hover_card_index = i
        for i, card in enumerate(hand):
            rr = self._card_rect(i, len(hand), hovered=(i == self.hover_card_index))
            if i == self.hover_card_index:
                rr = rr.inflate(12, 12)
            self._draw_card(s, rr, card, selected=(i == self.selected_card_index))

        # detail panel replaces floating tooltip
        if self.detail_panel_on:
            panel = pygame.Rect(1220, 350, 660, 250)
            self._draw_panel(s, panel, "Detalle")
            idx = self.hover_card_index if self.hover_card_index is not None else self.selected_card_index
            if idx is not None and idx < len(hand):
                card = hand[idx]
                art = self.app.assets.sprite("cards", card.definition.id, (220, 150), fallback=(70, 44, 105))
                s.blit(art, (panel.x + 14, panel.y + 42))
                s.blit(self.app.small_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (panel.x + 250, panel.y + 48))
                s.blit(self.app.mono_font.render(f"Coste: {card.cost}", True, UI_THEME["energy"]), (panel.x + 250, panel.y + 82))
                lines = wrap_text(self.app.tiny_font, str(card.definition.text_key), 380, max_lines=5)
                for i, ln in enumerate(lines):
                    s.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (panel.x + 250, panel.y + 114 + i * 22))
                tags = ", ".join(getattr(card.definition, "tags", [])[:4])
                s.blit(self.app.tiny_font.render(tags, True, UI_THEME["gold"]), (panel.x + 250, panel.y + 222))

        label, disabled = self._compute_action_button()
        col = (88, 84, 102) if disabled else (136, 102, 210) if not self.action_pressed else (116, 86, 184)
        pygame.draw.rect(s, col, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.end_turn_rect.x + 80, self.end_turn_rect.y + 24))

        if self.pause_open:
            self._draw_pause(s)
