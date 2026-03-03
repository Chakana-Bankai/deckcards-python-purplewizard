import pygame

from game.settings import COLORS


class MapScreen:
    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0

    def on_enter(self):
        self.lore_timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.app.toggle_language()
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            self.click_node(pos)

    def click_node(self, pos):
        run = self.app.run_state
        if run["map_index"] >= len(run["map"]):
            self.app.goto_menu()
            return
        col = run["map"][run["map_index"]]
        for node in col:
            if pygame.Rect(node["x"] - 22, node["y"] - 22, 44, 44).collidepoint(pos) and node["available"]:
                node["available"] = False
                run["map_index"] += 1
                self.app.enter_node(node)
                self.app.sfx.play("ui_click")
                return

    def update(self, dt):
        self.lore_timer += dt
        if self.lore_timer > 3:
            self.lore_timer = 0
            self.lore_idx = (self.lore_idx + 1) % 3

    def render(self, s):
        s.fill(COLORS["bg"])
        run = self.app.run_state
        title = self.app.big_font.render(self.app.loc.t("map_title"), True, COLORS["text"])
        s.blit(title, (40, 28))
        lore = self.app.loc.t("lore_tagline")
        lore2 = self.app.loc.t(f"lore_short_{self.lore_idx + 1}")
        s.blit(self.app.font.render(lore, True, COLORS["muted"]), (40, 74))
        s.blit(self.app.font.render(lore2, True, COLORS["violet"]), (40, 102))
        s.blit(self.app.font.render(f"{self.app.loc.t('gold')}: {run['gold']}", True, COLORS["gold"]), (1080, 28))
        for ci, col in enumerate(run["map"]):
            for n in col:
                color = COLORS["violet"] if n["available"] else COLORS["violet_dark"]
                if n["type"] == "boss":
                    color = COLORS["bad"]
                pygame.draw.circle(s, color, (n["x"], n["y"]), 18)
                key = f"node_{n['type']}"
                lbl = self.app.small_font.render(self.app.loc.t(key), True, COLORS["text"])
                s.blit(lbl, (n["x"] - 35, n["y"] + 26))
                if ci < len(run["map"]) - 1:
                    for nx in run["map"][ci + 1]:
                        if nx["id"] in n["next"]:
                            pygame.draw.line(s, (60, 66, 90), (n["x"], n["y"]), (nx["x"], nx["y"]), 2)
