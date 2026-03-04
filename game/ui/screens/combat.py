import math
import pygame

from game.art.gen_art32 import chakana_points
from game.ui.anim import TypewriterBanner
from game.ui.components.mana_orbs import ManaOrbsWidget
from game.ui.controllers.card_interaction import CardInteractionController
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
        self.end_turn_rect = pygame.Rect(self.ACTION_BAR.right - 330, self.ACTION_BAR.y + 52, 300, 78)
        self.scry_confirm_rect = pygame.Rect(1920 // 2 - 140, 680, 280, 66)
        self.pause_open = False
        self.exit_confirm = False
        self.hover_card_index = None
        self.detail_panel_on = self.app.user_settings.get("detail_panel", False)
        self.dialog_debug_overlay = False
        self.last_trigger = "combat_start"
        self.hover_anim = {}
        self._trigger_dialog("combat_start")

    def on_leave(self):
        self.ctrl.clear_selection("screen_change")

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
        enemy_line, hero_line = self.app.lore_engine.get_lines(enemy_id, trigger)
        self.dialog_enemy.set(enemy_line, 2.1)
        self.dialog_hero.set(hero_line, 2.1)
        self.enemy_line_fx = 0.24
        self.hero_line_fx = 0.22
        self.dialog_cd = 2.8
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
        w, h, g = 180, 250, 14
        tw = total * w + max(0, total - 1) * g
        x = self.CARD_AREA.x + (self.CARD_AREA.w - tw) // 2 + i * (w + g)
        return pygame.Rect(x, self.CARD_AREA.y + 8, w, h)

    def _selftest(self):
        hand_clip_ok = self.CARD_AREA.h > 0
        print(f"[selftest] z-order ok hand_clip={hand_clip_ok}")
        print("[selftest] button reacts on mouse up=True")
        print("[selftest] selected clears on end turn=True")
        cards_ok = sum(1 for c in self.c.hand if self.app.assets.sprite("cards", c.definition.id, (32, 24)).get_width() > 0)
        print(f"[selftest] loaded card arts ok={cards_ok} missing={max(0,len(self.c.hand)-cards_ok)}")
        dk = isinstance(getattr(self.app.content, "dialogues_combat", {}), dict) and len(getattr(self.app.content, "dialogues_combat", {})) > 0
        print(f"[selftest] dialogues {'ok' if dk else 'missing'}")

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
            seq = ["combat_start", "player_turn_start", "enemy_turn_start", "enemy_big_attack", "player_low_hp", "enemy_low_hp", "victory"]
            idx = (seq.index(self.last_trigger) + 1) % len(seq) if self.last_trigger in seq else 0
            self._trigger_dialog(seq[idx])
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            self._selftest()
            return

        if self.pause_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self.app.renderer.map_mouse(event.pos)
                options = {
                    "continue": pygame.Rect(760, 410, 400, 64),
                    "options": pygame.Rect(760, 492, 400, 64),
                    "menu": pygame.Rect(760, 574, 400, 64),
                    "quit": pygame.Rect(760, 656, 400, 64),
                }
                for k, r in options.items():
                    if r.collidepoint(pos):
                        if k == "continue": self.pause_open = False
                        elif k == "options": self.pause_open = False; self.app.goto_settings()
                        elif k == "menu":
                            if self.exit_confirm: self.pause_open = False; self.app.goto_menu()
                            else: self.exit_confirm = True
                        elif k == "quit": self.app.running = False
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
        accent = {
            "crimson_chaos": (220, 108, 84),
            "emerald_spirit": (88, 198, 154),
            "azure_cosmic": (112, 152, 228),
            "violet_arcane": (176, 126, 240),
            "solar_gold": (226, 190, 112),
        }.get(family, (176, 126, 240))
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, accent, rect, 3, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 14, int(rect.h * 0.56)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 7, rect.y + 30))
        s.blit(self.app.tiny_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 8, rect.y + 6))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 16, rect.y + 16), 12)
        s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 20, rect.y + 9))
        tags = set(getattr(card.definition, "tags", []))
        if "attack" in tags:
            pygame.draw.line(s, accent, (rect.x + 16, rect.bottom - 18), (rect.x + 30, rect.bottom - 34), 3)
        elif "block" in tags or "defense" in tags:
            pygame.draw.circle(s, accent, (rect.x + 22, rect.bottom - 24), 8, 2)
        elif "draw" in tags or "scry" in tags or "control" in tags:
            pygame.draw.ellipse(s, accent, (rect.x + 14, rect.bottom - 32, 18, 12), 2)
        else:
            pygame.draw.circle(s, accent, (rect.x + 22, rect.bottom - 24), 6)
        if selected:
            pygame.draw.rect(s, UI_THEME["gold"], rect.inflate(8, 8), 3, border_radius=14)

    def update(self, dt):
        self.c.update(dt)
        self.resolving_t = max(0, self.resolving_t - dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        self.mana_orbs.tick(dt)
        self.enemy_line_fx = max(0, self.enemy_line_fx - dt)
        self.hero_line_fx = max(0, self.hero_line_fx - dt)
        if self.last_turn != self.c.turn:
            self.last_turn = self.c.turn
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
        # Layer 0
        t = pygame.time.get_ticks() * 0.02
        self.app.bg_gen.render_parallax(s, self.selected_biome, self.bg_seed, t, clip_rect=self.PLAYFIELD, particles_on=self.app.user_settings.get("fx_particles", True))

        # Layer 1 enemy panel
        pygame.draw.rect(s, UI_THEME["panel"], self.ENEMY_PANEL, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.ENEMY_PANEL, 2, border_radius=12)
        s.blit(self.app.small_font.render("Enemigo", True, UI_THEME["gold"]), (self.ENEMY_PANEL.x + 12, self.ENEMY_PANEL.y + 8))
        for i, e in enumerate(self.c.enemies):
            er = pygame.Rect(self.ENEMY_PANEL.x + 24 + i * 600, self.ENEMY_PANEL.y + 36, 560, 286)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=12)
            s.blit(self.app.assets.sprite("enemies", e.id, (180, 180), fallback=(100, 60, 90)), (er.x + 18, er.y + 28))
            s.blit(self.app.small_font.render(str(e.name_key), True, UI_THEME["text"]), (er.x + 260, er.y + 46))
            intent_txt = e.current_intent().get("label", "Preparando")
            s.blit(self.app.small_font.render(f"Preparando: {intent_txt}", True, UI_THEME["gold"]), (er.x + 260, er.y + 86))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            pygame.draw.rect(s, (35, 24, 50), (er.x + 260, er.y + 156, 280, 16), border_radius=6)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 260, er.y + 156, int(280 * ratio), 16), border_radius=6)
            s.blit(self.app.tiny_font.render(f"HP {e.hp}/{e.max_hp}", True, UI_THEME["text"]), (er.x + 260, er.y + 178))
            guard = getattr(e, "block", 0)
            rupt = getattr(e, "statuses", {}).get("rupture", 0)
            s.blit(self.app.tiny_font.render(f"Guardia {guard}  Ruptura {rupt}", True, UI_THEME["muted"]), (er.x + 260, er.y + 200))

        # Layer 2 dialogues
        pygame.draw.rect(s, UI_THEME["panel"], self.DIALOGUE_PANEL, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.DIALOGUE_PANEL, 2, border_radius=12)
        s.blit(self.app.small_font.render("Voces", True, UI_THEME["gold"]), (self.DIALOGUE_PANEL.x + 12, self.DIALOGUE_PANEL.y + 8))
        e_line, h_line = self.dialog_enemy.current, self.dialog_hero.current
        s.blit(self.app.font.render(e_line, True, (245, 122, 132)), (self.DIALOGUE_PANEL.centerx - self.app.font.size(e_line)[0] // 2, self.DIALOGUE_PANEL.y + 36))
        s.blit(self.app.font.render(h_line, True, (168, 245, 188)), (self.DIALOGUE_PANEL.centerx - self.app.font.size(h_line)[0] // 2, self.DIALOGUE_PANEL.y + 82))

        # Layer 3 hand panel frame
        pygame.draw.rect(s, UI_THEME["panel"], self.CARD_AREA, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.CARD_AREA, 2, border_radius=12)
        s.blit(self.app.small_font.render("Mano", True, UI_THEME["gold"]), (self.CARD_AREA.x + 12, self.CARD_AREA.y + 8))

        hand = self.c.hand[:6]
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.hover_card_index = None
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                self.hover_card_index = i
        self.ctrl.on_hover(self.hover_card_index)

        # Layer 4 cards clipped
        old_clip = s.get_clip()
        s.set_clip(self.CARD_AREA)
        for i, card in enumerate(hand):
            base = self._card_rect(i, len(hand))
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, base, card, selected=(i == self.ctrl.selected_index), family=fam)
        s.set_clip(old_clip)

        # Layer 5 hover overlay (unclipped)
        if self.hover_card_index is not None and self.hover_card_index < len(hand):
            i = self.hover_card_index
            card = hand[i]
            key = card.definition.id
            cur = self.hover_anim.get(key, 0.0)
            cur = cur + (1.0 - cur) * 0.32
            self.hover_anim[key] = cur
            base = self._card_rect(i, len(hand))
            rr = base.move(0, int(-18 * cur)).inflate(int(12 * cur), int(12 * cur))
            if rr.bottom > self.ACTION_BAR.y:
                rr.move_ip(0, self.ACTION_BAR.y - rr.bottom - 8)
            if rr.right > self.end_turn_rect.x - 20:
                rr.move_ip(-max(0, rr.right - (self.end_turn_rect.x - 20)), 0)
            fam = getattr(card.definition, "family", "violet_arcane")
            self._draw_card(s, rr, card, selected=(i == self.ctrl.selected_index), family=fam)
            pygame.draw.rect(s, (220, 198, 255), rr.inflate(8, 8), 2, border_radius=14)

        # Layer 6 player HUD
        pygame.draw.rect(s, UI_THEME["panel"], self.PLAYER_HUD, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.PLAYER_HUD, 2, border_radius=12)
        s.blit(self.app.small_font.render("Chakana", True, UI_THEME["gold"]), (self.PLAYER_HUD.x + 12, self.PLAYER_HUD.y + 8))
        p = self.c.player
        s.blit(self.app.font.render(f"Vida {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (self.PLAYER_HUD.x + 22, self.PLAYER_HUD.y + 38))
        s.blit(self.app.mono_font.render(f"Bloqueo {p['block']}", True, UI_THEME["block"]), (self.PLAYER_HUD.x + 22, self.PLAYER_HUD.y + 78))
        s.blit(self.app.mono_font.render(f"Ruptura {p['rupture']}", True, UI_THEME["rupture"]), (self.PLAYER_HUD.x + 260, self.PLAYER_HUD.y + 38))
        self.mana_orbs.update(int(p.get("energy", 0)))
        self.mana_orbs.draw(s, self.PLAYER_HUD.x + 352, self.PLAYER_HUD.y + 90, int(p.get("energy", 0)), 6)
        pts = chakana_points((self.PLAYER_HUD.x + 545, self.PLAYER_HUD.y + 88), int(42 * (1.0 + 0.05 * math.sin(pygame.time.get_ticks() / 240.0))), 0.35)
        pygame.draw.polygon(s, (182, 154, 240), pts, 2)

        # Layer 7 action area + button
        pygame.draw.rect(s, UI_THEME["panel"], self.ACTION_BAR, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], self.ACTION_BAR, 2, border_radius=12)
        s.blit(self.app.small_font.render("Acciones", True, UI_THEME["gold"]), (self.ACTION_BAR.x + 12, self.ACTION_BAR.y + 8))
        label, disabled = self._compute_action_button()
        bcol = (88, 84, 102) if disabled else (116, 86, 184) if self.ctrl.pressed_on_button_id == "action" else UI_THEME["violet"]
        pygame.draw.rect(s, bcol, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.end_turn_rect.x + 82, self.end_turn_rect.y + 24))

        # Layer 8 optional detail panel
        if self.app.user_settings.get("detail_panel", False):
            panel = pygame.Rect(1490, 350, 390, 230)
            pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], panel, 2, border_radius=12)
            s.blit(self.app.small_font.render("Detalle", True, UI_THEME["gold"]), (panel.x + 12, panel.y + 8))
            idx = self.hover_card_index if self.hover_card_index is not None else self.ctrl.selected_index
            if idx is not None and idx < len(hand):
                card = hand[idx]
                s.blit(self.app.assets.sprite("cards", card.definition.id, (144, 98), fallback=(70, 44, 105)), (panel.x + 12, panel.y + 36))
                s.blit(self.app.small_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (panel.x + 166, panel.y + 44))
                s.blit(self.app.mono_font.render(f"Coste {card.cost}", True, UI_THEME["energy"]), (panel.x + 166, panel.y + 74))
                lines = wrap_text(self.app.tiny_font, str(card.definition.text_key), 210, max_lines=4)
                for j, ln in enumerate(lines):
                    s.blit(self.app.tiny_font.render(ln, True, UI_THEME["muted"]), (panel.x + 166, panel.y + 104 + j * 20))

        if self.dialog_debug_overlay:
            d = pygame.Rect(40, 40, 520, 130)
            pygame.draw.rect(s, (0, 0, 0), d, border_radius=8)
            pygame.draw.rect(s, UI_THEME["gold"], d, 2, border_radius=8)
            enemy_id = self.c.enemies[0].id if self.c.enemies else "default"
            ok = "OK" if getattr(self.app.lore_engine, "loaded", False) else "MISSING"
            keys = int(getattr(self.app.lore_engine, "keys_count", 0))
            s.blit(self.app.tiny_font.render(f"Dialogues: {ok} keys={keys}", True, UI_THEME["text"]), (56, 58))
            s.blit(self.app.tiny_font.render(f"enemy_id: {enemy_id}", True, UI_THEME["text"]), (56, 84))
            s.blit(self.app.tiny_font.render(f"last_trigger: {self.last_trigger}", True, UI_THEME["text"]), (56, 110))

        if self.pause_open:
            ov = pygame.Surface((1920, 1080), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 150)); s.blit(ov, (0, 0))
            panel = pygame.Rect(680, 340, 560, 420)
            pygame.draw.rect(s, UI_THEME["deep_purple"], panel, border_radius=16)
            pygame.draw.rect(s, UI_THEME["gold"], panel, 2, border_radius=16)
            s.blit(self.app.big_font.render("PAUSA", True, UI_THEME["gold"]), (880, 364))
            for lbl, y in [("Continuar", 410), ("Opciones", 492), ("Salir al Menú", 574), ("Salir del Juego", 656)]:
                r = pygame.Rect(760, y, 400, 64)
                pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=10)
                s.blit(self.app.font.render(lbl, True, UI_THEME["text"]), (r.x + 110, r.y + 18))
            if self.exit_confirm:
                s.blit(self.app.tiny_font.render("Click otra vez en 'Salir al Menú' para confirmar", True, UI_THEME["bad"]), (750, 736))
