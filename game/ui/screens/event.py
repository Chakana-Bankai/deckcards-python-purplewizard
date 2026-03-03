import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME


class EventScreen:
    def __init__(self, app, event):
        self.app = app
        self.event = event
        self.writer = TypewriterBanner()
        self.lines = [self.app.loc.t(event.get("body_key", "lore_tagline")), "...", "El guía espera tu elección."]
        self.idx = 0
        self.timer = 0
        self.msg = ""

    def on_enter(self):
        self.writer.set(self.lines[0], 3.0)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.app.toggle_language()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.app.sfx.play("ui_click")
            for i, ch in enumerate(self.event["choices"]):
                if pygame.Rect(340, 430 + i * 94, 1240, 76).collidepoint(pos):
                    self.app.apply_event_effects(ch["effects"])
                    self.msg = f"El guía te entregó: {self.app.loc.t(ch['text_key'])}"
                    self.app._complete_current_node()
                    self.app.goto_map()

    def update(self, dt):
        self.timer += dt
        if self.timer > 2.6:
            self.timer = 0
            self.idx = (self.idx + 1) % len(self.lines)
            self.writer.set(self.lines[self.idx], 2.4)

    def render(self, s):
        s.fill(UI_THEME["bg"])
        title = self.app.loc.t(self.event["title_key"])
        s.blit(self.app.big_font.render(title, True, UI_THEME["gold"]), (140, 70))

        panel = pygame.Rect(130, 150, 1660, 620)
        pygame.draw.rect(s, UI_THEME["panel"], panel, border_radius=16)

        avatar_frame = pygame.Rect(180, 220, 260, 320)
        pygame.draw.rect(s, (58, 40, 82), avatar_frame, border_radius=14)
        pygame.draw.rect(s, UI_THEME["gold"], avatar_frame, 2, border_radius=14)
        hover = int(2 * pygame.math.Vector2(1, 0).rotate(pygame.time.get_ticks() * 0.2).x)
        avatar = pygame.Surface((220, 280))
        avatar.fill((34, 24, 52))
        pygame.draw.circle(avatar, (188, 150, 230), (110, 100), 50)
        pygame.draw.rect(avatar, (110, 80, 160), (65, 150, 90, 100), border_radius=18)
        pygame.draw.circle(avatar, (255, 240, 210), (94, 95), 5)
        pygame.draw.circle(avatar, (255, 240, 210), (126, 95), 5)
        s.blit(avatar, (200, 240 + hover))
        glow = pygame.Surface((280, 340), pygame.SRCALPHA)
        pygame.draw.rect(glow, (170, 130, 230, 60), glow.get_rect(), border_radius=18)
        s.blit(glow, (170, 210))

        dialogue_box = pygame.Rect(500, 220, 1200, 170)
        pygame.draw.rect(s, (30, 18, 44), dialogue_box, border_radius=12)
        s.blit(self.app.small_font.render("Guía espiritual", True, UI_THEME["muted"]), (530, 246))
        s.blit(self.app.font.render(self.writer.current, True, UI_THEME["text"]), (530, 290))

        for i, ch in enumerate(self.event["choices"][:3]):
            r = pygame.Rect(340, 430 + i * 94, 1240, 76)
            mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
            col = UI_THEME["panel_2"] if r.collidepoint(mouse) else UI_THEME["panel"]
            pygame.draw.rect(s, col, r, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t(ch["text_key"]), True, UI_THEME["text"]), (370, r.y + 24))

        if self.msg:
            s.blit(self.app.small_font.render(self.msg, True, UI_THEME["good"]), (540, 720))
