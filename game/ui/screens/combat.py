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
    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.selected_card_index = None
        self.tooltip = None
        self.log_lines = []
        self.log_visible = True
        self.banner = TypewriterBanner()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        self.scry_drag_idx = None

        # 1920x1080 grid zones
        self.top_bar_h = 120
        self.battle_h = 520
        self.player_hud_h = 120
        self.cards_h = 180
        self.buttons_h = 140
        self.zone_battle_y = self.top_bar_h
        self.zone_hud_y = self.zone_battle_y + self.battle_h
        self.zone_cards_y = self.zone_hud_y + self.player_hud_h
        self.zone_buttons_y = self.zone_cards_y + self.cards_h

        self.end_turn_rect = pygame.Rect(INTERNAL_WIDTH - 360, self.zone_buttons_y + 28, 300, 84)
        self.status_rect = pygame.Rect(INTERNAL_WIDTH - 680, self.zone_buttons_y + 28, 280, 84)

        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self._set_intro()

    def _set_intro(self):
        self.banner.set(self.app.loc.t("lore_short_1"), 2.5)
        self._trigger_dialog("intro")

    def _enemy_rect(self, idx):
        return pygame.Rect(90 + idx * 430, self.zone_battle_y + 64, 390, 330)

    def _card_rect(self, vis_idx, total, hovered=False):
        card_w, card_h = 220, 320
        gap = 18
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = (INTERNAL_WIDTH - total_w) // 2
        y = self.zone_cards_y - 130
        r = pygame.Rect(start_x + vis_idx * (card_w + gap), y, card_w, card_h)
        if hovered:
            r = pygame.Rect(r.x - 20, r.y - 20, 260, 360)
        return r

    def _intent_text(self, enemy):
        intent = enemy.current_intent()
        kind = intent.get("intent", "attack")
        val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
        num = val[0] if isinstance(val, list) else val
        if kind == "attack":
            label = self.app.design_value("CANON_INTENT_ATTACK", "Preparando golpe: {value}").format(value=f"{self.app.design_value('CANON_LABEL_DANO', 'Daño')} {num}")
            return label, UI_THEME["bad"]
        if kind == "defend":
            label = self.app.design_value("CANON_INTENT_DEFEND", "Se protege: {value}").format(value=f"{self.app.design_value('CANON_LABEL_GUARDIA', 'Guardia')} {num}")
            return label, UI_THEME["block"]
        if kind == "debuff":
            return self.app.design_value("CANON_INTENT_DEBUFF", "Lanza Maldición"), UI_THEME["gold"]
        return self.app.design_value("CANON_INTENT_BUFF", "Canaliza poder"), UI_THEME["accent_violet"]

    def _selected_card(self):
        if self.selected_card_index is None or self.selected_card_index >= len(self.c.hand):
            return None
        return self.c.hand[self.selected_card_index]

    def _dialog_pick(self, side, trigger, enemy_id):
        data = self.app.lore_data
        if side == "enemy":
            arr = data.get("enemy", {}).get(enemy_id, {}).get(trigger, [])
            fallback = self.app.design_value("DIALOGUE_FALLBACK_ENEMY", "")
        else:
            arr = data.get("chakana", {}).get(trigger, [])
            fallback = self.app.design_value("DIALOGUE_FALLBACK_CHAKANA", "")
        if not arr and fallback:
            pairs = [p for p in fallback.split("|") if ":" in p]
            table = {k.strip(): v.strip() for k, v in (x.split(":", 1) for x in pairs)}
            txt = table.get(trigger)
            if txt:
                arr = [txt]
        return self.app.rng.choice(arr) if arr else "..."

    def _trigger_dialog(self, trigger):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "voidling"
        self.dialog_enemy.set(self._dialog_pick("enemy", trigger, enemy_id), 2.4)
        self.dialog_hero.set(self._dialog_pick("chakana", trigger, enemy_id), 2.4)
        self.dialog_cd = 4.0

    def _execute_selected(self):
        card = self._selected_card()
        if not card:
            self.c.end_turn()
            self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
            return
        if card.cost > self.c.player["energy"]:
            return
        if card.definition.target == "enemy":
            target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
            if target_idx is None:
                return
            self.c.play_card(self.selected_card_index, target_idx)
        else:
            self.c.play_card(self.selected_card_index, None)
        self.selected_card_index = None

    def _handle_scry_event(self, event):
        cards = self.c.scry_pending
        if not cards:
            return False
        rects = [pygame.Rect(420 + i * 250, 320, 220, 320) for i in range(len(cards))]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(rects):
                if r.collidepoint(pos):
                    self.scry_drag_idx = i
                    return True
            if pygame.Rect(800, 670, 320, 70).collidepoint(pos):
                self.c.apply_scry_order(cards)
                self.scry_drag_idx = None
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.scry_drag_idx is not None:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(rects):
                if r.collidepoint(pos) and i != self.scry_drag_idx:
                    cards[self.scry_drag_idx], cards[i] = cards[i], cards[self.scry_drag_idx]
                    break
            self.scry_drag_idx = None
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
            for i, e in enumerate(self.c.enemies):
                if self._enemy_rect(i).collidepoint(pos) and e.alive and self.selected_card_index is not None:
                    self.c.play_card(self.selected_card_index, i)
                    self.selected_card_index = None
                    return
            for i, _ in enumerate(self.c.hand[:6]):
                if self._card_rect(i, min(6, len(self.c.hand))).collidepoint(pos):
                    self.selected_card_index = i
                    self.app.sfx.play("card_pick")
                    return

    def update(self, dt):
        self.c.update(dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            self.turn_timer -= dt
            if self.turn_timer <= 0:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        for ev in self.c.pop_events():
            if ev["type"] == "damage":
                self.log_lines.insert(0, f"{ev['target']}: -{ev['amount']} Vida")
                if ev["target"] == "player" and ev["amount"] >= 9:
                    self._trigger_dialog("big_hit")
            elif ev["type"] == "block":
                self.log_lines.insert(0, f"{ev['target']}: +{ev['amount']} Guardia")
        self.log_lines = self.log_lines[:8]
        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("low_hp")
        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected=False):
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_border"], rect, 2, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 16, int(rect.h * 0.62)), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 8, rect.y + 36))
        title = self.app.loc.t(card.definition.name_key)
        s.blit(self.app.card_title_font.render(title, True, UI_THEME["text"]), (rect.x + 10, rect.y + 6))
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

        # zones
        pygame.draw.rect(s, UI_THEME["primary_purple"], (0, 0, INTERNAL_WIDTH, self.top_bar_h))
        pygame.draw.rect(s, (16, 14, 28), (0, self.zone_battle_y, INTERNAL_WIDTH, self.battle_h))
        pygame.draw.rect(s, UI_THEME["panel"], (0, self.zone_hud_y, INTERNAL_WIDTH, self.player_hud_h))
        pygame.draw.rect(s, (12, 14, 28), (0, self.zone_cards_y, INTERNAL_WIDTH, self.cards_h))
        pygame.draw.rect(s, UI_THEME["panel_2"], (0, self.zone_buttons_y, INTERNAL_WIDTH, self.buttons_h))

        s.blit(self.app.big_font.render(self.app.design_value("CANON_MENU_TITLE", "Chakana Purple Wizard"), True, UI_THEME["gold"]), (24, 26))
        lore = self.banner.current
        lore_w = self.app.font.size(lore)[0]
        s.blit(self.app.font.render(lore, True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - lore_w // 2, 44))
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            s.blit(self.app.font.render(f"⏱ {int(self.turn_timer)}s", True, UI_THEME["text"]), (INTERNAL_WIDTH - 160, 44))

        # centered stacked dialogue
        dialog_panel = pygame.Rect(INTERNAL_WIDTH // 2 - 420, self.zone_battle_y + 10, 840, 86)
        pygame.draw.rect(s, UI_THEME["panel"], dialog_panel, border_radius=10)
        enemy_line = f"Enemigo: {self.dialog_enemy.current}"
        hero_line = f"Chakana: {self.dialog_hero.current}"
        s.blit(self.app.small_font.render(enemy_line, True, UI_THEME["bad"]), (dialog_panel.x + 20, dialog_panel.y + 14))
        s.blit(self.app.small_font.render(hero_line, True, UI_THEME["good"]), (dialog_panel.x + 20, dialog_panel.y + 48))

        pstate = self.c.player
        hud = pygame.Rect(INTERNAL_WIDTH - 560, self.zone_hud_y + 8, 540, self.player_hud_h - 16)
        pygame.draw.rect(s, UI_THEME["panel_2"], hud, border_radius=10)
        s.blit(self.app.font.render(f"Vida {pstate['hp']}/{pstate['max_hp']}", True, UI_THEME["text"]), (hud.x + 20, hud.y + 16))
        s.blit(self.app.font.render(f"{self.app.design_value('CANON_LABEL_GUARDIA','Guardia')} {pstate['block']}", True, UI_THEME["block"]), (hud.x + 200, hud.y + 16))
        s.blit(self.app.font.render(f"{self.app.design_value('CANON_LABEL_QUIEBRE','Quiebre')} {pstate['rupture']}", True, UI_THEME["rupture"]), (hud.x + 20, hud.y + 54))
        s.blit(self.app.font.render(f"{self.app.design_value('CANON_LABEL_MANA','Maná')}", True, UI_THEME["text"]), (hud.x + 270, hud.y + 54))
        for i in range(5):
            pygame.draw.circle(s, UI_THEME["energy"] if i < pstate["energy"] else (65, 68, 90), (hud.x + 350 + i * 32, hud.y + 62), 11)

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=12)
            # enemy portrait
            s.blit(self.app.assets.sprite("enemies", e.id, (140, 140), fallback=(100, 60, 90)), (er.x + 12, er.y + 14))
            # intent card
            intent_card = pygame.Rect(er.x + 164, er.y + 12, 214, 120)
            pygame.draw.rect(s, UI_THEME["panel_2"], intent_card, border_radius=10)
            intent, icolor = self._intent_text(e)
            for li, line in enumerate(wrap_text(self.app.small_font, intent, intent_card.w - 12)[:3]):
                s.blit(self.app.small_font.render(line, True, icolor), (intent_card.x + 8, intent_card.y + 8 + li * 30))
            # hp bar
            ratio = max(0, e.hp) / max(1, e.max_hp)
            s.blit(self.app.small_font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 12, er.y + 166))
            pygame.draw.rect(s, (35, 24, 50), (er.x + 12, er.y + 198, 360, 18), border_radius=7)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 12, er.y + 198, int(360 * ratio), 18), border_radius=7)
            s.blit(self.app.small_font.render(f"Vida {e.hp}/{e.max_hp}", True, UI_THEME["text"]), (er.x + 12, er.y + 224))

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
        s.blit(self.app.small_font.render("Registro", True, UI_THEME["text"]), (self.status_rect.x + 90, self.status_rect.y + 30))

        selected = self._selected_card()
        label = "EJECUTAR" if selected and selected.definition.target != "enemy" else "ATACAR" if selected else self.app.loc.t("button_end_turn")
        bcol = UI_THEME["violet"]
        info = "Sin carta"
        if selected:
            info = f"Seleccionada: {self.app.loc.t(selected.definition.name_key)} (Costo {selected.cost})"
            if selected.cost > pstate["energy"]:
                bcol = (90, 78, 110)
                self.tooltip = "Energía insuficiente"
        pygame.draw.rect(s, bcol, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.end_turn_rect.x + 88, self.end_turn_rect.y + 24))
        s.blit(self.app.small_font.render(info, True, UI_THEME["muted"]), (self.end_turn_rect.x - 520, self.end_turn_rect.y + 32))

        if self.log_visible:
            log_rect = pygame.Rect(20, self.zone_buttons_y + 14, 760, 112)
            pygame.draw.rect(s, UI_THEME["panel"], log_rect, border_radius=10)
            s.blit(self.app.small_font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (log_rect.x + 14, log_rect.y + 10))
            for i, line in enumerate(self.log_lines[:3]):
                col = UI_THEME["bad"] if "-" in line else UI_THEME["block"] if "+" in line else UI_THEME["muted"]
                s.blit(self.app.small_font.render(line, True, col), (log_rect.x + 14, log_rect.y + 40 + i * 24))

        if self.c.scry_pending:
            ov = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160)); s.blit(ov, (0, 0))
            pygame.draw.rect(s, UI_THEME["deep_purple"], (340, 240, 1240, 560), border_radius=16)
            s.blit(self.app.big_font.render("Visión: mira y reordena", True, UI_THEME["gold"]), (700, 270))
            for i, card in enumerate(self.c.scry_pending):
                r = pygame.Rect(420 + i * 250, 320, 220, 320)
                self._draw_card(s, r, card, selected=(i == self.scry_drag_idx))
            pygame.draw.rect(s, UI_THEME["violet"], (800, 670, 320, 70), border_radius=10)
            s.blit(self.app.font.render("Confirmar", True, UI_THEME["text"]), (905, 692))

        if self.tooltip and not self.c.scry_pending:
            tr = pygame.Rect(20, self.zone_buttons_y + 14, 620, 70)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            s.blit(self.app.card_text_font.render(self.tooltip, True, UI_THEME["text"]), (tr.x + 10, tr.y + 24))
