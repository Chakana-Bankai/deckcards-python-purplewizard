import pygame

from game.ui.theme import UI_THEME


class RewardScreen:
    def __init__(self, app, picks, gold, xp_gained=0):
        self.app = app
        self.picks = picks
        self.gold = gold
        self.xp_gained = xp_gained
        self.msg = ""

    def on_enter(self):
        pass

    def _metaforma(self, s, rect):
        pygame.draw.rect(s, (66, 48, 88), rect, border_radius=18)
        pygame.draw.rect(s, UI_THEME["gold"], rect, 2, border_radius=18)
        inner = rect.inflate(-20, -20)
        pygame.draw.rect(s, (24, 18, 36), inner, border_radius=14)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, card in enumerate(self.picks):
                r = pygame.Rect(430 + i * 350, 370, 300, 420)
                if r.collidepoint(pos):
                    self.app.run_state["sideboard"].append(card.definition.id)
                    self.app.run_state["gold"] += self.gold
                    self.msg = self.app.loc.t("reward_claimed", gold=self.gold)
                    self.app.goto_map()
                    return

    def update(self, dt):
        pass

    def render(self, s):
        self.app.bg_gen.render_parallax(s, "Pampa Astral", 1111, pygame.time.get_ticks() * 0.02, particles_on=self.app.user_settings.get("fx_particles", True))
        panel = pygame.Rect(120, 120, 1680, 840)
        self._metaforma(s, panel)
        s.blit(self.app.big_font.render(self.app.loc.t("reward_title"), True, UI_THEME["gold"]), (140, 150))
        s.blit(self.app.small_font.render(self.app.loc.t("reward_hint"), True, UI_THEME["text"]), (140, 210))
        s.blit(self.app.small_font.render(f"XP +{self.xp_gained}", True, UI_THEME["good"]), (140, 244))

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, card in enumerate(self.picks):
            r = pygame.Rect(430 + i * 350, 370, 300, 420)
            hover = r.collidepoint(mouse)
            rr = r.inflate(12, 12) if hover else r
            pygame.draw.rect(s, UI_THEME["card_bg"], rr, border_radius=14)
            pygame.draw.rect(s, UI_THEME["gold"], rr, 2, border_radius=14)
            art = self.app.assets.sprite("cards", card.definition.id, (rr.w - 20, 220), fallback=(82, 52, 112))
            s.blit(art, (rr.x + 10, rr.y + 50))
            s.blit(self.app.small_font.render(str(card.definition.name_key), True, UI_THEME["text"]), (rr.x + 14, rr.y + 16))
            s.blit(self.app.tiny_font.render(str(card.definition.text_key), True, UI_THEME["muted"]), (rr.x + 14, rr.y + 292))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (140, 920))
