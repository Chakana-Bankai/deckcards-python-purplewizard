import pygame

from game.combat.intents import INTENT_KEYS
from game.ui.theme import SPACING, UI_THEME


def wrap_text(font, text, width):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class CombatScreen:
    def __init__(self, app, combat_state):
        self.app = app
        self.c = combat_state
        self.overlay = None
        self.rupture_pulse = 0.0
        self.last_rupture = self.c.player["rupture"]
        self.selected_card_index = None
        self.turn_banner_time = 1.0
        self.floaters = []
        self.tooltip = None

    def on_enter(self):
        pass

    def _card_rect(self, idx, hovering=False):
        card_w, card_h = 158, 220
        gap = 16
        total_w = len(self.c.hand) * card_w + max(0, len(self.c.hand) - 1) * gap
        start_x = (1280 - total_w) // 2
        y = 470 - (20 if hovering else 0)
        return pygame.Rect(start_x + idx * (card_w + gap), y, card_w, card_h)

    def _enemy_rect(self, idx):
        base_x = 180 + idx * 300
        return pygame.Rect(base_x, 130, 190, 220)

    def _play_from_index(self, idx, target_idx=0):
        if idx < 0 or idx >= len(self.c.hand):
            return
        card = self.c.hand[idx]
        if card.cost > self.c.player["energy"]:
            return
        if card.definition.target == "enemy":
            self.selected_card_index = idx
            self.c.needs_target = idx
        else:
            self.c.play_card(idx, target_idx)
            self.app.sfx.play("card_play")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.c.end_turn()
            elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0]:
                idx = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0].index(event.key)
                self._play_from_index(idx)
            elif event.key == pygame.K_d:
                self.overlay = "deck"
            elif event.key == pygame.K_r:
                self.overlay = "discard"
            elif event.key == pygame.K_ESCAPE:
                self.overlay = None
                self.selected_card_index = None
                self.c.needs_target = None
            elif event.key == pygame.K_SPACE and self.c.needs_target is not None:
                self.c.play_card(self.c.needs_target, 0)
                self.app.sfx.play("card_play")
                self.c.needs_target = None
                self.selected_card_index = None
            elif event.key == pygame.K_F1:
                self.app.toggle_language()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if pygame.Rect(1080, 600, 180, 90).collidepoint(pos):
                self.c.end_turn()
                self.app.sfx.play("ui_click")
                return
            for i, enemy in enumerate(self.c.enemies):
                er = self._enemy_rect(i)
                if er.collidepoint(pos) and enemy.alive:
                    if self.c.needs_target is not None:
                        self.c.play_card(self.c.needs_target, i)
                        self.app.sfx.play("card_play")
                        self.c.needs_target = None
                        self.selected_card_index = None
                    return
            for i, _card in enumerate(self.c.hand):
                r = self._card_rect(i)
                if r.collidepoint(pos):
                    self.selected_card_index = i
                    self.app.sfx.play("card_pick")
                    self._play_from_index(i)
                    return
            self.selected_card_index = None
            self.c.needs_target = None

    def update(self, dt):
        self.c.update(dt)
        self.turn_banner_time = max(0.0, self.turn_banner_time - dt)
        if self.c.player["rupture"] != self.last_rupture:
            self.rupture_pulse = 0.25
            self.last_rupture = self.c.player["rupture"]
        self.rupture_pulse = max(0, self.rupture_pulse - dt)

        for ev in self.c.pop_events():
            if ev["type"] == "turn_start":
                self.turn_banner_time = 1.0
            elif ev["type"] == "damage":
                self.app.sfx.play("hit")
                self.floaters.append({"text": f"-{ev['amount']}", "target": ev["target"], "time": 0.7, "color": UI_THEME["bad"]})
            elif ev["type"] == "block":
                self.app.sfx.play("shield")
                self.floaters.append({"text": f"+{ev['amount']}", "target": ev["target"], "time": 0.7, "color": UI_THEME["block"]})
            elif ev["type"] == "exhaust":
                self.app.sfx.play("exhaust")

        for f in self.floaters:
            f["time"] -= dt
        self.floaters = [f for f in self.floaters if f["time"] > 0]

        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, idx, card, hovered):
        rect = self._card_rect(idx, hovering=hovered or self.selected_card_index == idx)
        cost_ok = card.cost <= self.c.player["energy"]
        pygame.draw.rect(s, (0, 0, 0), rect.move(4, 6), border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        border = UI_THEME["card_selected"] if self.selected_card_index == idx else UI_THEME["card_border"]
        pygame.draw.rect(s, border, rect, width=3, border_radius=12)

        art_rect = pygame.Rect(rect.x + 8, rect.y + 8, rect.w - 16, int(rect.h * 0.68))
        sprite = self.app.assets.sprite("cards", card.definition.id, art_rect.size, fallback=(84, 66, 122))
        s.blit(sprite, art_rect)

        txt_rect = pygame.Rect(rect.x + 8, art_rect.bottom + 6, rect.w - 16, rect.bottom - art_rect.bottom - 14)
        pygame.draw.rect(s, (245, 245, 250), txt_rect, border_radius=8)
        name = self.app.loc.t(card.definition.name_key)
        if name == card.definition.name_key:
            name = card.definition.id
        s.blit(self.app.small_font.render(name, True, UI_THEME["card_text"]), (txt_rect.x + 4, txt_rect.y + 2))
        desc = self.app.loc.t(card.definition.text_key)
        for li, line in enumerate(wrap_text(self.app.tiny_font, desc, txt_rect.w - 8)[:3]):
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["card_text"]), (txt_rect.x + 4, txt_rect.y + 22 + li * 15))
        tags = ", ".join(card.definition.tags[:2])
        s.blit(self.app.tiny_font.render(tags, True, (80, 78, 95)), (txt_rect.x + 4, txt_rect.bottom - 16))

        cost_color = UI_THEME["energy"] if cost_ok else (110, 110, 110)
        pygame.draw.circle(s, cost_color, (rect.x + rect.w - 16, rect.y + 16), 13)
        s.blit(self.app.small_font.render(str(card.cost), True, UI_THEME["text"]), (rect.x + rect.w - 22, rect.y + 8))
        if not cost_ok:
            gray = pygame.Surface(rect.size, pygame.SRCALPHA)
            gray.fill((60, 60, 60, 120))
            s.blit(gray, rect.topleft)
        return rect

    def render(self, s):
        shake_x = int(self.app.rng.randint(-4, 4) if self.c.screen_shake > 0 else 0)
        s.fill((12, 16, 35))
        self.tooltip = None

        # enemies and intents
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, enemy in enumerate(self.c.enemies):
            er = self._enemy_rect(i).move(shake_x, 0)
            panel_color = (58, 45, 80) if enemy.alive else (45, 45, 45)
            pygame.draw.rect(s, panel_color, er, border_radius=12)
            sprite = self.app.assets.sprite("enemies", enemy.id, (110, 110), fallback=(95, 58, 85))
            s.blit(sprite, (er.x + 40, er.y + 24))
            name = self.app.loc.t(enemy.name_key)
            s.blit(self.app.small_font.render(name, True, UI_THEME["text"]), (er.x + 10, er.y + 6))
            hp_ratio = max(0, enemy.hp) / max(1, enemy.max_hp)
            pygame.draw.rect(s, (45, 45, 45), (er.x + 12, er.y + 150, 166, 14), border_radius=6)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 12, er.y + 150, int(166 * hp_ratio), 14), border_radius=6)
            s.blit(self.app.tiny_font.render(f"{max(0, enemy.hp)}/{enemy.max_hp}", True, UI_THEME["text"]), (er.x + 66, er.y + 148))
            intent = enemy.current_intent()
            val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
            num = val[0] if isinstance(val, list) else val
            ik = self.app.loc.t(INTENT_KEYS.get(intent.get("intent", "attack"), "intent_attack"))
            intent_rect = pygame.Rect(er.x + 12, er.y + 170, 166, 24)
            pygame.draw.rect(s, (28, 30, 48), intent_rect, border_radius=8)
            intent_text = f"{ik} {num}"
            s.blit(self.app.tiny_font.render(intent_text, True, UI_THEME["muted"]), (intent_rect.x + 6, intent_rect.y + 5))
            if intent_rect.collidepoint(mouse):
                self.tooltip = intent_text
            if er.collidepoint(mouse):
                self.tooltip = f"{name} | {intent_text}"

        # player HUD
        p = self.c.player
        hud = pygame.Rect(20 + shake_x, 500, 350, 200)
        pygame.draw.rect(s, UI_THEME["panel"], hud, border_radius=12)
        player_sprite = self.app.assets.sprite("player", "player", (88, 88), fallback=(77, 86, 133))
        s.blit(player_sprite, (hud.x + 10, hud.y + 10))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_hp')}: {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (hud.x + 110, hud.y + 18))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_block')}: {p['block']}", True, UI_THEME["block"]), (hud.x + 110, hud.y + 46))
        rup_color = UI_THEME["rupture"] if self.rupture_pulse > 0 else UI_THEME["text"]
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_rupture')}: {p['rupture']}", True, rup_color), (hud.x + 110, hud.y + 74))
        s.blit(self.app.font.render(self.app.loc.t("hud_energy"), True, UI_THEME["text"]), (hud.x + 12, hud.y + 110))
        for i in range(3):
            filled = i < p["energy"]
            pygame.draw.circle(s, UI_THEME["energy"] if filled else (60, 65, 80), (hud.x + 105 + i * 34, hud.y + 122), 12)

        # end turn button
        end_rect = pygame.Rect(1080, 600, 180, 90)
        pygame.draw.rect(s, UI_THEME["violet"], end_rect, border_radius=12)
        s.blit(self.app.font.render(self.app.loc.t("button_end_turn"), True, UI_THEME["text"]), (1100, 632))

        # cards
        hovered_idx = None
        for i, _ in enumerate(self.c.hand):
            if self._card_rect(i).collidepoint(mouse):
                hovered_idx = i
        for i, card in enumerate(self.c.hand):
            r = self._draw_card(s, i, card, hovered=(hovered_idx == i))
            if r.collidepoint(mouse):
                full = self.app.loc.t(card.definition.text_key)
                self.tooltip = full if full != card.definition.text_key else card.definition.id

        # targeting mode overlay
        if self.c.needs_target is not None:
            overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
            overlay.fill((30, 10, 35, 55))
            s.blit(overlay, (0, 0))
            for i, enemy in enumerate(self.c.enemies):
                er = self._enemy_rect(i)
                if enemy.alive:
                    pygame.draw.rect(s, UI_THEME["card_selected"], er, width=3, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t("button_confirm"), True, UI_THEME["text"]), (590, 20))

        # floaters
        for f in self.floaters:
            if f["target"] == "player":
                x, y = 120, 470
            else:
                idx = next((i for i, e in enumerate(self.c.enemies) if e.id == f["target"]), 0)
                er = self._enemy_rect(idx)
                x, y = er.centerx, er.y + 10
            y -= int((0.7 - f["time"]) * 36)
            s.blit(self.app.small_font.render(f["text"], True, f["color"]), (x, y))

        if self.turn_banner_time > 0:
            txt = self.app.big_font.render(self.app.loc.t("combat_turn_banner"), True, UI_THEME["good"])
            s.blit(txt, txt.get_rect(center=(640, 360)))

        if self.tooltip:
            tr = pygame.Rect(mouse[0] + 16, mouse[1] + 16, 350, 62)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            for li, line in enumerate(wrap_text(self.app.tiny_font, self.tooltip, tr.w - 10)[:3]):
                s.blit(self.app.tiny_font.render(line, True, UI_THEME["text"]), (tr.x + 6, tr.y + 6 + li * 17))
