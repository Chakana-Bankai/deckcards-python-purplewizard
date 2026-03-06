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
        "shop": "Umbral",
        "boss": "El Monolito Fracturado",
    }
    NODE_DIFF = {"event": "Eco", "combat": "Peligro II", "challenge": "Prueba", "treasure": "Botín", "shop": "Calma", "boss": "Peligro V"}

    NODE_LORE = {
        "event": "Los ecos del templo piden una decisión del espíritu.",
        "combat": "Sombras antiguas custodian este sendero.",
        "challenge": "Una guía pone a prueba tu equilibrio.",
        "treasure": "Una reliquia olvidada late bajo la piedra.",
        "shop": "El Comerciante del Umbral ofrece poder por oro.",
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


    MAP_HINTS = [
        "Sigue la ruta iluminada para avanzar al siguiente pacha.",
        "Explora nodos de guia para control y equilibrio de recursos.",
        "Si tu armonia esta lista, prioriza nodos de riesgo medio.",
        "Las reliquias cambian el ritmo: planea 2 nodos por delante.",
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
            pool = max(1, len(self.MAP_HINTS))
            self.lore_idx = (self.lore_idx + 1) % pool

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

    def _fit_text(self, font, text: str, width: int) -> str:
        out = str(text or "").replace("\n", " ").strip()
        if not out:
            return ""
        while font.size(out)[0] > width and len(out) > 4:
            out = out[:-4] + "..."
        return out

    def render(self, s):
        s.fill(UI_THEME["bg"])
        run = self.app.run_state or {"gold": 0, "map": []}
        stage_idx = self._current_stage_index(run)
        stage_title = self.STAGE_TITLES[stage_idx]
        stage_thought = self.CHAKANA_THOUGHTS[stage_idx]

        lvl = int(run.get("level", 1) or 1)
        xp = int(run.get("xp", 0) or 0)
        xp_need = max(1, lvl * 20)
        gold = int(run.get("gold", 0) or 0)

        topbar = pygame.Rect(18, 16, INTERNAL_WIDTH - 36, 98)
        chapter = f"Pacha {stage_idx + 1}"
        subtitle = "Ruta viva de la Trama"
        self.topbar.render(s, self.app, topbar, chapter, stage_title, subtitle, "")

        self.deck_btn = pygame.Rect(topbar.right - 174, topbar.y + 50, 156, 36)

        chip_specs = [
            (f"XP {xp}/{xp_need}", UI_THEME["text"]),
            (f"Oro {gold}", UI_THEME["gold"]),
            (f"Nivel {lvl}", UI_THEME["violet"]),
        ]
        gap = 8
        chip_h = 24
        chip_ws = [max(104, self.app.tiny_font.size(txt)[0] + 18) for txt, _ in chip_specs]
        total_w = sum(chip_ws) + gap * (len(chip_ws) - 1)
        chip_x = self.deck_btn.x - 14 - total_w
        chip_y = topbar.y + 56
        for (txt, col), cw in zip(chip_specs, chip_ws):
            chip = pygame.Rect(chip_x, chip_y, cw, chip_h)
            pygame.draw.rect(s, UI_THEME["panel_2"], chip, border_radius=8)
            pygame.draw.rect(s, col, chip, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(txt, True, col), (chip.x + 9, chip.y + 5))
            chip_x += cw + gap

        pygame.draw.rect(s, UI_THEME["panel_2"], self.deck_btn, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.deck_btn, 2, border_radius=10)
        txt = self.app.map_font.render("Mazo", True, UI_THEME["text"])
        s.blit(txt, txt.get_rect(center=self.deck_btn.center))

        left_rect = pygame.Rect(30, 130, 316, INTERNAL_HEIGHT - 222)
        right_rect = pygame.Rect(INTERNAL_WIDTH - 346, 130, 316, INTERNAL_HEIGHT - 222)
        center_rect = pygame.Rect(left_rect.right + 16, 130, right_rect.x - (left_rect.right + 32), INTERNAL_HEIGHT - 222)

        for r in (left_rect, center_rect, right_rect):
            pygame.draw.rect(s, UI_THEME["panel"], r, border_radius=16)
            pygame.draw.rect(s, UI_THEME["accent_violet"], r, 2, border_radius=16)

        s.blit(self.app.small_font.render("Trama", True, UI_THEME["gold"]), (left_rect.x + 16, left_rect.y + 14))
        stage_line = self._fit_text(self.app.tiny_font, stage_title, left_rect.w - 32)
        s.blit(self.app.tiny_font.render(stage_line, True, UI_THEME["muted"]), (left_rect.x + 16, left_rect.y + 40))
        self._draw_chakana(s, left_rect.centerx, left_rect.y + 132)
        thought_title = self.app.tiny_font.render("Pensamiento de Chakana", True, UI_THEME["text"])
        s.blit(thought_title, (left_rect.x + 16, left_rect.y + 198))
        thought_line = self._fit_text(self.app.small_font, stage_thought, left_rect.w - 32)
        s.blit(self.app.small_font.render(thought_line, True, UI_THEME["muted"]), (left_rect.x + 16, left_rect.y + 222))
        hint_box = pygame.Rect(left_rect.x + 14, left_rect.bottom - 86, left_rect.w - 28, 70)
        pygame.draw.rect(s, UI_THEME["panel_2"], hint_box, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], hint_box, 1, border_radius=10)
        hint_title = self.app.tiny_font.render("Senal de Trama", True, UI_THEME["gold"])
        hint_text = self._fit_text(self.app.tiny_font, self.MAP_HINTS[self.lore_idx % max(1, len(self.MAP_HINTS))], hint_box.w - 16)
        s.blit(hint_title, (hint_box.x + 8, hint_box.y + 8))
        s.blit(self.app.tiny_font.render(hint_text, True, UI_THEME["muted"]), (hint_box.x + 8, hint_box.y + 32))

        center_badge = pygame.Rect(center_rect.x + 14, center_rect.y + 12, 164, 24)
        pygame.draw.rect(s, UI_THEME["panel_2"], center_badge, border_radius=7)
        pygame.draw.rect(s, UI_THEME["gold"], center_badge, 1, border_radius=7)
        s.blit(self.app.tiny_font.render(f"Etapa {stage_idx + 1}", True, UI_THEME["gold"]), (center_badge.x + 8, center_badge.y + 5))

        # Stage progression rail for fast readability of current route.
        rail = pygame.Rect(center_badge.right + 18, center_badge.y + 2, center_rect.w - (center_badge.right - center_rect.x) - 34, 18)
        pygame.draw.rect(s, UI_THEME["panel_2"], rail, border_radius=8)
        steps = max(2, len(self.STAGE_TITLES))
        for i in range(steps):
            x = rail.x + int((i / (steps - 1)) * rail.w)
            is_done = i < stage_idx
            is_now = i == stage_idx
            col = UI_THEME["muted"]
            rr = 4
            if is_done:
                col = UI_THEME["good"]
                rr = 5
            if is_now:
                col = UI_THEME["gold"]
                rr = 7
                glow = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(glow, (240, 210, 138, 90), (10, 10), 10)
                s.blit(glow, (x - 10, rail.centery - 10))
            pygame.draw.circle(s, col, (x, rail.centery), rr)
            if i < steps - 1:
                nx = rail.x + int(((i + 1) / (steps - 1)) * rail.w)
                line_col = (90, 98, 132)
                if i < stage_idx:
                    line_col = (132, 182, 144)
                pygame.draw.line(s, line_col, (x + rr, rail.centery), (nx - rr, rail.centery), 2)

        for ci, col in enumerate(run.get("map", [])):
            if ci < len(run.get("map", [])) - 1:
                for node in col:
                    for next_id in node.get("next", []):
                        nxt = self.app.node_lookup.get(next_id)
                        if nxt:
                            active = node.get("state") in {"available", "current", "incomplete"}
                            clr = (122, 132, 182) if active else (68, 70, 88)
                            width = 4
                            if active:
                                width = 5
                                glow = pygame.Surface((abs(nxt["x"] - node["x"]) + 18, abs(nxt["y"] - node["y"]) + 18), pygame.SRCALPHA)
                                pygame.draw.line(glow, (154, 142, 214, 68), (9, 9), (glow.get_width() - 9, glow.get_height() - 9), 6)
                                s.blit(glow, (min(node["x"], nxt["x"]) - 9, min(node["y"], nxt["y"]) - 9))
                            pygame.draw.line(s, clr, (node["x"], node["y"]), (nxt["x"], nxt["y"]), width)

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

                radius = 28 if node["type"] != "boss" else 34
                node_hover = pygame.Rect(node["x"] - 40, node["y"] - 40, 80, 80).collidepoint(mouse)
                if node_hover:
                    hovered_node = node

                if state == "locked":
                    pygame.draw.circle(s, (40, 40, 56), (node["x"], node["y"]), radius + 4)
                    pygame.draw.circle(s, color, (node["x"], node["y"]), radius)
                    pygame.draw.line(s, UI_THEME["muted"], (node["x"] - 7, node["y"]), (node["x"] + 7, node["y"]), 2)
                else:
                    if node_hover:
                        pygame.draw.circle(s, (220, 194, 255), (node["x"], node["y"]), radius + 9)
                    elif state == "current":
                        pygame.draw.circle(s, (200, 180, 245), (node["x"], node["y"]), radius + 6)
                    pygame.draw.circle(s, color, (node["x"], node["y"]), radius)
                    self._draw_icon(s, node["type"], node["x"], node["y"])

                show_label = node_hover or state == "current" or node["type"] == "boss"
                if show_label:
                    label = self.NODE_NAMES.get(node["type"], "Ruta")
                    label_txt = self._fit_text(self.app.tiny_font, label, 120)
                    s.blit(self.app.tiny_font.render(label_txt, True, UI_THEME["text"]), (node["x"] - 44, node["y"] + radius + 5))

        harmony = run.get("player", {}).get("harmony_current", 0) if isinstance(run.get("player", {}), dict) else 0
        harmony_goal = run.get("player", {}).get("harmony_ready_threshold", 6) if isinstance(run.get("player", {}), dict) else 6
        deck_size = len(run.get("deck", []) or [])
        completed_nodes = 0
        available_nodes = 0
        for col in run.get("map", []):
            for node in col:
                st = node.get("state", "locked")
                if st in {"completed", "cleared"}:
                    completed_nodes += 1
                elif st in {"available", "current", "incomplete"}:
                    available_nodes += 1

        stats = [
            ("Oro", f"{gold}", UI_THEME["gold"]),
            ("XP", f"{xp}/{xp_need}", UI_THEME["text"]),
            ("Armonia", f"{harmony}/{harmony_goal}", UI_THEME["violet"]),
            ("Mazo", f"{deck_size}", UI_THEME["text"]),
        ]

        s.blit(self.app.small_font.render("Estado de Chakana", True, UI_THEME["gold"]), (right_rect.x + 14, right_rect.y + 14))
        y = right_rect.y + 52
        for label, val, col in stats:
            row = pygame.Rect(right_rect.x + 12, y, right_rect.w - 24, 34)
            pygame.draw.rect(s, UI_THEME["panel_2"], row, border_radius=8)
            pygame.draw.rect(s, col, row, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(label, True, UI_THEME["muted"]), (row.x + 10, row.y + 5))
            value_txt = self.app.small_font.render(val, True, col)
            s.blit(value_txt, (row.right - value_txt.get_width() - 10, row.y + 8))
            y += 42

        lore_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 520, INTERNAL_HEIGHT - 90, 1040, 52)
        pygame.draw.rect(s, UI_THEME["panel"], lore_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], lore_rect, 2, border_radius=12)
        if hovered_node:
            lore_text = self.NODE_LORE.get(hovered_node.get("type"), "La ruta susurra un destino incierto.")
            node_title = self.NODE_NAMES.get(hovered_node.get("type"), "Ruta")
            title_txt = self.app.tiny_font.render(node_title, True, UI_THEME["gold"])
            lore_line = self._fit_text(self.app.small_font, lore_text, lore_rect.w - title_txt.get_width() - 28)
            lore_txt = self.app.small_font.render(lore_line, True, UI_THEME["muted"])
            s.blit(title_txt, (lore_rect.x + 12, lore_rect.y + 16))
            s.blit(lore_txt, (lore_rect.x + 22 + title_txt.get_width(), lore_rect.y + 14))
        else:
            title_txt = self.app.tiny_font.render("Ruta", True, UI_THEME["gold"])
            flavor = self._fit_text(self.app.small_font, self.MAP_HINTS[self.lore_idx % max(1, len(self.MAP_HINTS))], lore_rect.w - title_txt.get_width() - 28)
            lore_txt = self.app.small_font.render(flavor, True, UI_THEME["muted"])
            s.blit(title_txt, (lore_rect.x + 12, lore_rect.y + 16))
            s.blit(lore_txt, (lore_rect.x + 22 + title_txt.get_width(), lore_rect.y + 14))
