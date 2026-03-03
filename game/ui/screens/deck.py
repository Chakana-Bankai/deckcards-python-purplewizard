import pygame

from game.ui.theme import UI_THEME


class DeckScreen:
    def __init__(self, app):
        self.app = app
        self.back = pygame.Rect(20, 20, 160, 46)

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                self.app.goto_map()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back.collidepoint(pos):
                self.app.goto_map()
                return
            # active list click remove to side (if >10)
            for i, cid in enumerate(self.app.run_state["deck"]):
                r = pygame.Rect(40, 110 + i * 26, 420, 24)
                if r.collidepoint(pos) and len(self.app.run_state["deck"]) > 10:
                    self.app.run_state["deck"].pop(i)
                    self.app.run_state["sideboard"].append(cid)
                    return
            for i, cid in enumerate(self.app.run_state["sideboard"]):
                r = pygame.Rect(500, 110 + i * 26, 420, 24)
                if r.collidepoint(pos) and len(self.app.run_state["deck"]) < 20:
                    self.app.run_state["sideboard"].pop(i)
                    self.app.run_state["deck"].append(cid)
                    return

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        pygame.draw.rect(s, UI_THEME["panel"], self.back, border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (60, 30))
        s.blit(self.app.big_font.render(self.app.loc.t("deck_title_active"), True, UI_THEME["text"]), (40, 70))
        s.blit(self.app.big_font.render(self.app.loc.t("deck_title_side"), True, UI_THEME["text"]), (500, 70))
        attacks = skills = rituals = total_cost = 0
        for i, cid in enumerate(self.app.run_state["deck"]):
            cd = self.app.card_defs.get(cid, self.app.card_defs.get("strike"))
            total_cost += cd.get("cost", 1)
            tags = cd.get("tags", [])
            if "attack" in tags:
                attacks += 1
            if "skill" in tags:
                skills += 1
            if "ritual" in tags:
                rituals += 1
            pygame.draw.rect(s, (34, 36, 56), (40, 110 + i * 26, 420, 24), border_radius=4)
            s.blit(self.app.tiny_font.render(self.app.loc.t(cd.get("name_key", cid)), True, UI_THEME["text"]), (46, 114 + i * 26))
        for i, cid in enumerate(self.app.run_state["sideboard"]):
            cd = self.app.card_defs.get(cid, self.app.card_defs.get("strike"))
            pygame.draw.rect(s, (34, 36, 56), (500, 110 + i * 26, 420, 24), border_radius=4)
            s.blit(self.app.tiny_font.render(self.app.loc.t(cd.get("name_key", cid)), True, UI_THEME["text"]), (506, 114 + i * 26))
        n = max(1, len(self.app.run_state["deck"]))
        avg = total_cost / n
        s.blit(self.app.font.render(self.app.loc.t("deck_stats", count=n, avg=f"{avg:.1f}"), True, UI_THEME["gold"]), (40, 640))
        s.blit(self.app.font.render(self.app.loc.t("deck_stats_tags", atk=attacks, skill=skills, ritual=rituals), True, UI_THEME["muted"]), (40, 670))
