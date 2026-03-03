import pygame

from game.combat.intents import INTENT_KEYS
from game.settings import COLORS


class CombatScreen:
    def __init__(self, app, combat_state):
        self.app = app
        self.c = combat_state
        self.overlay = None
        self.rupture_pulse = 0.0
        self.last_rupture = self.c.player["rupture"]

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.c.end_turn()
            elif event.key in [pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5,pygame.K_6,pygame.K_7,pygame.K_8,pygame.K_9,pygame.K_0]:
                keymap=[pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5,pygame.K_6,pygame.K_7,pygame.K_8,pygame.K_9,pygame.K_0]
                idx = keymap.index(event.key)
                self.c.play_card(idx, 0)
            elif event.key == pygame.K_d:
                self.overlay = "deck"
            elif event.key == pygame.K_r:
                self.overlay = "discard"
            elif event.key == pygame.K_ESCAPE:
                self.overlay = None
                self.c.needs_target = None
            elif event.key == pygame.K_SPACE and self.c.needs_target is not None:
                self.c.play_card(self.c.needs_target, 0)
                self.c.needs_target = None
            elif event.key == pygame.K_F1:
                self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if pygame.Rect(1120, 620, 130, 60).collidepoint(pos):
                self.c.end_turn()
                return
            for i, e in enumerate(self.c.enemies):
                r = pygame.Rect(170 + i * 300, 180, 150, 160)
                if r.collidepoint(pos) and self.c.needs_target is not None:
                    self.c.play_card(self.c.needs_target, i)
                    self.c.needs_target = None
                    return
            for i, _card in enumerate(self.c.hand):
                r = pygame.Rect(60 + i * 118, 500, 110, 160)
                if r.collidepoint(pos):
                    self.c.play_card(i, 0)
                    self.app.sfx.play("card_play")
                    return

    def update(self, dt):
        self.c.update(dt)
        if self.c.player["rupture"] != self.last_rupture:
            self.rupture_pulse = 0.25
            self.last_rupture = self.c.player["rupture"]
        self.rupture_pulse = max(0, self.rupture_pulse - dt)
        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def render(self, s):
        shake_x = int(self.app.rng.randint(-4, 4) if self.c.screen_shake > 0 else 0)
        s.fill((10, 14, 34))
        hud = pygame.Rect(20 + shake_x, 20, 420, 108)
        pygame.draw.rect(s, COLORS["panel"], hud, border_radius=8)
        p = self.c.player
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_hp')}: {p['hp']}/{p['max_hp']}", True, COLORS['text']), (34 + shake_x, 34))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_block')}: {p['block']}", True, COLORS['text']), (34 + shake_x, 58))
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_energy')}: {p['energy']}", True, COLORS['text']), (34 + shake_x, 82))
        rup_color = COLORS["violet"] if self.rupture_pulse > 0 else COLORS["text"]
        s.blit(self.app.font.render(f"{self.app.loc.t('hud_rupture')}: {p['rupture']}", True, rup_color), (230 + shake_x, 82))
        for i, e in enumerate(self.c.enemies):
            r = pygame.Rect(170 + i * 300 + shake_x, 180, 150, 160)
            pygame.draw.rect(s, COLORS["bad"] if e.id == "inverse_weaver" else COLORS["panel"], r, border_radius=8)
            s.blit(self.app.small_font.render(self.app.loc.t(e.name_key), True, COLORS["text"]), (r.x + 10, r.y + 12))
            s.blit(self.app.small_font.render(f"{self.app.loc.t('hud_hp')} {max(0, e.hp)}/{e.max_hp}", True, COLORS["text"]), (r.x + 10, r.y + 34))
            intent = e.current_intent()
            iv = intent.get("value", [intent.get('stacks', 1), intent.get('stacks', 1)])
            num = iv[0] if isinstance(iv, list) else iv
            ik = INTENT_KEYS[intent["intent"]]
            s.blit(self.app.small_font.render(f"{self.app.loc.t(ik)} {num}", True, COLORS["muted"]), (r.x + 10, r.y + 56))
        pygame.draw.rect(s, COLORS["violet_dark"], (1120, 620, 130, 60), border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("button_end_turn"), True, COLORS["text"]), (1132, 640))
        for i, card in enumerate(self.c.hand):
            r = pygame.Rect(60 + i * 118, 500, 110, 160)
            pygame.draw.rect(s, COLORS["panel"], r, border_radius=8)
            s.blit(self.app.small_font.render(self.app.loc.t(card.definition.name_key), True, COLORS["text"]), (r.x + 6, r.y + 8))
            s.blit(self.app.small_font.render(str(card.cost), True, COLORS["gold"]), (r.x + 90, r.y + 8))
            s.blit(self.app.small_font.render(self.app.loc.t(card.definition.text_key)[:46], True, COLORS["muted"]), (r.x + 6, r.y + 130))
        if self.c.start_line_time > 0:
            t = self.app.font.render(self.app.loc.t(self.c.start_line), True, COLORS["violet"])
            s.blit(t, t.get_rect(center=(640, 420)))
        if self.overlay:
            pygame.draw.rect(s, (0, 0, 0, 140), (140, 90, 1000, 520))
            key = {"deck": "overlay_deck", "discard": "overlay_discard"}.get(self.overlay, "overlay_exhaust")
            s.blit(self.app.big_font.render(self.app.loc.t(key), True, COLORS["text"]), (470, 120))
