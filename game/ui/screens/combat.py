import pygame

from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


def wrap_text(font, text, width):
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
    return lines


class CombatScreen:
    TOPBAR = pygame.Rect(0, 0, INTERNAL_WIDTH, 110)
    ENEMY_PANEL = pygame.Rect(40, 120, INTERNAL_WIDTH - 80, 360)
    DIALOGUE_PANEL = pygame.Rect(260, 490, INTERNAL_WIDTH - 520, 130)
    PLAYER_HUD = pygame.Rect(40, 630, INTERNAL_WIDTH - 80, 120)
    CARD_AREA = pygame.Rect(40, 760, INTERNAL_WIDTH - 80, 220)
    ACTION_BAR = pygame.Rect(40, 990, INTERNAL_WIDTH - 80, 80)

    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.selected_card_index = None
        self.scry_selected = None
        self.tooltip = None
        self.log_lines = []
        self.log_visible = True
        self.banner = TypewriterBanner()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0
        self.dialog_jitter = 0.0
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)

        self.end_turn_rect = pygame.Rect(self.ACTION_BAR.right - 320, self.ACTION_BAR.y + 8, 300, 64)
        self.status_rect = pygame.Rect(self.ACTION_BAR.right - 640, self.ACTION_BAR.y + 8, 280, 64)
        self.scry_confirm_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 140, 680, 280, 66)

        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self._set_intro()

    def _set_intro(self):
        self.banner.set(self.app.loc.t("lore_short_1"), 2.5)
        self._trigger_dialog("start")

    def draw_panel(self, surface, rect, title=None):
        pygame.draw.rect(surface, UI_THEME["panel"], rect, border_radius=12)
        pygame.draw.rect(surface, UI_THEME["accent_violet"], rect, 2, border_radius=12)
        self.apply_inset_shadow(surface, rect)
        if title:
            surface.blit(self.app.small_font.render(title, True, UI_THEME["gold"]), (rect.x + 12, rect.y + 8))

    def draw_separator(self, surface, y):
        pygame.draw.line(surface, (80, 66, 110), (20, y), (INTERNAL_WIDTH - 20, y), 2)

    def apply_inset_shadow(self, surface, panel):
        sh = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 28), sh.get_rect(), width=6, border_radius=12)
        surface.blit(sh, panel.topleft)

    def _enemy_rect(self, idx):
        return pygame.Rect(self.ENEMY_PANEL.x + 24 + idx * 520, self.ENEMY_PANEL.y + 48, 500, 286)

    def _card_rect(self, vis_idx, total, hovered=False):
        card_w, card_h = 220, 320
        gap = 18
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = self.CARD_AREA.centerx - total_w // 2
        y = self.CARD_AREA.y - 90
        r = pygame.Rect(start_x + vis_idx * (card_w + gap), y, card_w, card_h)
        return r.inflate(40, 40) if hovered else r

    def _intent_text(self, enemy):
        intent = enemy.current_intent()
        kind = intent.get("intent", "attack")
        val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
        num = val[0] if isinstance(val, list) else val
        if kind == "attack":
            return f"Daño {num}", UI_THEME["bad"]
        if kind == "defend":
            return f"Guardia {num}", UI_THEME["block"]
        if kind == "debuff":
            return "Maldición", UI_THEME["gold"]
        return "Canaliza", UI_THEME["accent_violet"]

    def _dialog_pick(self, side, trigger, enemy_id):
        arr = self.app.lore_service.dialogue(side, trigger, enemy_id)
        if arr:
            return self.app.rng.choice(arr)
        fallback = self.app.design_value("DIALOGUE_FALLBACK_ENEMY" if side == "enemy" else "DIALOGUE_FALLBACK_CHAKANA", "")
        return fallback.split("|")[0].split(":")[-1].strip() if fallback else "..."

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "voidling"
        self.dialog_enemy.set(self._dialog_pick("enemy", trigger, enemy_id), 2.2)
        self.dialog_hero.set(self._dialog_pick("chakana", trigger, enemy_id), 2.2)
        self.dialog_cd = 3.8
        self.dialog_jitter = 0.28
        self.app.sfx.play("whisper")

    def _execute_selected(self):
        card = self.c.hand[self.selected_card_index] if self.selected_card_index is not None and self.selected_card_index < len(self.c.hand) else None
        if not card:
            self.c.end_turn()
            self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
            return
        if card.cost > self.c.player["energy"]:
            return
        target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None) if card.definition.target == "enemy" else None
        if card.definition.target == "enemy" and target_idx is None:
            return
        self.c.play_card(self.selected_card_index, target_idx)
        self.selected_card_index = None

    def _handle_scry_event(self, event):
        cards = self.c.scry_pending
        if not cards:
            return False
        rects = [pygame.Rect(360 + i * 250, 320, 220, 320) for i in range(len(cards))]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(rects):
                if r.collidepoint(pos):
                    self.scry_selected = i
                    return True
            if self.scry_confirm_rect.collidepoint(pos) and self.scry_selected is not None:
                self.c.apply_scry_order(cards)
                self.log_lines.insert(0, f"Elegiste {cards[self.scry_selected].definition.id}")
                self.app.sfx.play("ui_click")
                self.scry_selected = None
                return True
        return True

    def handle_event(self, event):
        if self.c.scry_pending and self._handle_scry_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self._execute_selected()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected_card_index = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self._execute_selected(); return
            if self.status_rect.collidepoint(pos):
                self.log_visible = not self.log_visible; return
            for i, _ in enumerate(self.c.hand[:6]):
                if self._card_rect(i, min(6, len(self.c.hand))).collidepoint(pos):
                    self.selected_card_index = i
                    self.app.sfx.play("card_pick")
                    return

    def update(self, dt):
        self.c.update(dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        self.dialog_jitter = max(0, self.dialog_jitter - dt)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            self.turn_timer -= dt
            if self.turn_timer <= 0:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        for ev in self.c.pop_events():
            if ev["type"] == "damage":
                self.log_lines.insert(0, f"{ev['target']}: -{ev['amount']} Vida")
                if ev["target"] == "player" and ev["amount"] >= 9:
                    self._trigger_dialog("player_low_hp")
            elif ev["type"] == "block":
                self.log_lines.insert(0, f"{ev['target']}: +{ev['amount']} Guardia")
                if ev["target"] != "player":
                    self._trigger_dialog("enemy_intent_reveal")
        if self.c.player["hp"] <= max(10, self.c.player["max_hp"] * 0.3):
            self._trigger_dialog("player_low_hp")
        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("enemy_low_hp")
        if self.is_boss and self.c.turn % 4 == 0:
            self._trigger_dialog("boss_phase")
        self.log_lines = self.log_lines[:8]
        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected=False):
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_border"], rect, 2, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 16, int(rect.h * 0.62)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 8, rect.y + 36))
        s.blit(self.app.card_title_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 10, rect.y + 6))
        lines = wrap_text(self.app.card_text_font, self.app.loc.t(card.definition.text_key), rect.w - 18)[:3]
        for i, line in enumerate(lines):
            s.blit(self.app.card_text_font.render(line, True, UI_THEME["muted"]), (rect.x + 10, rect.y + int(rect.h * 0.7) + i * 24))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 18, rect.y + 18), 14)
        s.blit(self.app.small_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 24, rect.y + 7))
        if selected:
            pygame.draw.rect(s, UI_THEME["accent_violet"], rect.inflate(8, 8), 3, border_radius=14)

    def render(self, s):
        sky, silhouettes, fog = self.app.bg_gen.get_layers(self.selected_biome, self.bg_seed)
        p = int((pygame.time.get_ticks() * 0.02) % 24)
        s.blit(sky, (0, 0)); s.blit(silhouettes, (-p, 0)); s.blit(fog, (p // 2, 0))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.tooltip = None

        self.draw_panel(s, self.TOPBAR, "TOPBAR")
        self.draw_panel(s, self.ENEMY_PANEL, "ENEMY_PANEL")
        self.draw_panel(s, self.DIALOGUE_PANEL, "DIALOGUE_PANEL")
        self.draw_panel(s, self.PLAYER_HUD, "PLAYER_HUD")
        self.draw_panel(s, self.CARD_AREA, "CARD_AREA")
        self.draw_panel(s, self.ACTION_BAR, "ACTION_BAR")
        for y in [self.ENEMY_PANEL.bottom + 4, self.DIALOGUE_PANEL.bottom + 4, self.PLAYER_HUD.bottom + 4]:
            self.draw_separator(s, y)

        s.blit(self.app.big_font.render(self.app.design_value("CANON_MENU_TITLE", "Chakana Purple Wizard"), True, UI_THEME["gold"]), (54, 28))
        lore = self.banner.current
        s.blit(self.app.small_font.render(lore, True, UI_THEME["text"]), (self.TOPBAR.right - self.app.small_font.size(lore)[0] - 40, 42))

        jit = int(2 * pygame.math.Vector2(1, 0).rotate(pygame.time.get_ticks() * 0.5).x) if self.dialog_jitter > 0 else 0
        enemy_line = self.dialog_enemy.current
        hero_line = self.dialog_hero.current
        s.blit(self.app.font.render(enemy_line, True, UI_THEME["bad"]), (self.DIALOGUE_PANEL.centerx - self.app.font.size(enemy_line)[0] // 2 + jit, self.DIALOGUE_PANEL.y + 30))
        s.blit(self.app.font.render(hero_line, True, UI_THEME["good"]), (self.DIALOGUE_PANEL.centerx - self.app.font.size(hero_line)[0] // 2 - jit, self.DIALOGUE_PANEL.y + 72))

        pstate = self.c.player
        s.blit(self.app.font.render(f"Vida {pstate['hp']}/{pstate['max_hp']}", True, UI_THEME["text"]), (self.PLAYER_HUD.x + 20, self.PLAYER_HUD.y + 44))
        s.blit(self.app.font.render(f"Guardia {pstate['block']}", True, UI_THEME["block"]), (self.PLAYER_HUD.x + 330, self.PLAYER_HUD.y + 44))
        s.blit(self.app.font.render(f"Quiebre {pstate['rupture']}", True, UI_THEME["rupture"]), (self.PLAYER_HUD.x + 560, self.PLAYER_HUD.y + 44))
        s.blit(self.app.font.render("Maná", True, UI_THEME["text"]), (self.PLAYER_HUD.x + 780, self.PLAYER_HUD.y + 44))
        for i in range(5):
            pygame.draw.circle(s, UI_THEME["energy"] if i < pstate["energy"] else (65, 68, 90), (self.PLAYER_HUD.x + 860 + i * 32, self.PLAYER_HUD.y + 56), 11)

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=12)
            s.blit(self.app.assets.sprite("enemies", e.id, (150, 150), fallback=(100, 60, 90)), (er.x + 14, er.y + 18))
            intent_card = pygame.Rect(er.x + 178, er.y + 16, 302, 108)
            pygame.draw.rect(s, UI_THEME["panel_2"], intent_card, border_radius=10)
            intent, icolor = self._intent_text(e)
            s.blit(self.app.font.render(intent, True, icolor), (intent_card.x + 14, intent_card.y + 40))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            s.blit(self.app.small_font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 16, er.y + 184))
            pygame.draw.rect(s, (35, 24, 50), (er.x + 16, er.y + 220, 468, 18), border_radius=7)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 16, er.y + 220, int(468 * ratio), 18), border_radius=7)
            s.blit(self.app.small_font.render(f"HP {e.hp}/{e.max_hp} Guardia {e.block}", True, UI_THEME["text"]), (er.x + 16, er.y + 246))

        hand = self.c.hand[:6]
        hover_idx = None
        for i in range(len(hand)):
            if self._card_rect(i, len(hand)).collidepoint(mouse):
                hover_idx = i
        for i, card in enumerate(hand):
            rr = self._card_rect(i, len(hand), hovered=(i == hover_idx))
            self._draw_card(s, rr, card, selected=(i == self.selected_card_index))
            if rr.collidepoint(mouse):
                self.tooltip = self.app.loc.t(card.definition.text_key)

        pygame.draw.rect(s, UI_THEME["panel"], self.status_rect, border_radius=10)
        s.blit(self.app.small_font.render("Registro", True, UI_THEME["text"]), (self.status_rect.x + 90, self.status_rect.y + 22))

        selected = self.c.hand[self.selected_card_index] if self.selected_card_index is not None and self.selected_card_index < len(self.c.hand) else None
        label = "ATACAR" if selected else self.app.loc.t("button_end_turn")
        bcol = UI_THEME["violet"] if not selected or selected.cost <= pstate["energy"] else (90, 78, 110)
        pygame.draw.rect(s, bcol, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.end_turn_rect.x + 88, self.end_turn_rect.y + 18))

        if self.log_visible:
            log_rect = pygame.Rect(self.ACTION_BAR.x + 10, self.ACTION_BAR.y + 6, 760, 68)
            pygame.draw.rect(s, UI_THEME["panel"], log_rect, border_radius=10)
            for i, line in enumerate(self.log_lines[:2]):
                col = UI_THEME["bad"] if "-" in line else UI_THEME["block"] if "+" in line else UI_THEME["muted"]
                s.blit(self.app.small_font.render(line, True, col), (log_rect.x + 14, log_rect.y + 12 + i * 26))

        if self.c.scry_pending:
            ov = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170)); s.blit(ov, (0, 0))
            modal = pygame.Rect(300, 240, 1320, 560)
            self.draw_panel(s, modal, "SELECCIONA 1")
            for i, card in enumerate(self.c.scry_pending):
                r = pygame.Rect(360 + i * 250, 320, 220, 320)
                hov = r.collidepoint(mouse)
                if hov:
                    pygame.draw.rect(s, (200, 170, 255), r.inflate(12, 12), 2, border_radius=14)
                self._draw_card(s, r, card, selected=(i == self.scry_selected))
                if i == self.scry_selected:
                    pygame.draw.rect(s, UI_THEME["gold"], r.inflate(16, 16), 4, border_radius=16)
                    s.blit(self.app.small_font.render("SELECCIONADA", True, UI_THEME["gold"]), (r.x + 24, r.y - 28))
            enabled = self.scry_selected is not None
            pygame.draw.rect(s, UI_THEME["violet"] if enabled else (76, 72, 94), self.scry_confirm_rect, border_radius=10)
            s.blit(self.app.font.render("Confirmar", True, UI_THEME["text"]), (self.scry_confirm_rect.x + 86, self.scry_confirm_rect.y + 18))

        if self.tooltip and not self.c.scry_pending:
            tr = pygame.Rect(self.ACTION_BAR.x + 10, self.ACTION_BAR.y - 62, 620, 54)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            s.blit(self.app.card_text_font.render(self.tooltip, True, UI_THEME["text"]), (tr.x + 10, tr.y + 16))
