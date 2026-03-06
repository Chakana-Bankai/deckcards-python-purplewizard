import pygame

from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.ui.components.topbar import MapTopBar
from game.ui.theme import UI_THEME


class MapScreen:
    NODE_NAMES = {
        "event": "Ritual",
        "combat": "Sombra",
        "challenge": "Guía",
        "treasure": "Reliquia",
        "shop": "Tienda",
        "boss": "El Monolito Fracturado",
    }
    NODE_DIFF = {"event": "Eco", "combat": "Peligro II", "challenge": "Prueba", "treasure": "Botín", "shop": "Calma", "boss": "Peligro V"}

    NODE_LORE = {
        "event": "Los ecos del templo piden una decisión del espíritu.",
        "combat": "Sombras antiguas custodian este sendero.",
        "challenge": "Una guía pone a prueba tu equilibrio.",
        "treasure": "Una reliquia olvidada late bajo la piedra.",
        "shop": "Mercaderes errantes ofrecen poder por oro.",
        "boss": "El Monolito Fracturado aguarda tras los sellos.",
    }

    STAGE_TITLES = [
        "Sendero del Kay Pacha",
        "Ecos del Uku Pacha",
        "Pruebas del Hanan Pacha",
        "Umbral de la Trama Viva",
        "Cámara de los Sellos",
        "Portal del Monolito",
    ]

    CHAKANA_THOUGHTS = [
        "Respiro. El primer paso define el pulso del viaje.",
        "El eco del Uku me pide mirar sin miedo.",
        "Hanan prueba mi foco: mente calma, mano precisa.",
        "La Trama viva cambia; yo también debo cambiar.",
        "Siento los sellos vibrar bajo mis pies.",
        "Frente al Monolito, solo queda verdad y voluntad.",
    ]

    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0
        self.deck_btn = pygame.Rect(1688, 108, 188, 40)
        self.topbar = MapTopBar()

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
                if pygame.Rect(node["x"] - 34, node["y"] - 34, 68, 68).collidepoint(pos) and node.get("state") in {"available", "incomplete", "current"}:
                    self.app.sfx.play("ui_click")
                    self.app.select_map_node(node)
                    return

    def update(self, dt):
        self.lore_timer += dt
        if self.lore_timer > 3:
            self.lore_timer = 0
            self.lore_idx = (self.lore_idx + 1) % 3

    def _current_stage_index(self, run: dict) -> int:
        current_id = getattr(self.app, "current_node_id", None)
        if current_id and current_id in self.app.node_lookup:
            return max(0, min(len(self.STAGE_TITLES) - 1, int(self.app.node_lookup[current_id].get("col", 0))))

        stage = 0
        for col in run.get("map", []):
            for node in col:
                if node.get("state") in {"completed", "cleared", "current", "incomplete"}:
                    stage = max(stage, int(node.get("col", 0)))
        return max(0, min(len(self.STAGE_TITLES) - 1, stage))

    def _draw_icon(self, s, node_type, x, y):
        col = (24, 20, 34)
        if node_type == "combat":
            pygame.draw.line(s, col, (x - 10, y + 10), (x + 8, y - 8), 3)
            pygame.draw.polygon(s, col, [(x + 8, y - 8), (x + 14, y - 2), (x + 2, y + 4)])
        elif node_type == "challenge":
            pts = [(x, y - 12), (x + 8, y - 5), (x + 10, y + 6), (x, y + 12), (x - 10, y + 6), (x - 8, y - 5)]
            pygame.draw.polygon(s, col, pts, 2)
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

    def _draw_chakana(self, s, cx, cy, r=42):
        pygame.draw.circle(s, UI_THEME["gold"], (cx, cy), r, 2)
        for dx, dy in [(-r, 0), (r, 0), (0, -r), (0, r)]:
            pygame.draw.line(s, UI_THEME["gold"], (cx, cy), (cx + dx, cy + dy), 2)
        pygame.draw.rect(s, UI_THEME["gold"], pygame.Rect(cx - 10, cy - 10, 20, 20), 2)

    def render(self, s):
        s.fill(UI_THEME["bg"])
        run = self.app.run_state or {"gold": 0, "map": []}
        stage_idx = self._current_stage_index(run)
        stage_title = self.STAGE_TITLES[stage_idx]
        stage_thought = self.CHAKANA_THOUGHTS[stage_idx]

        topbar = pygame.Rect(18, 16, INTERNAL_WIDTH - 36, 92)
        lvl = int(run.get("level", 1) or 1)
        xp = int(run.get("xp", 0) or 0)
        xp_need = max(1, lvl * 20)
        gold = int(run.get("gold", 0) or 0)
        self.topbar.render(s, self.app, topbar, "Trama", stage_title, "Lee la geometría del destino.", f"XP {xp}/{xp_need} · Oro {gold} · Nivel {lvl}")

        chip_y = topbar.bottom + 8
        chip_specs = [
            (f"XP {xp}/{xp_need}", UI_THEME["text"]),
            (f"Oro {gold}", UI_THEME["gold"]),
            (f"Nivel {lvl}", UI_THEME["violet"]),
        ]
        chip_x = 40
        for txt, col in chip_specs:
            chip_w = max(140, self.app.tiny_font.size(txt)[0] + 22)
            chip = pygame.Rect(chip_x, chip_y, chip_w, 30)
            pygame.draw.rect(s, UI_THEME["panel_2"], chip, border_radius=8)
            pygame.draw.rect(s, col, chip, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(txt, True, col), (chip.x + 10, chip.y + 8))
            chip_x += chip_w + 10

        left_rect = pygame.Rect(40, 146, 320, INTERNAL_HEIGHT - 256)
        center_rect = pygame.Rect(370, 146, 1160, INTERNAL_HEIGHT - 256)
        right_rect = pygame.Rect(1540, 146, 340, INTERNAL_HEIGHT - 256)
        for r in (left_rect, center_rect, right_rect):
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=16)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=16)

        pygame.draw.rect(s, UI_THEME["panel_2"], self.deck_btn, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.deck_btn, 2, border_radius=10)
        txt = self.app.map_font.render("Mazo", True, UI_THEME["text"])
        s.blit(txt, txt.get_rect(center=self.deck_btn.center))

        s.blit(self.app.small_font.render("Trama", True, UI_THEME["gold"]), (left_rect.x + 16, left_rect.y + 12))
        s.blit(self.app.tiny_font.render(stage_title, True, UI_THEME["muted"]), (left_rect.x + 16, left_rect.y + 48))
        self._draw_chakana(s, left_rect.centerx, left_rect.y + 170)
        s.blit(self.app.tiny_font.render("Protagonista: Chakana", True, UI_THEME["text"]), (left_rect.x + 62, left_rect.y + 240))
        s.blit(self.app.tiny_font.render(stage_thought[:44], True, UI_THEME["muted"]), (left_rect.x + 16, left_rect.y + 274))

        center_title = self.app.small_font.render(stage_title, True, UI_THEME["gold"])
        s.blit(center_title, (center_rect.x + 18, center_rect.y + 12))

        for ci, col in enumerate(run.get("map", [])):
            if ci < len(run["map"]) - 1:
                for node in col:
                    for next_id in node.get("next", []):
                        nxt = self.app.node_lookup.get(next_id)
                        if nxt:
                            clr = (120, 128, 170) if node.get("state") in {"available", "current", "incomplete"} else (70, 70, 86)
                            pygame.draw.line(s, clr, (node["x"], node["y"]), (nxt["x"], nxt["y"]), 5)

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        hovered_node = None
        for col in run.get("map", []):
            for node in col:
                state = node.get("state", "locked")
                color = (92, 92, 98)
                if state == "available":
                    color = UI_THEME["violet"]
                elif state in {"completed", "cleared"}:
                    color = UI_THEME["good"]
                elif state == "incomplete":
                    color = (210, 128, 86)
                elif state == "current":
                    color = UI_THEME["card_selected"]
                if node["type"] == "boss":
                    color = UI_THEME["bad"] if state != "locked" else (90, 40, 40)
                radius = 30 if node["type"] != "boss" else 36
                node_hover = pygame.Rect(node["x"] - 40, node["y"] - 40, 80, 80).collidepoint(mouse)
                if node_hover:
                    hovered_node = node
                if state == "locked":
                    pygame.draw.circle(s, (40, 40, 56), (node["x"], node["y"]), radius + 4)
                    pygame.draw.circle(s, color, (node["x"], node["y"]), radius)
                    pygame.draw.line(s, UI_THEME["muted"], (node["x"] - 7, node["y"]), (node["x"] + 7, node["y"]), 2)
                else:
                    if node_hover:
                        pygame.draw.circle(s, (220, 194, 255), (node["x"], node["y"]), radius + 8)
                    pygame.draw.circle(s, color, (node["x"], node["y"]), radius)
                    self._draw_icon(s, node["type"], node["x"], node["y"])
                label = self.NODE_NAMES.get(node["type"], "Ruta")
                s.blit(self.app.tiny_font.render(label[:26], True, UI_THEME["text"]), (node["x"] - 40, node["y"] + radius + 4))
                s.blit(self.app.tiny_font.render(self.NODE_DIFF.get(node["type"], "?"), True, UI_THEME["muted"]), (node["x"] - 34, node["y"] + radius + 20))

        harmony = run.get("player", {}).get("harmony_current", 0) if isinstance(run.get("player", {}), dict) else 0
        harmony_goal = run.get("player", {}).get("harmony_ready_threshold", 6) if isinstance(run.get("player", {}), dict) else 6
        stats = [
            f"Oro: {int(run.get('gold', 0) or 0)}",
            f"XP: {xp}/{xp_need}",
            f"Armonía meta: {harmony}/{harmony_goal}",
            f"Mazo: {len(run.get('deck', []) or [])}",
        ]
        s.blit(self.app.small_font.render("Estado de Chakana", True, UI_THEME["gold"]), (right_rect.x + 14, right_rect.y + 12))
        for i, line in enumerate(stats):
            s.blit(self.app.small_font.render(line, True, UI_THEME["text"]), (right_rect.x + 18, right_rect.y + 56 + i * 34))

        if hovered_node:
            lore_text = self.NODE_LORE.get(hovered_node.get("type"), "La ruta susurra un destino incierto.")
            lore_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 520, INTERNAL_HEIGHT - 96, 1040, 56)
            pygame.draw.rect(s, UI_THEME["panel"], lore_rect, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], lore_rect, 2, border_radius=12)
            lore = self.app.small_font.render(lore_text, True, UI_THEME["muted"])
            s.blit(lore, lore.get_rect(center=lore_rect.center))
