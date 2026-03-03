import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME

KEYWORDS = {
    "Bloque": "Reduce daño entrante en este turno.",
    "Energía": "Recurso para jugar cartas cada turno.",
    "Ruptura": "Potencia mística que habilita efectos.",
    "Debilidad": "Reduce daño de ataque.",
    "Fragilidad": "Reduce Bloque ganado.",
}


def wrap_text(font, text, width):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= width:
            cur = t
        else:
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
        self.hand_scroll = 0
        self.selected_card_index = None
        self.turn_banner_time = 1.0
        self.floaters = []
        self.tooltip = None
        self.glossary = False
        self.log_visible = True
        self.log_lines = []
        self.banner = TypewriterBanner()
        self._taunt("enemy_taunt_start")
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
        self.end_turn_rect = pygame.Rect(1080, 618, 190, 78)
        self.status_rect = pygame.Rect(1080, 530, 190, 72)

    def _enemy_rect(self, idx):
        return pygame.Rect(60 + idx * 280, 110, 220, 220)

    def _visible_hand(self):
        hand = self.c.hand
        max_cards = 6
        start = max(0, min(self.hand_scroll, max(0, len(hand) - max_cards)))
        return start, hand[start : start + max_cards]

    def _card_rect(self, vis_idx, total):
        card_w, card_h = 132, 188
        gap = 18
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = (1280 - total_w) // 2
        base_y = 528
        x = start_x + vis_idx * (card_w + gap)
        arc = abs((vis_idx - (total - 1) / 2.0))
        y = base_y + int(arc * 5)
        return pygame.Rect(x, y, card_w, card_h)

    def _taunt(self, key):
        text = self.app.loc.t(key)
        if text == key:
            text = self.app.loc.t("lore_short_2")
        self.banner.set(text, 2.3)

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
        if card.definition.rarity == "rare":
            self._taunt("enemy_taunt_big_hit")
        self.c.play_card(idx, target_idx)
        self.app.sfx.play("card_play")

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.hand_scroll -= event.y
            self.app.set_debug(last_ui_event=f"wheel:{event.y}")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.app.set_debug(last_ui_event="key:E_end_turn")
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
            elif event.key == pygame.K_h:
                self.glossary = not self.glossary
                self.app.set_debug(last_ui_event="key:H_glossary")
            elif event.key == pygame.K_ESCAPE:
                self.c.needs_target = None
                self.selected_card_index = None
                self.glossary = False
            elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0]:
                keymap = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0]
                rel = keymap.index(event.key)
                start, _ = self._visible_hand()
                self._play_card(start + rel, None)
            elif event.key == pygame.K_SPACE and self.c.needs_target is not None:
                self._play_card(self.c.needs_target, 0)
                self.c.needs_target = None
                self.selected_card_index = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self.app.set_debug(last_ui_event="click:end_turn")
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
                return
            if self.status_rect.collidepoint(pos):
                self.app.set_debug(last_ui_event="click:status_log")
                self.log_visible = not self.log_visible
                return
            for i, e in enumerate(self.c.enemies):
                er = self._enemy_rect(i)
                if er.collidepoint(pos) and e.alive:
                    if self.c.needs_target is not None:
                        self.app.set_debug(last_ui_event=f"target_enemy:{i}")
                        self._play_card(self.c.needs_target, i)
                        self.c.needs_target = None
                        self.selected_card_index = None
                    return
            start, visible = self._visible_hand()
            for i, _card in enumerate(visible):
                rr = self._card_rect(i, len(visible))
                if rr.collidepoint(pos):
                    self.selected_card_index = start + i
                    self.app.set_debug(last_ui_event=f"card_click:{start+i}")
                    self.app.sfx.play("card_pick")
                    self._play_card(start + i, None)
                    return

    def update(self, dt):
        self.c.update(dt)
        self.banner.update(dt)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            self.turn_timer = max(0, self.turn_timer - dt)
            if self.turn_timer <= 0:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 30)
                self.app.sfx.play("ui_click")

        for ev in self.c.pop_events():
            if ev["type"] == "turn_start":
                self.turn_banner_time = 0.9
                self._taunt("enemy_taunt_intent")
            elif ev["type"] == "damage":
                self.app.sfx.play("hit")
                self.log_lines = [f"DMG {ev['amount']} -> {ev['target']}"] + self.log_lines[:4]
                self.floaters.append({"text": f"-{ev['amount']}", "target": ev["target"], "time": 0.7, "color": UI_THEME["bad"]})
                if ev["amount"] >= 10:
                    self._taunt("enemy_taunt_big_hit")
            elif ev["type"] == "block":
                self.app.sfx.play("shield")
                self.log_lines = [f"BLK +{ev['amount']} -> {ev['target']}"] + self.log_lines[:4]
                self.floaters.append({"text": f"+{ev['amount']}", "target": ev["target"], "time": 0.7, "color": UI_THEME["block"]})
            elif ev["type"] == "exhaust":
                self.app.sfx.play("exhaust")
        self.turn_banner_time = max(0.0, self.turn_banner_time - dt)
        for f in self.floaters:
            f["time"] -= dt
        self.floaters = [f for f in self.floaters if f["time"] > 0]

        if self.c.result == "victory":
            self._taunt("enemy_taunt_death")
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected):
        can_play = card.cost <= self.c.player["energy"]
        grow = 8 if selected else 0
        r = rect.inflate(grow, grow)
        pygame.draw.rect(s, (0, 0, 0), r.move(3, 4), border_radius=10)
        pygame.draw.rect(s, UI_THEME["card_bg"], r, border_radius=10)
        pygame.draw.rect(s, UI_THEME["card_selected"] if selected else UI_THEME["card_border"], r, width=3, border_radius=10)
        art = pygame.Rect(r.x + 6, r.y + 6, r.w - 12, int(r.h * 0.64))
        sprite = self.app.assets.sprite("cards", card.definition.id, art.size, fallback=(84, 66, 122))
        s.blit(sprite, art)
        txt = pygame.Rect(r.x + 6, art.bottom + 4, r.w - 12, r.bottom - art.bottom - 10)
        pygame.draw.rect(s, (245, 245, 250), txt, border_radius=6)
        name = self.app.loc.t(card.definition.name_key)
        s.blit(self.app.tiny_font.render(name, True, UI_THEME["card_text"]), (txt.x + 4, txt.y + 2))
        desc = self.app.loc.t(card.definition.text_key)
        for i, line in enumerate(wrap_text(self.app.tiny_font, desc, txt.w - 8)[:3]):
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["card_text"]), (txt.x + 4, txt.y + 18 + i * 14))
        tags = "/".join(card.definition.tags[:2])
        s.blit(self.app.tiny_font.render(tags, True, (80, 78, 95)), (txt.x + 4, txt.bottom - 14))
        pygame.draw.circle(s, UI_THEME["energy"] if can_play else (90, 90, 90), (r.x + 14, r.y + 14), 11)
        s.blit(self.app.tiny_font.render(str(card.cost), True, UI_THEME["text"]), (r.x + 11, r.y + 8))
        if not can_play:
            ov = pygame.Surface(r.size, pygame.SRCALPHA)
            ov.fill((40, 40, 40, 110))
            s.blit(ov, r.topleft)
        return r

    def render(self, s):
        s.fill((12, 16, 35))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.tooltip = None

        bt = self.banner.visible_text()
        if bt:
            rect = pygame.Rect(290, 18, 700, 44)
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            panel.fill((15, 14, 28, min(210, self.banner.alpha())))
            s.blit(panel, rect.topleft)
            s.blit(self.app.small_font.render(bt, True, UI_THEME["text"]), (rect.x + 12, rect.y + 12))

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, (58, 45, 80) if e.alive else (42, 42, 42), er, border_radius=12)
            sp = self.app.assets.sprite("enemies", e.id, (114, 114), fallback=(100, 60, 90))
            s.blit(sp, (er.x + 53, er.y + 26))
            s.blit(self.app.small_font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 8, er.y + 8))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            pygame.draw.rect(s, (45, 45, 45), (er.x + 10, er.y + 154, 200, 14), border_radius=6)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 10, er.y + 154, int(200 * ratio), 14), border_radius=6)
            intent = e.current_intent()
            iv = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
            num = iv[0] if isinstance(iv, list) else iv
            ik = intent.get("intent", "attack")
            intent_txt = {"attack": f"ATK {num}", "defend": f"DEF {num}", "debuff": f"DEBUFF {intent.get('status','')}({intent.get('stacks',1)})", "buff": f"BUFF {intent.get('status','')}({intent.get('stacks',1)})"}.get(ik, f"ATK {num}")
            ir = pygame.Rect(er.x + 10, er.y + 174, 200, 24)
            pygame.draw.rect(s, (26, 28, 42), ir, border_radius=8)
            s.blit(self.app.tiny_font.render(intent_txt, True, UI_THEME["muted"]), (ir.x + 6, ir.y + 5))
            if ir.collidepoint(mouse):
                self.tooltip = intent_txt

        hud = pygame.Rect(930, 120, 330, 220)
        pygame.draw.rect(s, UI_THEME["panel"], hud, border_radius=12)
        p = self.c.player
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_hp')}: {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (946, 138))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_block')}: {p['block']}", True, UI_THEME["block"]), (946, 166))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_rupture')}: {p['rupture']}", True, UI_THEME["rupture"]), (946, 194))
        s.blit(self.app.font.render(self.app.loc.t("hud_energy"), True, UI_THEME["text"]), (946, 224))
        for i in range(3):
            pygame.draw.circle(s, UI_THEME["energy"] if i < p["energy"] else (65, 68, 90), (1080 + i * 32, 236), 12)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            s.blit(self.app.small_font.render(f"{self.turn_timer:04.1f}s", True, UI_THEME["gold"]), (1130, 222))

        if self.log_visible:
            pygame.draw.rect(s, UI_THEME["panel"], (930, 350, 330, 170), border_radius=12)
            s.blit(self.app.small_font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (946, 360))
            for i, line in enumerate(self.log_lines[:5]):
                s.blit(self.app.tiny_font.render(line, True, UI_THEME["muted"]), (946, 385 + i * 24))

        pygame.draw.rect(s, (15, 18, 30), (0, 500, 1280, 220))
        start, visible = self._visible_hand()
        for i, c in enumerate(visible):
            rr = self._draw_card(s, self._card_rect(i, len(visible)), c, selected=(start + i == self.selected_card_index))
            if rr.collidepoint(mouse):
                self.tooltip = self.app.loc.t(c.definition.text_key)

        for f in self.floaters:
            if f["target"] == "player":
                x, y = 1030, 118
            else:
                idx = next((i for i, e in enumerate(self.c.enemies) if e.id == f["target"]), 0)
                er = self._enemy_rect(idx)
                x, y = er.centerx, er.y + 5
            y -= int((0.7 - f["time"]) * 34)
            s.blit(self.app.small_font.render(f["text"], True, f["color"]), (x, y))

        if self.turn_banner_time > 0:
            t = self.app.big_font.render(self.app.loc.t("combat_turn_banner"), True, UI_THEME["good"])
            s.blit(t, t.get_rect(center=(640, 410)))

        if self.glossary:
            g = pygame.Rect(170, 120, 940, 420)
            pygame.draw.rect(s, (10, 10, 20), g, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t("glossary_title"), True, UI_THEME["text"]), (200, 145))
            yy = 185
            for k, v in KEYWORDS.items():
                s.blit(self.app.small_font.render(k, True, UI_THEME["gold"]), (220, yy))
                s.blit(self.app.small_font.render(v, True, UI_THEME["text"]), (420, yy))
                yy += 40

        if self.tooltip and not self.glossary:
            tr = pygame.Rect(mouse[0] + 16, mouse[1] + 16, 360, 70)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            for li, line in enumerate(wrap_text(self.app.tiny_font, self.tooltip, tr.w - 10)[:3]):
                s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (tr.x + 6, tr.y + 6 + li * 17))

        # Always visible critical combat buttons (draw last)
        pygame.draw.rect(s, UI_THEME["panel"], self.status_rect, border_radius=10)
        s.blit(self.app.small_font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (1132, 557))
        pygame.draw.rect(s, UI_THEME["violet"], self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(self.app.loc.t("button_end_turn"), True, UI_THEME["text"]), (1102, 646))

        self.app.set_debug(
            hand_count=len(self.c.hand),
            hovered_card_id=self.tooltip or "-",
            selected_card_id=(self.c.hand[self.selected_card_index].definition.id if self.selected_card_index is not None and self.selected_card_index < len(self.c.hand) else "-"),
            target_mode=self.c.needs_target is not None,
            combat_end_turn_button_visible=True,
            combat_status_button_visible=True,
            combat_end_turn_rect=str(self.end_turn_rect),
            combat_status_rect=str(self.status_rect),
            enemies_count=len(self.c.enemies),
            enemies_hp=",".join(str(max(0,e.hp)) for e in self.c.enemies),
        )
