import pygame

from game.ui.theme import UI_THEME
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


class MapScreen:
    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0
        self.deck_btn = pygame.Rect(INTERNAL_WIDTH - 260, 76, 220, 56)

    def on_enter(self):
        self.lore_timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
            if event.key == pygame.K_TAB:
                self.app.goto_deck()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.deck_btn.collidepoint(pos):
                self.app.goto_deck()
                return
            self.click_node(pos)

    def click_node(self, pos):
        for col in self.app.run_state.get("map", []):
            for node in col:
                if pygame.Rect(node["x"] - 34, node["y"] - 34, 68, 68).collidepoint(pos) and node.get("state") == "available":
                    self.app.sfx.play("ui_click")
                    self.app.select_map_node(node)
                    return

    def update(self, dt):
        self.lore_timer += dt
        if self.lore_timer > 3:
            self.lore_timer = 0
            self.lore_idx = (self.lore_idx + 1) % 3

    def _draw_icon(self, s, node_type, x, y):
        col = (24, 20, 34)
        if node_type == "combat":
            pygame.draw.line(s, col, (x - 10, y + 10), (x + 8, y - 8), 3)
            pygame.draw.polygon(s, col, [(x + 8, y - 8), (x + 14, y - 2), (x + 2, y + 4)])
        elif node_type == "challenge":
            pts = [(x, y - 12), (x + 8, y - 5), (x + 10, y + 6), (x, y + 12), (x - 10, y + 6), (x - 8, y - 5)]
            pygame.draw.polygon(s, col, pts, 2)
            pygame.draw.circle(s, col, (x - 4, y - 1), 2)
            pygame.draw.circle(s, col, (x + 4, y - 1), 2)
        elif node_type == "event":
            pygame.draw.polygon(s, col, [(x, y - 12), (x + 4, y - 3), (x + 12, y - 2), (x + 6, y + 4), (x + 8, y + 12), (x, y + 7), (x - 8, y + 12), (x - 6, y + 4), (x - 12, y - 2), (x - 4, y - 3)])
        elif node_type == "treasure":
            pygame.draw.rect(s, col, (x - 10, y - 4, 20, 12), 2, border_radius=3)
            pygame.draw.line(s, col, (x - 10, y + 1), (x + 10, y + 1), 2)
        elif node_type == "shop":
            pygame.draw.rect(s, col, (x - 9, y - 2, 18, 12), 2, border_radius=3)
            pygame.draw.arc(s, col, (x - 8, y - 10, 16, 14), 3.14, 6.28, 2)
        else:
            pygame.draw.line(s, col, (x - 10, y), (x + 10, y), 3)
            pygame.draw.line(s, col, (x, y - 10), (x, y + 10), 3)

    def render(self, s):
        s.fill(UI_THEME["bg"])
        run = self.app.run_state

        s.blit(self.app.map_font.render(self.app.loc.t("map_title"), True, UI_THEME["text"]), (34, 24))
        s.blit(self.app.small_font.render(self.app.loc.t(f"lore_short_{self.lore_idx + 1}"), True, UI_THEME["violet"]), (36, 62))
        gold = self.app.map_font.render(f"{self.app.loc.t('gold')}: {run['gold']}", True, UI_THEME["gold"])
        s.blit(gold, (INTERNAL_WIDTH - gold.get_width() - 30, 28))

        pygame.draw.rect(s, UI_THEME["panel"], self.deck_btn, border_radius=10)
        s.blit(self.app.map_font.render(self.app.loc.t("deck_button"), True, UI_THEME["text"]), (INTERNAL_WIDTH - 230, 94))

        for ci, col in enumerate(run["map"]):
            if ci < len(run["map"]) - 1:
                for node in col:
                    for next_id in node.get("next", []):
                        nxt = self.app.node_lookup.get(next_id)
                        if nxt:
                            pygame.draw.line(s, (85, 92, 136), (node["x"], node["y"]), (nxt["x"], nxt["y"]), 5)

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for col in run["map"]:
            for node in col:
                state = node.get("state", "locked")
                color = (92, 92, 98)
                if state == "available":
                    color = UI_THEME["violet"]
                elif state == "completed":
                    color = UI_THEME["good"]
                elif state == "current":
                    color = UI_THEME["card_selected"]
                if node["type"] == "boss":
                    color = UI_THEME["bad"] if state != "locked" else (90, 40, 40)
                if node["type"] == "challenge" and state != "locked":
                    color = (246, 168, 74)
                radius = 30 if node["type"] != "boss" else 36
                if pygame.Rect(node["x"] - 40, node["y"] - 40, 80, 80).collidepoint(mouse) and state == "available":
                    pygame.draw.circle(s, (220, 194, 255), (node["x"], node["y"]), radius + 8)
                pygame.draw.circle(s, color, (node["x"], node["y"]), radius)
                self._draw_icon(s, node["type"], node["x"], node["y"])
                label = "Élite" if node["type"] == "challenge" else self.app.loc.t(f"node_{node['type']}")
                lbl = self.app.small_font.render(label, True, UI_THEME["text"])
                s.blit(lbl, (node["x"] - lbl.get_width() // 2, node["y"] + radius + 8))

        lvl = run["level"]
        need = lvl * 20
        ratio = run["xp"] / max(1, need)
        bar = pygame.Rect(INTERNAL_WIDTH // 2 - 520, INTERNAL_HEIGHT - 84, 1040, 40)
        pygame.draw.rect(s, UI_THEME["panel"], bar, border_radius=12)
        pygame.draw.rect(s, UI_THEME["good"], (bar.x, bar.y, int(bar.w * ratio), bar.h), border_radius=12)
        tx = self.app.map_font.render(f"XP {run['xp']}/{need}   LV {lvl}", True, UI_THEME["text"])
        s.blit(tx, (INTERNAL_WIDTH // 2 - tx.get_width() // 2, INTERNAL_HEIGHT - 78))
