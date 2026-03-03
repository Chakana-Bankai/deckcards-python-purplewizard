import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


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
        self.floaters = []
        self.tooltip = None
        self.log_lines = []
        self.log_visible = True
        self.help_visible = False
        self.banner = TypewriterBanner()
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        self.end_turn_rect = pygame.Rect(INTERNAL_WIDTH - 300, INTERNAL_HEIGHT - 146, 250, 90)
        self.status_rect = pygame.Rect(INTERNAL_WIDTH - 300, INTERNAL_HEIGHT - 250, 250, 84)
        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self.scry_drag_idx = None
        self._set_intro()

    def _set_intro(self):
        self.banner.set(self.app.loc.t("lore_short_1"), 2.5)
        self._trigger_dialog("intro")

    def _enemy_rect(self, idx):
        return pygame.Rect(120 + idx * 430, 150, 370, 405)

    def _card_rect(self, vis_idx, total):
        card_w, card_h, gap = 198, 282, 18
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = (INTERNAL_WIDTH - total_w) // 2
        base_y = int(INTERNAL_HEIGHT * 0.665)
        center = (total - 1) / 2.0
        arc = abs(vis_idx - center)
        return pygame.Rect(start_x + vis_idx * (card_w + gap), base_y + int(arc * 8), card_w, card_h)

    def _intent_text(self, enemy):
        intent = enemy.current_intent()
        kind = intent.get("intent", "attack")
        val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
        num = val[0] if isinstance(val, list) else val
        if kind == "attack":
            return f"Se prepara para: Daño {num}", UI_THEME["bad"]
        if kind == "defend":
            return f"Levanta Guardia {num}", UI_THEME["block"]
        if kind == "debuff":
            return f"Te marca con Debilidad ({intent.get('stacks', 1)})", UI_THEME["gold"]
        return f"Canaliza poder ({intent.get('stacks', 1)})", UI_THEME["accent_violet"]

    def _selected_card(self):
        if self.selected_card_index is None or self.selected_card_index >= len(self.c.hand):
            return None
        return self.c.hand[self.selected_card_index]

    def _dialog_pick(self, side, trigger, enemy_id):
        data = self.app.lore_data
        if side == "enemy":
            arr = data.get("enemy", {}).get(enemy_id, {}).get(trigger, [])
        else:
            arr = data.get("chakana", {}).get(trigger, [])
        if not arr:
            return "..."
        return self.app.rng.choice(arr)

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
            self._trigger_dialog("rare" if card.definition.rarity in {"rare", "legendary"} else "block_break")
        else:
            self.c.play_card(self.selected_card_index, None)
            self._trigger_dialog("intro")
        self.selected_card_index = None

    def _handle_scry_event(self, event):
        cards = self.c.scry_pending
        if not cards:
            return False
        rects = [pygame.Rect(520 + i * 220, 340, 200, 280) for i in range(len(cards))]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, r in enumerate(rects):
                if r.collidepoint(pos):
                    self.scry_drag_idx = i
                    return True
            if pygame.Rect(820, 650, 280, 64).collidepoint(pos):
                self.c.apply_scry_order(cards)
                self.scry_drag_idx = None
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.scry_drag_idx is not None:
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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self._execute_selected()
            elif event.key == pygame.K_h:
                self.help_visible = not self.help_visible
            elif event.key == pygame.K_ESCAPE:
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
            for i, c in enumerate(self.c.hand[:6]):
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
                self.c.end_turn(); self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        for ev in self.c.pop_events():
            if ev["type"] == "damage":
                self.floaters.append({"target": ev["target"], "text": f"-{ev['amount']}", "color": UI_THEME["bad"], "time": 0.9})
                self.log_lines.insert(0, f"{ev['target']}: -{ev['amount']} Vida")
                if ev["target"] == "player" and ev["amount"] >= 9:
                    self._trigger_dialog("big_hit")
            elif ev["type"] == "block":
                self.floaters.append({"target": ev["target"], "text": f"+{ev['amount']} G", "color": UI_THEME["block"], "time": 0.9})
                self.log_lines.insert(0, f"{ev['target']}: +{ev['amount']} Guardia")
        self.log_lines = self.log_lines[:8]
        self.floaters = [{**f, "time": f["time"] - dt} for f in self.floaters if f["time"] > 0]
        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("low_hp")
        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected=False):
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_border"], rect, 2, border_radius=12)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 16, 190), fallback=(70, 44, 105))
        s.blit(art, (rect.x + 8, rect.y + 36))
        s.blit(self.app.card_title_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (rect.x + 10, rect.y + 6))
        for i, line in enumerate(wrap_text(self.app.card_text_font, self.app.loc.t(card.definition.text_key), rect.w - 18)[:3]):
            s.blit(self.app.card_text_font.render(line, True, UI_THEME["muted"]), (rect.x + 10, rect.y + 230 + i * 20))
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

        pygame.draw.rect(s, UI_THEME["primary_purple"], (0, 0, INTERNAL_WIDTH, 96))
        s.blit(self.app.big_font.render("CHAKANA: Purple Wizard", True, UI_THEME["gold"]), (24, 24))
        s.blit(self.app.font.render(self.banner.current, True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - 270, 34))
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            s.blit(self.app.font.render(f"⏱ Tiempo de turno: {int(self.turn_timer)}s", True, UI_THEME["text"]), (INTERNAL_WIDTH - 330, 32))
        pygame.draw.rect(s, UI_THEME["panel"], (280, 104, 620, 72), border_radius=10)
        pygame.draw.rect(s, UI_THEME["panel"], (940, 104, 620, 72), border_radius=10)
        s.blit(self.app.small_font.render(f"Enemigo: {self.dialog_enemy.current}", True, UI_THEME["bad"]), (298, 130))
        s.blit(self.app.small_font.render(f"Chakana: {self.dialog_hero.current}", True, UI_THEME["good"]), (958, 130))

        hud = pygame.Rect(INTERNAL_WIDTH - 540, 186, 490, 300)
        pstate = self.c.player
        pygame.draw.rect(s, UI_THEME["panel"], hud, border_radius=12)
        s.blit(self.app.font.render(f"Vida {pstate['hp']}/{pstate['max_hp']}", True, UI_THEME["text"]), (hud.x + 20, hud.y + 20))
        s.blit(self.app.font.render(f"Guardia {pstate['block']}", True, UI_THEME["block"]), (hud.x + 20, hud.y + 62))
        s.blit(self.app.font.render(f"Quiebre {pstate['rupture']}", True, UI_THEME["rupture"]), (hud.x + 20, hud.y + 104))
        s.blit(self.app.font.render("Maná", True, UI_THEME["text"]), (hud.x + 20, hud.y + 148))
        for i in range(5):
            pygame.draw.circle(s, UI_THEME["energy"] if i < pstate["energy"] else (65, 68, 90), (hud.x + 120 + i * 42, hud.y + 164), 13)

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=14)
            s.blit(self.app.assets.sprite("enemies", e.id, (184, 184), fallback=(100, 60, 90)), (er.x + 12, er.y + 16))
            intent, icolor = self._intent_text(e)
            s.blit(self.app.big_font.render(intent, True, icolor), (er.x + 200, er.y + 46))
            s.blit(self.app.font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 12, er.y + 214))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            pygame.draw.rect(s, (35, 24, 50), (er.x + 12, er.y + 252, 340, 18), border_radius=7)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 12, er.y + 252, int(340 * ratio), 18), border_radius=7)
            s.blit(self.app.small_font.render(f"Vida {e.hp}/{e.max_hp}  Guardia {e.block}  Quiebre {e.statuses.get('rupture',0)}", True, UI_THEME["text"]), (er.x + 12, er.y + 278))

        pygame.draw.rect(s, (12, 14, 28), (0, int(INTERNAL_HEIGHT * 0.61), INTERNAL_WIDTH, INTERNAL_HEIGHT - int(INTERNAL_HEIGHT * 0.61)))
        hand = self.c.hand[:6]
        for i, card in enumerate(hand):
            rr = self._card_rect(i, len(hand))
            self._draw_card(s, rr, card, selected=(i == self.selected_card_index))
            if rr.collidepoint(mouse):
                self.tooltip = self.app.loc.t(card.definition.text_key)

        pygame.draw.rect(s, UI_THEME["panel_2"], self.status_rect, border_radius=10)
        s.blit(self.app.small_font.render("Registro", True, UI_THEME["text"]), (self.status_rect.x + 78, self.status_rect.y + 30))
        selected = self._selected_card()
        label = self.app.loc.t("button_end_turn")
        color = UI_THEME["violet"]
        info = "Sin carta"
        if selected:
            label = "ATACAR" if selected.definition.target == "enemy" else "EJECUTAR"
            info = f"Seleccionada: {self.app.loc.t(selected.definition.name_key)} (Costo {selected.cost})"
            if selected.cost > pstate["energy"]:
                color = (90, 78, 110)
                self.tooltip = "Energía insuficiente"
        pygame.draw.rect(s, color, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(label, True, UI_THEME["text"]), (self.end_turn_rect.x + 58, self.end_turn_rect.y + 26))
        s.blit(self.app.small_font.render(info, True, UI_THEME["muted"]), (self.end_turn_rect.x - 360, self.end_turn_rect.y + 32))

        if self.log_visible:
            logr = pygame.Rect(INTERNAL_WIDTH - 540, 500, 490, 300)
            pygame.draw.rect(s, UI_THEME["panel"], logr, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (logr.x + 14, logr.y + 12))
            for i, line in enumerate(self.log_lines[:8]):
                col = UI_THEME["bad"] if "-" in line else UI_THEME["block"] if "+" in line else UI_THEME["muted"]
                s.blit(self.app.small_font.render(line, True, col), (logr.x + 14, logr.y + 48 + i * 30))

        if self.c.scry_pending:
            ov = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160)); s.blit(ov, (0, 0))
            pygame.draw.rect(s, UI_THEME["deep_purple"], (430, 220, 1060, 520), border_radius=16)
            s.blit(self.app.big_font.render("Visión: mira y reordena", True, UI_THEME["gold"]), (690, 250))
            for i, card in enumerate(self.c.scry_pending):
                r = pygame.Rect(520 + i * 220, 340, 200, 280)
                self._draw_card(s, r, card, selected=(i == self.scry_drag_idx))
            pygame.draw.rect(s, UI_THEME["violet"], (820, 650, 280, 64), border_radius=10)
            s.blit(self.app.font.render("Confirmar", True, UI_THEME["text"]), (900, 668))

        if self.tooltip and not self.c.scry_pending:
            tr = pygame.Rect(min(mouse[0] + 16, INTERNAL_WIDTH - 420), min(mouse[1] + 14, INTERNAL_HEIGHT - 80), 400, 60)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            s.blit(self.app.card_text_font.render(self.tooltip, True, UI_THEME["text"]), (tr.x + 10, tr.y + 18))
