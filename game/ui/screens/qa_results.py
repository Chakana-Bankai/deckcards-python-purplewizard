import pygame

from game.ui.theme import UI_THEME


class QAResultsScreen:
    def __init__(self, app, results):
        self.app = app
        self.results = results

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.app.goto_menu()

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("QA RESULTS", True, UI_THEME["text"]), (70, 50))
        y = 130
        for row in self.results[:24]:
            color = UI_THEME["good"] if row.get("status") == "PASS" else UI_THEME["bad"]
            line = f"[{row.get('status')}] {row.get('name')} - {row.get('detail','')}"
            s.blit(self.app.small_font.render(line, True, color), (80, y))
            y += 36
        s.blit(self.app.font.render("ESC / ENTER: volver", True, UI_THEME["muted"]), (80, 1000))
