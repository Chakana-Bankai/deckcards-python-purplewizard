import pygame

from game.ui.theme import UI_THEME


class MapScreen:
    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0
        self.deck_btn = pygame.Rect(1110, 74, 150, 44)

    def on_enter(self):
        self.lore_timer = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.app.toggle_language()
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
            if event.key == pygame.K_TAB:
                self.app.set_debug(last_ui_event="map:deck_open")
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
                if pygame.Rect(node["x"] - 24, node["y"] - 24, 48, 48).collidepoint(pos) and node.get("state") == "available":
                    self.app.sfx.play("ui_click")
                    self.app.set_debug(last_ui_event=f"map:select_{node['id']}")
                    self.app.select_map_node(node)
                    return

    def update(self, dt):
        self.lore_timer += dt
        if self.lore_timer > 3:
            self.lore_timer = 0
            self.lore_idx = (self.lore_idx + 1) % 3

    def render(self, s):
        s.fill(UI_THEME["bg"])
        run = self.app.run_state
        s.blit(self.app.big_font.render(self.app.loc.t("map_title"), True, UI_THEME["text"]), (40, 24))
        s.blit(self.app.font.render(self.app.loc.t("lore_tagline"), True, UI_THEME["muted"]), (40, 74))
        s.blit(self.app.font.render(self.app.loc.t(f"lore_short_{self.lore_idx + 1}"), True, UI_THEME["violet"]), (40, 102))
        s.blit(self.app.tiny_font.render("Tip: mejora tu mazo en tienda y busca sinergias para el boss", True, UI_THEME["muted"]), (40, 158))
        s.blit(self.app.font.render(f"{self.app.loc.t('gold')}: {run['gold']}", True, UI_THEME["gold"]), (940, 30))

        # xp bar
        lvl = run["level"]
        need = lvl * 20
        ratio = run["xp"] / max(1, need)
        pygame.draw.rect(s, UI_THEME["panel"], (40, 132, 300, 18), border_radius=8)
        pygame.draw.rect(s, UI_THEME["good"], (40, 132, int(300 * ratio), 18), border_radius=8)
        s.blit(self.app.tiny_font.render(f"XP {run['xp']}/{need}  Lv {lvl}", True, UI_THEME["text"]), (350, 132))

        pygame.draw.rect(s, UI_THEME["panel"], self.deck_btn, border_radius=8)
        s.blit(self.app.small_font.render(self.app.loc.t("deck_button"), True, UI_THEME["text"]), (1120, 86))

        for ci, col in enumerate(run["map"]):
            if ci < len(run["map"]) - 1:
                for node in col:
                    for next_id in node.get("next", []):
                        nxt = self.app.node_lookup.get(next_id)
                        if nxt:
                            pygame.draw.line(s, (75, 80, 120), (node["x"], node["y"]), (nxt["x"], nxt["y"]), 2)

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for col in run["map"]:
            for node in col:
                state = node.get("state", "locked")
                color = (90, 90, 95)
                if state == "available":
                    color = UI_THEME["violet"]
                elif state == "completed":
                    color = UI_THEME["good"]
                elif state == "current":
                    color = UI_THEME["card_selected"]
                if node["type"] == "boss":
                    color = UI_THEME["bad"] if state != "locked" else (80, 40, 45)
                r = pygame.Rect(node["x"] - 18, node["y"] - 18, 36, 36)
                if r.collidepoint(mouse) and state == "available":
                    pygame.draw.circle(s, (220, 195, 255), (node["x"], node["y"]), 22)
                pygame.draw.circle(s, color, (node["x"], node["y"]), 18)
                pygame.draw.line(s, (160, 120, 220), (node["x"] - 8, node["y"]), (node["x"] + 8, node["y"]), 2)
                pygame.draw.line(s, (160, 120, 220), (node["x"], node["y"] - 8), (node["x"], node["y"] + 8), 2)
                lbl = self.app.small_font.render(self.app.loc.t(f"node_{node['type']}"), True, UI_THEME["text"])
                s.blit(lbl, (node["x"] - lbl.get_width() // 2, node["y"] + 24))
