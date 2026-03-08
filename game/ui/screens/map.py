import pygame

from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.ui.components.topbar import MapTopBar
from game.ui.theme import UI_THEME
from game.ui.system.components import UIPanel
from game.ui.system.colors import UColors
from game.ui.system.layout import safe_area


class MapScreen:
    NODE_NAMES = {
        "event": "Ritual",
        "combat": "Sombra",
        "challenge": "Guia",
        "treasure": "Reliquia",
        "shop": "Umbral",
        "boss": "El Monolito Fracturado",
    }
    NODE_DIFF = {"event": "Eco", "combat": "Peligro II", "challenge": "Prueba", "treasure": "Botin", "shop": "Calma", "boss": "Peligro V"}

    NODE_LORE = {
        "event": "Los ecos del templo piden una decision del espiritu.",
        "combat": "Sombras antiguas custodian este sendero.",
        "challenge": "Una guia pone a prueba tu equilibrio.",
        "treasure": "Una reliquia olvidada late bajo la piedra.",
        "shop": "El Comerciante del Umbral ofrece poder por oro.",
        "boss": "El Monolito Fracturado aguarda tras los sellos.",
    }

    STAGE_TITLES = [
        "Sendero del Kay Pacha",
        "Ecos del Uku Pacha",
        "Pruebas del Hanan Pacha",
        "Umbral de la Trama Viva",
        "Camara de los Sellos",
        "Portal del Monolito",
    ]

    CHAKANA_THOUGHTS = [
        "Respiro. El primer paso define el pulso del viaje.",
        "El eco del Uku me pide mirar sin miedo.",
        "Hanan prueba mi foco: mente calma, mano precisa.",
        "La Trama viva cambia; yo tambien debo cambiar.",
        "Siento los sellos vibrar bajo mis pies.",
        "Frente al Monolito, solo queda verdad y voluntad.",
    ]

    MAP_HINTS = [
        "Sigue la ruta iluminada para avanzar al siguiente pacha.",
        "Explora nodos de guia para control y equilibrio de recursos.",
        "Si tu armonia esta lista, prioriza nodos de riesgo medio.",
        "Las reliquias cambian el ritmo: planea 2 nodos por delante.",
    ]

    BIOME_BG_NAME = {
        "kaypacha": "Templo Obsidiana",
        "forest": "Pampa Astral",
        "umbral": "Caverna Umbral",
        "hanan": "Ruinas Chakana",
    }

    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0
        self.deck_btn = pygame.Rect(1688, 108, 188, 40)
        self.topbar = MapTopBar()
        self.selected_biome = "kaypacha"
        self.bg_seed = abs(hash("map:kaypacha")) % 100000
        self.node_positions = {}

    def on_enter(self):
        self.lore_timer = 0

    def _panel_rects(self):
        left_rect = pygame.Rect(30, 130, 316, INTERNAL_HEIGHT - 222)
        right_rect = pygame.Rect(INTERNAL_WIDTH - 346, 130, 316, INTERNAL_HEIGHT - 222)
        center_rect = pygame.Rect(left_rect.right + 16, 130, right_rect.x - (left_rect.right + 32), INTERNAL_HEIGHT - 222)
        return left_rect, center_rect, right_rect

    def _graph_rect(self, center_rect: pygame.Rect) -> pygame.Rect:
        # Keep a dedicated safe graph lane inside center panel.
        return pygame.Rect(center_rect.x + 24, center_rect.y + 92, center_rect.w - 48, center_rect.h - 176)

    def _node_metrics(self, run_map) -> tuple[int, int, int, int]:
        cols = max(1, len(run_map or []))
        max_rows = 1
        for col in run_map or []:
            max_rows = max(max_rows, len(col) if isinstance(col, list) else 1)
        dense_score = max(cols - 6, 0) + max(max_rows - 4, 0)
        base = 22
        radius = max(14, base - dense_score)
        boss_radius = min(radius + 4, 24)
        hit_radius = max(radius + 8, 24)
        line_w = 3 if dense_score <= 1 else 2
        return radius, boss_radius, hit_radius, line_w

    def _refresh_graph_layout(self, run):
        _, center_rect, _ = self._panel_rects()
        graph_rect = self._graph_rect(center_rect)
        run_map = run.get("map", []) if isinstance(run, dict) else []
        cols = max(1, len(run_map))

        self.node_positions = {}
        for ci, col in enumerate(run_map):
            if not isinstance(col, list):
                continue
            count = max(1, len(col))
            x = graph_rect.x + int((ci / max(1, cols - 1)) * graph_rect.w)
            for ri, node in enumerate(col):
                if not isinstance(node, dict):
                    continue
                if count == 1:
                    y = graph_rect.centery
                else:
                    y = graph_rect.y + int((ri / max(1, count - 1)) * graph_rect.h)
                self.node_positions[str(node.get("id", f"{ci}_{ri}"))] = (x, y)

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
            run = self.app.run_state or {"map": []}
            self._refresh_graph_layout(run)
            self.click_node(pos)

    def click_node(self, pos):
        run = self.app.run_state or {"map": []}
        radius, boss_radius, hit_radius, _ = self._node_metrics(run.get("map", []))
        for col in run.get("map", []):
            for node in col if isinstance(col, list) else []:
                node_id = str(node.get("id", ""))
                if not node_id or node_id not in self.node_positions:
                    continue
                nx, ny = self.node_positions[node_id]
                rr = boss_radius if node.get("type") == "boss" else radius
                rr = max(rr, hit_radius - 8)
                if pygame.Rect(nx - hit_radius, ny - hit_radius, hit_radius * 2, hit_radius * 2).collidepoint(pos) and node.get("state") in {"available", "incomplete", "current"}:
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
            pygame.draw.line(s, col, (x - 8, y + 8), (x + 7, y - 7), 2)
            pygame.draw.polygon(s, col, [(x + 7, y - 7), (x + 12, y - 2), (x + 1, y + 3)])
        elif node_type == "challenge":
            pts = [(x, y - 9), (x + 6, y - 4), (x + 8, y + 5), (x, y + 9), (x - 8, y + 5), (x - 6, y - 4)]
            pygame.draw.polygon(s, col, pts, 2)
        elif node_type == "event":
            pygame.draw.polygon(s, col, [(x, y - 9), (x + 3, y - 2), (x + 9, y - 2), (x + 4, y + 3), (x + 6, y + 9), (x, y + 5), (x - 6, y + 9), (x - 4, y + 3), (x - 9, y - 2), (x - 3, y - 2)])
        elif node_type == "treasure":
            pygame.draw.rect(s, col, (x - 8, y - 3, 16, 10), 2, border_radius=3)
            pygame.draw.line(s, col, (x - 8, y + 1), (x + 8, y + 1), 2)
        elif node_type == "shop":
            pygame.draw.rect(s, col, (x - 7, y - 2, 14, 10), 2, border_radius=3)
            pygame.draw.arc(s, col, (x - 6, y - 8, 12, 10), 3.14, 6.28, 2)
        else:
            pygame.draw.line(s, col, (x - 8, y), (x + 8, y), 2)
            pygame.draw.line(s, col, (x, y - 8), (x, y + 8), 2)

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
        run = self.app.run_state or {"gold": 0, "map": []}
        stage_idx = self._current_stage_index(run)
        self.selected_biome = str(run.get("biome", "kaypacha") or "kaypacha").lower()
        bg_name = self.BIOME_BG_NAME.get(self.selected_biome, "Templo Obsidiana")
        self.bg_seed = abs(hash(f"map:{self.selected_biome}:{stage_idx}")) % 100000
        self.app.bg_gen.render_parallax(
            s,
            bg_name,
            self.bg_seed,
            pygame.time.get_ticks() / 1000.0,
            particles_on=bool(self.app.user_settings.get("fx_particles", True)),
        )
        stage_title = self.STAGE_TITLES[stage_idx]
        stage_thought = self.CHAKANA_THOUGHTS[stage_idx]

        lvl = int(run.get("level", 1) or 1)
        xp = int(run.get("xp", 0) or 0)
        xp_need = self.app.xp_needed_for_level(lvl) if hasattr(self.app, "xp_needed_for_level") else max(1, lvl * 20)
        gold = int(run.get("gold", 0) or 0)

        viewport = safe_area(INTERNAL_WIDTH, INTERNAL_HEIGHT, 18, 18)
        topbar = pygame.Rect(viewport.x, 16, viewport.w, 98)
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
        chip_x = max(topbar.x + 16, self.deck_btn.x - 14 - total_w)
        chip_y = topbar.y + 56
        for (txt, col), cw in zip(chip_specs, chip_ws):
            chip = pygame.Rect(chip_x, chip_y, cw, chip_h)
            pygame.draw.rect(s, UColors.PANEL_ALT, chip, border_radius=8)
            pygame.draw.rect(s, col, chip, 1, border_radius=8)
            s.blit(self.app.tiny_font.render(txt, True, col), (chip.x + 9, chip.y + 5))
            chip_x += cw + gap

        pygame.draw.rect(s, UI_THEME["panel_2"], self.deck_btn, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], self.deck_btn, 2, border_radius=10)
        txt = self.app.map_font.render("Mazo", True, UI_THEME["text"])
        s.blit(txt, txt.get_rect(center=self.deck_btn.center))

        left_rect, center_rect, right_rect = self._panel_rects()

        for r in (left_rect, center_rect, right_rect):
            UIPanel(r).draw(s)

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

        self._refresh_graph_layout(run)
        radius, boss_radius, hit_radius, line_w = self._node_metrics(run.get("map", []))

        for ci, col in enumerate(run.get("map", [])):
            if ci < len(run.get("map", [])) - 1:
                for node in col if isinstance(col, list) else []:
                    node_id = str(node.get("id", ""))
                    if node_id not in self.node_positions:
                        continue
                    npos = self.node_positions[node_id]
                    for next_id in node.get("next", []):
                        nxt = self.app.node_lookup.get(next_id)
                        if nxt is None:
                            continue
                        nxt_pos = self.node_positions.get(str(next_id))
                        if not nxt_pos:
                            continue
                        active = node.get("state") in {"available", "current", "incomplete"}
                        clr = (122, 132, 182) if active else (68, 70, 88)
                        width = line_w + (1 if active else 0)
                        pygame.draw.line(s, clr, npos, nxt_pos, width)

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        hovered_node = None
        for col in run.get("map", []):
            for node in col if isinstance(col, list) else []:
                node_id = str(node.get("id", ""))
                if node_id not in self.node_positions:
                    continue
                nx, ny = self.node_positions[node_id]
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
                if node.get("type") == "boss":
                    color = UI_THEME["bad"] if state != "locked" else (90, 40, 40)

                rr = boss_radius if node.get("type") == "boss" else radius
                node_hover = pygame.Rect(nx - hit_radius, ny - hit_radius, hit_radius * 2, hit_radius * 2).collidepoint(mouse)
                if node_hover:
                    hovered_node = node

                if state == "locked":
                    pygame.draw.circle(s, (40, 40, 56), (nx, ny), rr + 3)
                    pygame.draw.circle(s, color, (nx, ny), rr)
                    pygame.draw.line(s, UI_THEME["muted"], (nx - 6, ny), (nx + 6, ny), 2)
                else:
                    if node_hover:
                        pygame.draw.circle(s, (220, 194, 255), (nx, ny), rr + 7)
                    elif state == "current":
                        pygame.draw.circle(s, (200, 180, 245), (nx, ny), rr + 5)
                    pygame.draw.circle(s, color, (nx, ny), rr)
                    self._draw_icon(s, node.get("type", "event"), nx, ny)

                show_label = node_hover or state == "current"
                if show_label:
                    label = self.NODE_NAMES.get(node.get("type"), "Ruta")
                    label_txt = self._fit_text(self.app.tiny_font, label, 120)
                    s.blit(self.app.tiny_font.render(label_txt, True, UI_THEME["text"]), (nx - 44, ny + rr + 4))

        harmony = run.get("player", {}).get("harmony_current", 0) if isinstance(run.get("player", {}), dict) else 0
        harmony_goal = run.get("player", {}).get("harmony_ready_threshold", 6) if isinstance(run.get("player", {}), dict) else 6
        deck_size = len(run.get("deck", []) or [])

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
