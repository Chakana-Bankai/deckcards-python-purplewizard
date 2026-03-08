import pygame

from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH
from game.ui.components.topbar import MapTopBar
from game.ui.theme import UI_THEME
from game.ui.system.components import UIPanel, UITooltip
from game.ui.system.icons import draw_icon_with_value
from game.ui.system.layout import safe_area


class MapScreen:
    NODE_NAMES = {
        "event": "Ritual",
        "combat": "Sombra",
        "challenge": "Prueba",
        "elite": "Elite",
        "path": "Camino",
        "treasure": "Reliquia",
        "relic": "Reliquia",
        "shop": "Mercader",
        "sanctuary": "Santuario",
        "boss": "Arconte",
    }

    NODE_SHORT = {
        "combat": "Prueba",
        "challenge": "Prueba",
        "event": "Susurro",
        "path": "Camino",
        "treasure": "Fragmento",
        "relic": "Reliquia",
        "shop": "Mercader",
        "sanctuary": "Santuario",
        "boss": "Archonte",
        "elite": "Elite",
    }

    NODE_LORE = {
        "event": "Los ecos del templo piden una decision serena.",
        "combat": "Sombras antiguas custodian este sendero.",
        "challenge": "Una prueba mayor intenta quebrar tu foco.",
        "elite": "Una entidad de alto riesgo marca el rito.",
        "path": "Uno de los 7 Caminos bendice tu progreso.",
        "treasure": "Una reliquia olvidada late bajo la piedra.",
        "relic": "Una reliquia del camino altera tu destino.",
        "shop": "El mercader del umbral intercambia poder por oro.",
        "sanctuary": "Un santuario restaura el pulso antes de continuar.",
        "boss": "El Arconte aguarda al final de la geometria.",
    }

    STAGE_TITLES = [
        "Ukhu Pacha",
        "Kay Pacha",
        "Hanan Pacha",
        "Fractura de la Chakana",
    ]

    CHAKANA_THOUGHTS = [
        "La piedra recuerda cada paso que doy.",
        "Entre ecos y rutas, mi voluntad se afina.",
        "El cielo ritual exige precision y calma.",
        "Frente a la fractura, solo queda verdad.",
    ]

    MAP_HINTS = [
        "Ruta activa: sigue los nodos iluminados.",
        "Los 7 Caminos entregan bendiciones de run.",
        "El Arconte final observa desde la fractura.",
        "Planea dos nodos adelante para no romper ritmo.",
    ]

    PATH_TITLES = [
        "Camino del Filo",
        "Camino del Velo",
        "Camino del Eco",
        "Camino del Pulso",
        "Camino del Umbral",
        "Camino del Cielo",
        "Camino del Sello",
    ]

    BRANCH_LANES = [("NORTE", "Hanan"), ("ESTE", "Oraculo"), ("OESTE", "Guerrero"), ("SUR", "Uku")]

    ARCHON_NAMES = {
        "ukhu": "Arconte del Vacio",
        "kaypacha": "Arconte del Ritual",
        "hanan": "Arconte Celestial",
        "fractura_chakana": "Arconte Supremo",
    }

    ARCHON_LINES = {
        "ukhu": "Bajo la roca, el vacio aprende tu nombre.",
        "kaypacha": "Toda ofrenda altera el pulso del rito.",
        "hanan": "La altura juzga tu armonia en silencio.",
        "fractura_chakana": "La Chakana rota reclama su guardian final.",
    }

    BIOME_BG_NAME = {
        "ukhu": "Caverna Umbral",
        "kaypacha": "Templo Obsidiana",
        "hanan": "Ruinas Chakana",
        "fractura_chakana": "Ruinas Chakana",
        "forest": "Pampa Astral",
        "umbral": "Caverna Umbral",
    }

    def __init__(self, app):
        self.app = app
        self.lore_timer = 0
        self.lore_idx = 0
        self.topbar = MapTopBar()
        self.selected_biome = "kaypacha"
        self.bg_seed = abs(hash("map:kaypacha")) % 100000
        self.node_positions = {}
        self.top_buttons = {
            "deck": pygame.Rect(0, 0, 132, 34),
            "shop": pygame.Rect(0, 0, 132, 34),
            "codex": pygame.Rect(0, 0, 132, 34),
        }

    def on_enter(self):
        self.lore_timer = 0

    def _panel_rects(self):
        left_rect = pygame.Rect(28, 128, 340, INTERNAL_HEIGHT - 214)
        right_rect = pygame.Rect(INTERNAL_WIDTH - 368, 128, 340, INTERNAL_HEIGHT - 214)
        center_rect = pygame.Rect(left_rect.right + 14, 128, right_rect.x - (left_rect.right + 28), INTERNAL_HEIGHT - 214)
        return left_rect, center_rect, right_rect

    def _graph_rect(self, center_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(center_rect.x + 30, center_rect.y + 108, center_rect.w - 60, center_rect.h - 214)

    def _node_metrics(self, run_map) -> tuple[int, int]:
        cols = max(1, len(run_map or []))
        max_rows = 1
        for col in run_map or []:
            max_rows = max(max_rows, len(col) if isinstance(col, list) else 1)
        dense_score = max(cols - 6, 0) + max(max_rows - 3, 0)
        base = max(11, 18 - dense_score)
        line_w = 2 if dense_score <= 1 else 1
        return base, line_w

    def _node_radius(self, node_type: str, base_radius: int) -> int:
        nt = self._normalized_node_type(node_type)
        if nt == "boss":
            return base_radius + 9
        if nt in {"elite", "challenge"}:
            return base_radius + 4
        if nt in {"event", "path", "treasure", "relic", "shop", "sanctuary"}:
            return base_radius + 2
        return base_radius

    def _normalized_node_type(self, node_type: str | None) -> str:
        nt = str(node_type or "event").lower()
        if nt == "guide":
            return "path"
        if nt == "relic":
            return "treasure"
        return nt

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
            if count == 1:
                ys = [graph_rect.centery]
            elif count == 4:
                # Chakana-like lane anchors: norte / este / oeste / sur.
                top = graph_rect.y + max(28, int(graph_rect.h * 0.10))
                upper = graph_rect.y + int(graph_rect.h * 0.36)
                lower = graph_rect.y + int(graph_rect.h * 0.64)
                bottom = graph_rect.bottom - max(28, int(graph_rect.h * 0.10))
                ys = [int(top), int(upper), int(lower), int(bottom)]
            else:
                row_gap = min(110, max(68, graph_rect.h // (count + 1)))
                center_idx = (count - 1) / 2.0
                ys = [int(graph_rect.centery + (ri - center_idx) * row_gap) for ri in range(count)]
            for ri, node in enumerate(col):
                if not isinstance(node, dict):
                    continue
                self.node_positions[str(node.get("id", f"{ci}_{ri}"))] = (x, ys[min(ri, len(ys) - 1)])

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.goto_menu()
            if event.key == pygame.K_TAB:
                self.app.goto_deck()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for bid, rect in self.top_buttons.items():
                if rect.collidepoint(pos):
                    self.app.sfx.play("ui_click")
                    if bid == "deck":
                        self.app.goto_deck()
                    elif bid == "shop":
                        self.app.goto_shop()
                    else:
                        self.app.goto_codex()
                    return
            run = self.app.run_state or {"map": []}
            self._refresh_graph_layout(run)
            self.click_node(pos)

    def click_node(self, pos):
        run = self.app.run_state or {"map": []}
        base_radius, _ = self._node_metrics(run.get("map", []))
        hit_pad = max(10, base_radius + 6)
        for col in run.get("map", []):
            for node in col if isinstance(col, list) else []:
                node_id = str(node.get("id", ""))
                if not node_id or node_id not in self.node_positions:
                    continue
                nx, ny = self.node_positions[node_id]
                rr = self._node_radius(node.get("type"), base_radius)
                hit = rr + hit_pad
                if pygame.Rect(nx - hit, ny - hit, hit * 2, hit * 2).collidepoint(pos) and node.get("state") in {"available", "incomplete", "current"}:
                    self.app.sfx.play("ui_click")
                    self.app.select_map_node(node)
                    return

    def update(self, dt):
        self.lore_timer += dt
        if self.lore_timer > 3:
            self.lore_timer = 0
            self.lore_idx = (self.lore_idx + 1) % max(1, len(self.MAP_HINTS))

    def _current_stage_index(self, run: dict) -> int:
        current_id = getattr(self.app, "current_node_id", None)
        if current_id and current_id in self.app.node_lookup:
            col = int(self.app.node_lookup[current_id].get("col", 0))
            total_cols = max(1, len(run.get("map", [])))
            stages = max(1, len(self.STAGE_TITLES))
            return max(0, min(stages - 1, int((col * stages) / max(1, total_cols))))

        stage = 0
        for col in run.get("map", []):
            for node in col:
                if node.get("state") in {"completed", "cleared", "current", "incomplete"}:
                    stage = max(stage, int(node.get("col", 0)))
        total_cols = max(1, len(run.get("map", [])))
        stages = max(1, len(self.STAGE_TITLES))
        return max(0, min(stages - 1, int((stage * stages) / max(1, total_cols))))

    def _draw_icon(self, s, node_type, x, y):
        col = (24, 20, 34)
        t = self._normalized_node_type(node_type)
        if t == "combat":
            pygame.draw.line(s, col, (x - 10, y + 10), (x + 9, y - 9), 2)
            pygame.draw.polygon(s, col, [(x + 9, y - 9), (x + 14, y - 3), (x + 2, y + 4)])
        elif t in {"elite", "challenge"}:
            pts = [(x, y - 10), (x + 7, y - 4), (x + 9, y + 5), (x, y + 10), (x - 9, y + 5), (x - 7, y - 4)]
            pygame.draw.polygon(s, col, pts, 2)
        elif t == "event":
            pygame.draw.polygon(s, col, [(x, y - 9), (x + 3, y - 2), (x + 9, y - 2), (x + 4, y + 3), (x + 6, y + 9), (x, y + 5), (x - 6, y + 9), (x - 4, y + 3), (x - 9, y - 2), (x - 3, y - 2)])
        elif t == "path":
            pygame.draw.circle(s, col, (x - 6, y), 2)
            pygame.draw.circle(s, col, (x, y), 2)
            pygame.draw.circle(s, col, (x + 6, y), 2)
            pygame.draw.line(s, col, (x - 6, y), (x + 6, y), 2)
        elif t == "treasure":
            pygame.draw.rect(s, col, (x - 10, y - 4, 20, 12), 2, border_radius=3)
            pygame.draw.line(s, col, (x - 8, y + 1), (x + 8, y + 1), 2)
        elif t == "shop":
            pygame.draw.circle(s, col, (x, y), 8, 2)
            pygame.draw.line(s, col, (x - 4, y), (x + 4, y), 2)
            pygame.draw.line(s, col, (x, y - 4), (x, y + 4), 2)
        elif t == "sanctuary":
            pygame.draw.circle(s, col, (x, y), 8, 2)
            pygame.draw.line(s, col, (x, y - 6), (x, y + 6), 2)
            pygame.draw.line(s, col, (x - 6, y), (x + 6, y), 2)
        elif t == "boss":
            pygame.draw.circle(s, col, (x, y), 7, 2)
            pygame.draw.line(s, col, (x - 9, y), (x + 9, y), 2)
            pygame.draw.line(s, col, (x, y - 9), (x, y + 9), 2)
        else:
            pygame.draw.line(s, col, (x - 8, y), (x + 8, y), 2)
            pygame.draw.line(s, col, (x, y - 8), (x, y + 8), 2)

    def _fit_text(self, font, text: str, width: int) -> str:
        out = str(text or "").replace("\n", " ").strip()
        if not out:
            return ""
        while font.size(out)[0] > width and len(out) > 4:
            out = out[:-4] + "..."
        return out

    def _wrap_lines(self, font, text: str, width: int, max_lines: int) -> list[str]:
        words = str(text or "").replace("\n", " ").split()
        if not words:
            return [""]
        lines = []
        cur = words[0]
        for w in words[1:]:
            cand = f"{cur} {w}"
            if font.size(cand)[0] <= width:
                cur = cand
            else:
                lines.append(cur)
                cur = w
                if len(lines) >= max_lines - 1:
                    break
        if len(lines) < max_lines:
            lines.append(cur)
        lines = lines[:max_lines]
        if len(lines) == max_lines and font.size(lines[-1])[0] > width:
            lines[-1] = self._fit_text(font, lines[-1], width)
        return lines

    def _archon_data(self):
        biome_key = str(self.selected_biome or "kaypacha").lower()
        fallback = self.ARCHON_NAMES.get(biome_key, "Arconte Desconocido")
        line = self.ARCHON_LINES.get(biome_key, "La profecia aun no se revela.")
        boss_id = ""
        if hasattr(self.app, "biome_def_by_id") and isinstance(self.app.biome_def_by_id, dict):
            boss_id = str((self.app.biome_def_by_id.get(biome_key, {}) or {}).get("boss", "") or "")
        boss_name = fallback
        if boss_id:
            pool = []
            if hasattr(self.app, "content") and self.app.content:
                pool.extend(list(getattr(self.app.content, "bosses", []) or []))
            pool.extend(list(getattr(self.app, "enemies_data", []) or []))
            for entry in pool:
                if not isinstance(entry, dict) or str(entry.get("id", "")) != boss_id:
                    continue
                name_key = entry.get("name_key")
                boss_name = self.app.loc.t(name_key) if name_key else str(entry.get("name", boss_id)).replace("_", " ").title()
                break
        return boss_id or biome_key, boss_name, line

    def _draw_top_buttons(self, s, topbar: pygame.Rect):
        labels = [("deck", "Mazo"), ("shop", "Tienda"), ("codex", "Codex")]
        x = topbar.right - 430
        y = topbar.y + 54
        for key, label in labels:
            rect = pygame.Rect(x, y, 132, 32)
            self.top_buttons[key] = rect
            pygame.draw.rect(s, UI_THEME["panel_2"], rect, border_radius=9)
            pygame.draw.rect(s, UI_THEME["gold"] if key != "shop" else UI_THEME["accent_violet"], rect, 2, border_radius=9)
            txt = self.app.tiny_font.render(label, True, UI_THEME["text"])
            s.blit(txt, txt.get_rect(center=rect.center))
            x += 142

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

        stage_title = self.STAGE_TITLES[min(stage_idx, len(self.STAGE_TITLES) - 1)]
        stage_thought = self.CHAKANA_THOUGHTS[min(stage_idx, len(self.CHAKANA_THOUGHTS) - 1)]

        lvl = int(run.get("level", 1) or 1)
        xp = int(run.get("xp", 0) or 0)
        xp_need = self.app.xp_needed_for_level(lvl) if hasattr(self.app, "xp_needed_for_level") else max(1, lvl * 20)
        gold = int(run.get("gold", 0) or 0)

        viewport = safe_area(INTERNAL_WIDTH, INTERNAL_HEIGHT, 18, 18)
        topbar = pygame.Rect(viewport.x, 16, viewport.w, 98)
        chapter = f"Ritual de {stage_title}"
        subtitle = "Viaje sagrado por los Pachas"
        self.topbar.render(s, self.app, topbar, "Mapa Ritual", chapter, subtitle, "")
        self._draw_top_buttons(s, topbar)

        left_rect, center_rect, right_rect = self._panel_rects()
        for r in (left_rect, center_rect, right_rect):
            UIPanel(r).draw(s)

        # Left panel: mage journey state.
        s.blit(self.app.small_font.render("Chakana", True, UI_THEME["gold"]), (left_rect.x + 16, left_rect.y + 14))
        avatar = self.app.assets.sprite("avatar", "codex", (118, 118), fallback=(86, 56, 132))
        s.blit(avatar, avatar.get_rect(center=(left_rect.centerx, left_rect.y + 110)).topleft)

        player = run.get("player", {}) if isinstance(run.get("player", {}), dict) else {}
        hp = int(player.get("hp", 0) or 0)
        max_hp = int(player.get("max_hp", 0) or 0)
        harmony = int(player.get("harmony_current", 0) or 0)
        blessings = list(run.get("path_blessings", []) or [])
        owned_relics = list(run.get("relics", []) or [])
        relic_count = len(owned_relics)
        mouse_now = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        relic_hover_text = ""

        rows = [
            ("vida", hp, "Vitalidad", UI_THEME["bad"], f"{hp}/{max_hp}"),
            ("harmony", harmony, "Armonia", UI_THEME["violet"], f"{harmony}"),
            ("level", lvl, "Nivel", UI_THEME["gold"], f"{lvl}"),
            ("gold", gold, "Oro", UI_THEME["gold"], f"{gold}"),
            ("relic", relic_count, "Reliquias", UI_THEME["text"], f"{relic_count}"),
        ]
        y = left_rect.y + 182
        for icon_name, icon_val, label, col, val_text in rows:
            row = pygame.Rect(left_rect.x + 12, y, left_rect.w - 24, 36)
            pygame.draw.rect(s, UI_THEME["panel_2"], row, border_radius=8)
            pygame.draw.rect(s, col, row, 1, border_radius=8)
            draw_icon_with_value(s, icon_name, icon_val, col, self.app.tiny_font, row.x + 8, row.y + 8, size=2)
            s.blit(self.app.tiny_font.render(label, True, UI_THEME["muted"]), (row.x + 60, row.y + 4))
            value_txt = self.app.small_font.render(val_text, True, col)
            s.blit(value_txt, (row.right - value_txt.get_width() - 10, row.y + 9))
            y += 42

        relic_strip = pygame.Rect(left_rect.x + 12, y + 2, left_rect.w - 24, 44)
        pygame.draw.rect(s, UI_THEME["panel_2"], relic_strip, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], relic_strip, 1, border_radius=8)
        s.blit(self.app.tiny_font.render("Reliquias activas", True, UI_THEME["gold"]), (relic_strip.x + 8, relic_strip.y + 4))
        relic_by_id = {str(r.get("id")): r for r in list(getattr(self.app, "relics_data", []) or []) if isinstance(r, dict) and r.get("id")}
        rx = relic_strip.x + 8
        for rid in owned_relics[-5:]:
            slot = pygame.Rect(rx, relic_strip.y + 18, 22, 22)
            pygame.draw.rect(s, (30, 24, 42), slot, border_radius=6)
            pygame.draw.rect(s, UI_THEME["gold"], slot, 1, border_radius=6)
            icon = self.app.assets.sprite("relics", str(rid), (18, 18), fallback=(96, 76, 124))
            s.blit(icon, (slot.x + 2, slot.y + 2))
            if slot.collidepoint(mouse_now):
                relic = relic_by_id.get(str(rid), {})
                rname = self.app.loc.t(relic.get("name_key")) if relic.get("name_key") else str(rid).replace("_", " ").title()
                rdesc = self.app.loc.t(relic.get("text_key")) if relic.get("text_key") else "Reliquia activa en esta run."
                relic_hover_text = self._fit_text(self.app.tiny_font, f"{rname}: {rdesc}", 340)
            rx += 26

        y += 50
        path_text = ", ".join([str(x) for x in blessings[-2:]]) if blessings else "Sin bendicion activa"
        s.blit(self.app.tiny_font.render("Camino activo", True, UI_THEME["gold"]), (left_rect.x + 16, y + 4))
        for i, line in enumerate(self._wrap_lines(self.app.tiny_font, path_text, left_rect.w - 28, 2)):
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["muted"]), (left_rect.x + 16, y + 24 + i * 16))

        lore_box = pygame.Rect(left_rect.x + 14, left_rect.bottom - 108, left_rect.w - 28, 92)
        pygame.draw.rect(s, UI_THEME["panel_2"], lore_box, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], lore_box, 1, border_radius=10)
        s.blit(self.app.tiny_font.render("Cronica del viaje", True, UI_THEME["gold"]), (lore_box.x + 8, lore_box.y + 8))
        lore_lines = self._wrap_lines(self.app.small_font, stage_thought, lore_box.w - 14, 2)
        for i, line in enumerate(lore_lines):
            s.blit(self.app.small_font.render(line, True, UI_THEME["muted"]), (lore_box.x + 8, lore_box.y + 30 + i * 22))

        # Center panel: ritual graph + biome motif.
        biome_panel = self.app.assets.sprite("biomes", self.selected_biome, (center_rect.w - 14, center_rect.h - 14), fallback=(40, 32, 60))
        biome_panel.set_alpha(34)
        s.blit(biome_panel, (center_rect.x + 7, center_rect.y + 7))

        center_badge = pygame.Rect(center_rect.x + 14, center_rect.y + 12, 220, 24)
        pygame.draw.rect(s, UI_THEME["panel_2"], center_badge, border_radius=7)
        pygame.draw.rect(s, UI_THEME["gold"], center_badge, 1, border_radius=7)
        s.blit(self.app.tiny_font.render(f"Etapa {stage_idx + 1} - {stage_title}", True, UI_THEME["gold"]), (center_badge.x + 8, center_badge.y + 5))
        # Chakana branch lane hints for fast route readability.
        lane_ys = [
            center_rect.y + int(center_rect.h * 0.24),
            center_rect.y + int(center_rect.h * 0.39),
            center_rect.y + int(center_rect.h * 0.54),
            center_rect.y + int(center_rect.h * 0.69),
        ]
        for idx, (axis, branch) in enumerate(self.BRANCH_LANES):
            if idx >= len(lane_ys):
                break
            yy = lane_ys[idx]
            lane_txt = self.app.tiny_font.render(f"{axis} - {branch}", True, UI_THEME["muted"])
            s.blit(lane_txt, (center_rect.x + 16, yy))

        self._refresh_graph_layout(run)
        base_radius, line_w = self._node_metrics(run.get("map", []))

        for ci, col in enumerate(run.get("map", [])):
            if ci >= len(run.get("map", [])) - 1:
                continue
            for node in col if isinstance(col, list) else []:
                node_id = str(node.get("id", ""))
                if node_id not in self.node_positions:
                    continue
                npos = self.node_positions[node_id]
                nstate = node.get("state")
                for next_id in node.get("next", []):
                    nxt_pos = self.node_positions.get(str(next_id))
                    if not nxt_pos:
                        continue
                    col_line = (88, 92, 124)
                    if nstate in {"completed", "cleared"}:
                        col_line = (122, 176, 132)
                    elif nstate in {"available", "current", "incomplete"}:
                        col_line = (146, 156, 210)
                    pygame.draw.line(s, col_line, npos, nxt_pos, line_w)

        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        hovered_node = None
        hit_pad = max(10, base_radius + 6)

        for col in run.get("map", []):
            for node in col if isinstance(col, list) else []:
                node_id = str(node.get("id", ""))
                if node_id not in self.node_positions:
                    continue
                nx, ny = self.node_positions[node_id]
                ntype = self._normalized_node_type(node.get("type", "event"))
                state = node.get("state", "locked")
                rr = self._node_radius(ntype, base_radius)
                hover_hit = rr + hit_pad
                node_hover = pygame.Rect(nx - hover_hit, ny - hover_hit, hover_hit * 2, hover_hit * 2).collidepoint(mouse)
                if node_hover:
                    hovered_node = node

                color = (92, 92, 98)
                if state == "available":
                    color = UI_THEME["violet"]
                elif state in {"completed", "cleared"}:
                    color = UI_THEME["good"]
                elif state == "incomplete":
                    color = (210, 128, 86)
                elif state == "current":
                    color = UI_THEME["card_selected"]
                if ntype == "boss":
                    color = UI_THEME["bad"] if state != "locked" else (90, 40, 40)

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
                    self._draw_icon(s, ntype, nx, ny)

                short_label = self.NODE_SHORT.get(ntype, "Ruta")
                short_txt = self._fit_text(self.app.tiny_font, short_label, 82)
                s.blit(self.app.tiny_font.render(short_txt, True, UI_THEME["muted"]), (nx + rr + 6, ny - 7))

                if node_hover or state == "current":
                    label = self.NODE_NAMES.get(ntype, "Ruta")
                    if ntype == "path" and node.get("path_name"):
                        label = str(node.get("path_name"))
                    label_txt = self._fit_text(self.app.tiny_font, label, 148)
                    s.blit(self.app.tiny_font.render(label_txt, True, UI_THEME["text"]), (nx - 54, ny + rr + 4))

        # Right panel: archon anticipation.
        archon_id, archon_name, archon_line = self._archon_data()
        s.blit(self.app.small_font.render("Presagio del Arconte", True, UI_THEME["gold"]), (right_rect.x + 14, right_rect.y + 14))
        archon_rect = pygame.Rect(right_rect.x + 24, right_rect.y + 46, right_rect.w - 48, 220)
        pygame.draw.rect(s, UI_THEME["panel_2"], archon_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], archon_rect, 1, border_radius=12)

        archon_overlay = self.app.assets.sprite("overlays", "archon", (archon_rect.w - 22, archon_rect.h - 20), fallback=(52, 36, 72))
        archon_overlay.set_alpha(186)
        s.blit(archon_overlay, (archon_rect.x + 11, archon_rect.y + 10))

        name_line = self._fit_text(self.app.small_font, archon_name, right_rect.w - 28)
        s.blit(self.app.small_font.render(name_line, True, UI_THEME["text"]), (right_rect.x + 14, archon_rect.bottom + 12))
        for i, line in enumerate(self._wrap_lines(self.app.tiny_font, archon_line, right_rect.w - 28, 3)):
            s.blit(self.app.tiny_font.render(line, True, UI_THEME["muted"]), (right_rect.x + 14, archon_rect.bottom + 40 + i * 18))

        progress_box = pygame.Rect(right_rect.x + 14, right_rect.bottom - 118, right_rect.w - 28, 102)
        pygame.draw.rect(s, UI_THEME["panel_2"], progress_box, border_radius=10)
        pygame.draw.rect(s, UI_THEME["gold"], progress_box, 1, border_radius=10)
        s.blit(self.app.tiny_font.render("Frente ritual", True, UI_THEME["gold"]), (progress_box.x + 8, progress_box.y + 8))
        progress_txt = f"Pacha: {self.selected_biome}   Arconte: {archon_id}"
        s.blit(self.app.tiny_font.render(self._fit_text(self.app.tiny_font, progress_txt, progress_box.w - 14), True, UI_THEME["muted"]), (progress_box.x + 8, progress_box.y + 30))
        hint = self.MAP_HINTS[self.lore_idx % max(1, len(self.MAP_HINTS))]
        s.blit(self.app.tiny_font.render(self._fit_text(self.app.tiny_font, hint, progress_box.w - 14), True, UI_THEME["text"]), (progress_box.x + 8, progress_box.y + 54))

        lore_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 530, INTERNAL_HEIGHT - 86, 1060, 48)
        pygame.draw.rect(s, UI_THEME["panel"], lore_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], lore_rect, 2, border_radius=12)
        if hovered_node:
            ntype = self._normalized_node_type(hovered_node.get("type", "event"))
            lore_text = self.NODE_LORE.get(ntype, "La ruta susurra un destino incierto.")
            node_title = self.NODE_NAMES.get(ntype, "Ruta")
            if ntype == "path" and hovered_node.get("path_name"):
                node_title = str(hovered_node.get("path_name"))
                lore_text = str(hovered_node.get("path_lore") or lore_text)
            title_txt = self.app.tiny_font.render(node_title, True, UI_THEME["gold"])
            lore_line = self._fit_text(self.app.small_font, lore_text, lore_rect.w - title_txt.get_width() - 28)
            lore_txt = self.app.small_font.render(lore_line, True, UI_THEME["muted"])
            s.blit(title_txt, (lore_rect.x + 12, lore_rect.y + 14))
            s.blit(lore_txt, (lore_rect.x + 22 + title_txt.get_width(), lore_rect.y + 12))
        else:
            title_txt = self.app.tiny_font.render("Ruta viva", True, UI_THEME["gold"])
            flavor = self._fit_text(self.app.small_font, self.MAP_HINTS[self.lore_idx % max(1, len(self.MAP_HINTS))], lore_rect.w - title_txt.get_width() - 28)
            lore_txt = self.app.small_font.render(flavor, True, UI_THEME["muted"])
            s.blit(title_txt, (lore_rect.x + 12, lore_rect.y + 14))
            s.blit(lore_txt, (lore_rect.x + 22 + title_txt.get_width(), lore_rect.y + 12))

        if relic_hover_text:
            tip_rect = pygame.Rect(mouse_now[0] + 14, mouse_now[1] - 32, 360, 28)
            if tip_rect.right > INTERNAL_WIDTH - 12:
                tip_rect.x = INTERNAL_WIDTH - tip_rect.w - 12
            if tip_rect.y < 10:
                tip_rect.y = 10
            UITooltip(tip_rect, relic_hover_text).draw(s, self.app.tiny_font)
