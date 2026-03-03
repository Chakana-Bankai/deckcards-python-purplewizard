import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class CombatScreen:
    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.hand_scroll = 0
        self.selected_card_index = None
        self.turn_banner_time = 1.0
        self.floaters = []
        self.tooltip = None
        self.log_visible = True
        self.log_lines = []
        self.banner = TypewriterBanner()
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
        self.end_turn_rect = pygame.Rect(INTERNAL_WIDTH - 260, INTERNAL_HEIGHT - 128, 210, 84)
        self.status_rect = pygame.Rect(INTERNAL_WIDTH - 260, INTERNAL_HEIGHT - 226, 210, 78)
        self._taunt("enemy_taunt_start")

    def _taunt(self, key):
        txt = self.app.loc.t(key)
        if txt == key:
            txt = self.app.loc.t("lore_short_2")
        self.banner.set(txt, 2.5)

    def _enemy_rect(self, idx):
        return pygame.Rect(90 + idx * 360, 160, 330, 360)

    def _visible_hand(self):
        hand = self.c.hand
        start = max(0, min(self.hand_scroll, max(0, len(hand) - 6)))
        return start, hand[start : start + 6]

    def _card_rect(self, vis_idx, total, hovered):
        card_w, card_h = 170, 250
        gap = 20
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = (INTERNAL_WIDTH - total_w) // 2
        base_y = int(INTERNAL_HEIGHT * 0.69)
        center = (total - 1) / 2.0
        arc = abs(vis_idx - center)
        x = start_x + vis_idx * (card_w + gap)
        y = base_y + int(arc * 7)
        if hovered:
            y -= 18
        return pygame.Rect(x, y, card_w, card_h)

    def _intent_text(self, enemy):
        intent = enemy.current_intent()
        kind = intent.get("intent", "attack")
        val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
        num = val[0] if isinstance(val, list) else val
        if kind == "attack":
            label = f"ATK {num}"
        elif kind == "defend":
            label = f"DEF {num}"
        elif kind == "debuff":
            label = f"DEBUFF {intent.get('status', 'weak')}({intent.get('stacks', 1)})"
        else:
            label = f"BUFF {intent.get('status', 'fury')}({intent.get('stacks', 1)})"
        return label, intent.get("name", label)

    def _play_card(self, idx, target_idx=0):
        if idx < 0 or idx >= len(self.c.hand):
            return
        card = self.c.hand[idx]
        if card.cost > self.c.player["energy"]:
            return
        if card.definition.target == "enemy" and target_idx is None:
            self.c.needs_target = idx
            self.selected_card_index = idx
            return
        self.c.play_card(idx, target_idx)
        self.app.sfx.play("card_play")

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.hand_scroll -= event.y
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
            elif event.key == pygame.K_ESCAPE:
                self.c.needs_target = None
                self.selected_card_index = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
                return
            if self.status_rect.collidepoint(pos):
                self.log_visible = not self.log_visible
                return
            for i, e in enumerate(self.c.enemies):
                if self._enemy_rect(i).collidepoint(pos) and e.alive:
                    if self.c.needs_target is not None:
                        self._play_card(self.c.needs_target, i)
                        self.c.needs_target = None
                        self.selected_card_index = None
                    return
            start, visible = self._visible_hand()
            mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
            hover_idx = None
            for i, _ in enumerate(visible):
                if self._card_rect(i, len(visible), False).inflate(0, 22).collidepoint(mouse):
                    hover_idx = i
            for i, _card in enumerate(visible):
                rr = self._card_rect(i, len(visible), hover_idx == i)
                if rr.collidepoint(pos):
                    self.selected_card_index = start + i
                    self.app.sfx.play("card_pick")
                    self._play_card(start + i, None)
                    return

    def update(self, dt):
        self.c.update(dt)
        self.turn_banner_time = max(0, self.turn_banner_time - dt)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            self.turn_timer -= dt
            if self.turn_timer <= 0:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)

        for ev in self.c.pop_events():
            if ev["type"] == "damage":
                target = ev["target"]
                amount = ev["amount"]
                self.floaters.append({"target": target, "text": f"-{amount}", "color": UI_THEME["bad"], "time": 0.7})
                self.log_lines.insert(0, f"{target}: -{amount} HP")
            elif ev["type"] == "block":
                target = ev["target"]
                amount = ev["amount"]
                self.floaters.append({"target": target, "text": f"+{amount} B", "color": UI_THEME["block"], "time": 0.7})
                self.log_lines.insert(0, f"{target}: +{amount} Bloque")
        self.log_lines = self.log_lines[:6]
        for f in self.floaters:
            f["time"] -= dt
        self.floaters = [f for f in self.floaters if f["time"] > 0]

        if self.c.result == "victory":
            self.app.goto_reward()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected=False, hovered=False):
        if hovered:
            shadow = pygame.Surface((rect.w + 18, rect.h + 18), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
            s.blit(shadow, (rect.x - 9, rect.y + 10))
        draw_rect = rect.copy()
        if hovered:
            draw_rect.inflate_ip(10, 14)
            draw_rect.center = rect.center
        pygame.draw.rect(s, UI_THEME["card_bg"], draw_rect, border_radius=10)
        art_h = int(draw_rect.h * 0.7)
        art = self.app.assets.sprite("cards", card.definition.id, (draw_rect.w - 16, art_h), fallback=(80, 60, 120))
        s.blit(art, (draw_rect.x + 8, draw_rect.y + 8))
        pygame.draw.rect(s, UI_THEME["card_border"], draw_rect, 2, border_radius=10)
        if selected or hovered:
            pygame.draw.rect(s, UI_THEME["violet"], draw_rect.inflate(8, 8), 3, border_radius=12)
        s.blit(self.app.card_title_font.render(self.app.loc.t(card.definition.name_key), True, UI_THEME["text"]), (draw_rect.x + 10, draw_rect.y + int(draw_rect.h * 0.72)))
        txt = self.app.loc.t(card.definition.text_key)
        s.blit(self.app.card_text_font.render(txt, True, UI_THEME["muted"]), (draw_rect.x + 10, draw_rect.y + int(draw_rect.h * 0.84)))
        pygame.draw.circle(s, UI_THEME["energy"], (draw_rect.right - 18, draw_rect.y + 18), 12)
        s.blit(self.app.card_text_font.render(str(card.cost), True, (15, 15, 22)), (draw_rect.right - 23, draw_rect.y + 9))
        return draw_rect

    def render(self, s):
        s.fill((14, 16, 28))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.tooltip = None

        top = pygame.Rect(0, 0, INTERNAL_WIDTH, 100)
        pygame.draw.rect(s, (20, 24, 38), top)
        combat_name = self.app.loc.t("node_boss") if self.is_boss else self.app.loc.t("node_combat")
        s.blit(self.app.font.render(combat_name, True, UI_THEME["gold"]), (24, 30))
        banner_text = self.banner.current
        s.blit(self.app.big_font.render(banner_text, True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - self.app.big_font.size(banner_text)[0] // 2, 32))

        p = self.c.player
        hud = pygame.Rect(INTERNAL_WIDTH - 520, 120, 470, 260)
        pygame.draw.rect(s, UI_THEME["panel"], hud, border_radius=12)
        s.blit(self.app.font.render(f"HP {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (INTERNAL_WIDTH - 498, 138))
        s.blit(self.app.font.render(f"Bloque {p['block']}", True, UI_THEME["block"]), (INTERNAL_WIDTH - 498, 174))
        s.blit(self.app.font.render(f"Ruptura {p['rupture']}", True, UI_THEME["rupture"]), (INTERNAL_WIDTH - 498, 210))
        s.blit(self.app.font.render("Energía", True, UI_THEME["text"]), (INTERNAL_WIDTH - 498, 246))
        wobble = pygame.time.get_ticks() / 240.0
        for i in range(5):
            r = 13 + int(1.5 * pygame.math.Vector2(1, 0).rotate(i * 37 + wobble * 40).x)
            pygame.draw.circle(s, UI_THEME["energy"] if i < p["energy"] else (65, 68, 90), (INTERNAL_WIDTH - 360 + i * 38, 258), max(10, r))
        yy = 300
        for name, stacks in p["statuses"].items():
            s.blit(self.app.card_text_font.render(f"{name}({stacks})", True, UI_THEME["muted"]), (INTERNAL_WIDTH - 498, yy))
            yy += 22

        battle_log = pygame.Rect(INTERNAL_WIDTH - 520, 410, 470, 360)
        if self.log_visible:
            pygame.draw.rect(s, UI_THEME["panel"], battle_log, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (INTERNAL_WIDTH - 498, 430))
            for i, line in enumerate(self.log_lines[:6]):
                s.blit(self.app.small_font.render(line, True, UI_THEME["muted"]), (INTERNAL_WIDTH - 498, 472 + i * 44))

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, (55, 45, 80) if e.alive else (44, 44, 44), er, border_radius=12)
            sp = self.app.assets.sprite("enemies", e.id, (160, 160), fallback=(100, 60, 90))
            s.blit(sp, (er.x + 12, er.y + 12))
            pygame.draw.rect(s, (22, 24, 36), (er.x + 180, er.y + 12, 96, 160), border_radius=8)
            s.blit(self.app.font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 12, er.y + 178))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            pygame.draw.rect(s, (45, 45, 45), (er.x + 12, er.y + 214, 260, 16), border_radius=7)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 12, er.y + 214, int(260 * ratio), 16), border_radius=7)
            s.blit(self.app.small_font.render(f"HP {e.hp}/{e.max_hp}", True, UI_THEME["text"]), (er.x + 14, er.y + 236))
            s.blit(self.app.small_font.render(f"Bloque {e.block}", True, UI_THEME["block"]), (er.x + 128, er.y + 236))
            s.blit(self.app.small_font.render(f"Ruptura {e.statuses.get('rupture', 0)}", True, UI_THEME["rupture"]), (er.x + 14, er.y + 260))
            intent_txt, action_name = self._intent_text(e)
            s.blit(self.app.small_font.render(f"Intent: {intent_txt}", True, UI_THEME["gold"]), (er.x + 14, er.y + 286))
            s.blit(self.app.card_text_font.render(f"Acción: {action_name}", True, UI_THEME["muted"]), (er.x + 14, er.y + 306))
            if er.collidepoint(mouse):
                self.tooltip = f"{self.app.loc.t(e.name_key)} | {intent_txt}"

        pygame.draw.rect(s, (16, 18, 32), (0, int(INTERNAL_HEIGHT*0.62), INTERNAL_WIDTH, INTERNAL_HEIGHT-int(INTERNAL_HEIGHT*0.62)))
        start, visible = self._visible_hand()
        hover_idx = None
        for i, _ in enumerate(visible):
            if self._card_rect(i, len(visible), False).inflate(0, 24).collidepoint(mouse):
                hover_idx = i
        for i, c in enumerate(visible):
            rr = self._card_rect(i, len(visible), hover_idx == i)
            if hover_idx is not None and abs(i - hover_idx) == 1:
                rr.x += -10 if i < hover_idx else 10
            dr = self._draw_card(s, rr, c, selected=(start + i == self.selected_card_index), hovered=(hover_idx == i))
            if dr.collidepoint(mouse):
                self.tooltip = self.app.loc.t(c.definition.text_key)

        for f in self.floaters:
            if f["target"] == "player":
                x, y = INTERNAL_WIDTH - 440, 120
            else:
                idx = next((i for i, e in enumerate(self.c.enemies) if e.id == f["target"]), 0)
                er = self._enemy_rect(idx)
                x, y = er.centerx, er.y + 4
            y -= int((0.7 - f["time"]) * 34)
            s.blit(self.app.small_font.render(f["text"], True, f["color"]), (x, y))

        pygame.draw.rect(s, UI_THEME["panel"], self.status_rect, border_radius=10)
        s.blit(self.app.small_font.render("Estados/Registro", True, UI_THEME["text"]), (INTERNAL_WIDTH - 245, INTERNAL_HEIGHT - 356))
        pygame.draw.rect(s, UI_THEME["violet"], self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(self.app.loc.t("button_end_turn"), True, UI_THEME["text"]), (INTERNAL_WIDTH - 208, INTERNAL_HEIGHT - 97))

        if self.tooltip:
            tr = pygame.Rect(min(mouse[0] + 16, INTERNAL_WIDTH - 390), min(mouse[1] + 14, INTERNAL_HEIGHT - 76), 360, 58)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            s.blit(self.app.card_text_font.render(self.tooltip, True, UI_THEME["text"]), (tr.x + 8, tr.y + 18))

        self.app.set_debug(
            hovered_card_id=self.tooltip or "-",
            target_mode=self.c.needs_target is not None,
            combat_end_turn_button_visible=True,
            combat_status_button_visible=True,
            combat_end_turn_rect=str(self.end_turn_rect),
            combat_status_rect=str(self.status_rect),
            enemies_count=len(self.c.enemies),
            enemies_hp=",".join(str(max(0, e.hp)) for e in self.c.enemies),
            enemy_intent=",".join(self._intent_text(e)[0] for e in self.c.enemies),
        )
