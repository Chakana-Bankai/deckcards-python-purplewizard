import math

import pygame

from game.ui.components.card_effect_summary import infer_card_role, summarize_card_effect
from game.ui.components.card_preview_panel import CardPreviewPanel
from game.ui.theme import UI_THEME
from game.ui.system.layout import inset, safe_area, split_horizontal, split_vertical


class DeckScreen:
    MIN_MAIN_DECK = 15
    MAX_MAIN_DECK = 20

    def __init__(self, app):
        self.app = app
        self.back = pygame.Rect(20, 20, 160, 46)
        self.selected_card_id = None
        self.selected_zone = None
        self.selected_index = None
        self.toast_text = ""
        self.toast_t = 0.0
        self.main_scroll = 0
        self.side_scroll = 0
        self.row_h_main = 30
        self.row_h_side = 28
        self.main_view_rows = 11
        self.side_view_rows = 11
        self.move_to_side_btn = pygame.Rect(720, 930, 260, 48)
        self.move_to_main_btn = pygame.Rect(990, 930, 260, 48)
        self.preview = CardPreviewPanel(app=app)

        self.main_rect = pygame.Rect(36, 98, 644, 384)
        self.side_rect = pygame.Rect(36, 510, 644, 404)
        self.preview_rect = pygame.Rect(700, 98, 1184, 816)

    def _refresh_layout(self, s: pygame.Surface):
        w, h = s.get_size()
        root = safe_area(w, h, 20, 56)

        top_h = 58
        body = pygame.Rect(root.x, root.y + top_h + 12, root.w, root.h - top_h - 12)
        left_col, right_col = split_horizontal(body, 0.36)
        top_left, bottom_left = split_vertical(left_col, 0.46)

        self.main_rect = inset(top_left, 8)
        self.side_rect = inset(bottom_left, 8)
        self.preview_rect = inset(right_col, 8)

        self.back = pygame.Rect(root.x, root.y + 6, 170, 46)

        btn_w = 250
        btn_h = 48
        gap = 18
        total_w = btn_w * 2 + gap
        btn_x = root.centerx - total_w // 2
        btn_y = min(root.bottom - btn_h, self.side_rect.bottom + 10)
        self.move_to_side_btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        self.move_to_main_btn = pygame.Rect(self.move_to_side_btn.right + gap, btn_y, btn_w, btn_h)

    def _toast(self, text: str):
        self.toast_text = str(text)
        self.toast_t = 1.8

    def _select(self, zone: str, index: int, cid: str):
        self.selected_zone = zone
        self.selected_index = index
        self.selected_card_id = cid

    def _move_selected(self):
        if self.selected_zone == "main" and self.selected_index is not None:
            self._swap_main_to_sideboard(self.selected_index)
        elif self.selected_zone == "sideboard" and self.selected_index is not None:
            self._swap_sideboard_to_main(self.selected_index)

    def _swap_main_to_sideboard(self, index: int):
        deck = self.app.run_state["deck"]
        sideboard = self.app.run_state["sideboard"]
        if not (0 <= index < len(deck)):
            return
        cid = deck[index]
        if len(deck) <= self.MIN_MAIN_DECK:
            self._toast(f"No puedes bajar de {self.MIN_MAIN_DECK} cartas en el mazo principal")
            return
        deck.pop(index)
        sideboard.append(cid)
        self._select("sideboard", len(sideboard) - 1, cid)
        self._toast(f"{self.app.loc.t(self.app.card_defs.get(cid, {}).get('name_key', cid))} movida a reserva")

    def _swap_sideboard_to_main(self, index: int):
        deck = self.app.run_state["deck"]
        sideboard = self.app.run_state["sideboard"]
        if not (0 <= index < len(sideboard)):
            return
        cid = sideboard[index]
        if len(deck) >= self.MAX_MAIN_DECK:
            self._toast(f"El mazo principal no puede superar {self.MAX_MAIN_DECK} cartas")
            return
        sideboard.pop(index)
        deck.append(cid)
        self._select("main", len(deck) - 1, cid)
        self._toast(f"{self.app.loc.t(self.app.card_defs.get(cid, {}).get('name_key', cid))} movida al mazo principal")

    def _list_rects(self):
        return self.main_rect, self.side_rect

    def _visible_main_range(self):
        deck = self.app.run_state["deck"]
        start = max(0, min(self.main_scroll, max(0, len(deck) - self.main_view_rows)))
        end = min(len(deck), start + self.main_view_rows)
        return start, end

    def _visible_side_range(self):
        sb = self.app.run_state["sideboard"]
        start = max(0, min(self.side_scroll, max(0, len(sb) - self.side_view_rows)))
        end = min(len(sb), start + self.side_view_rows)
        return start, end

    def _main_row_rect(self, visible_idx: int) -> pygame.Rect:
        y0 = self.main_rect.y + 52
        return pygame.Rect(self.main_rect.x + 12, y0 + visible_idx * self.row_h_main, self.main_rect.w - 24, 26)

    def _side_row_rect(self, visible_idx: int) -> pygame.Rect:
        y0 = self.side_rect.y + 52
        return pygame.Rect(self.side_rect.x + 12, y0 + visible_idx * self.row_h_side, self.side_rect.w - 24, 24)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                self.app.goto_map()
            elif event.key == pygame.K_RETURN:
                self._move_selected()

        if event.type == pygame.MOUSEWHEEL:
            pos = self.app.renderer.map_mouse(pygame.mouse.get_pos())
            main_rect, side_rect = self._list_rects()
            if main_rect.collidepoint(pos):
                self.main_scroll = max(0, self.main_scroll - event.y)
            elif side_rect.collidepoint(pos):
                self.side_scroll = max(0, self.side_scroll - event.y)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back.collidepoint(pos):
                self.app.goto_map()
                return
            if self.move_to_side_btn.collidepoint(pos) and self.selected_zone == "main":
                self._move_selected()
                return
            if self.move_to_main_btn.collidepoint(pos) and self.selected_zone == "sideboard":
                self._move_selected()
                return

            m_start, m_end = self._visible_main_range()
            for vi, i in enumerate(range(m_start, m_end)):
                cid = self.app.run_state["deck"][i]
                r = self._main_row_rect(vi)
                if r.collidepoint(pos):
                    self._select("main", i, cid)
                    return

            s_start, s_end = self._visible_side_range()
            for vi, i in enumerate(range(s_start, s_end)):
                cid = self.app.run_state["sideboard"][i]
                r = self._side_row_rect(vi)
                if r.collidepoint(pos):
                    self._select("sideboard", i, cid)
                    return

    def update(self, dt):
        self.toast_t = max(0.0, self.toast_t - dt)

    def _draw_scrollbar(self, s, rect, total, visible, start):
        if total <= visible:
            return
        bar = pygame.Rect(rect.right - 10, rect.y + 40, 6, rect.h - 52)
        pygame.draw.rect(s, (56, 52, 72), bar, border_radius=4)
        ratio = visible / float(total)
        knob_h = max(24, int(bar.h * ratio))
        max_start = max(1, total - visible)
        offset = int((bar.h - knob_h) * (start / max_start))
        knob = pygame.Rect(bar.x, bar.y + offset, bar.w, knob_h)
        pygame.draw.rect(s, UI_THEME["gold"], knob, border_radius=4)

    def _deck_geometry_stats(self, deck_ids: list[str]) -> dict[str, float]:
        axes = {"Attack": 0.0, "Defense": 0.0, "Harmony": 0.0, "Control": 0.0, "Ritual": 0.0, "Tempo": 0.0}
        for cid in deck_ids:
            card = self.app.card_defs.get(cid, {}) if isinstance(self.app.card_defs, dict) else {}
            if not isinstance(card, dict):
                continue
            summary = summarize_card_effect(card, card_instance=None, ctx=None)
            stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
            tags = set(card.get("tags", []) or [])
            axes["Attack"] += float(stats.get("damage", 0) or 0)
            axes["Defense"] += float(stats.get("block", 0) or 0)
            axes["Harmony"] += float(stats.get("harmony", 0) or 0)
            axes["Control"] += float(stats.get("draw", 0) or 0) + float(stats.get("scry", 0) or 0) + float(stats.get("rupture", 0) or 0)
            axes["Ritual"] += 1.0 if "ritual" in tags else 0.0
            axes["Tempo"] += float(stats.get("energy", 0) or 0) + (0.5 if int(card.get("cost", 1) or 1) <= 1 else 0.0)
        return axes

    def _draw_geometry_map(self, s: pygame.Surface, rect: pygame.Rect, axes: dict[str, float]):
        pygame.draw.rect(s, (30, 28, 44), rect, border_radius=10)
        pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 1, border_radius=10)
        labels = ["Attack", "Defense", "Harmony", "Control", "Ritual", "Tempo"]
        values = [max(0.0, float(axes.get(k, 0.0))) for k in labels]
        max_v = max(1.0, max(values))
        cx, cy = rect.centerx, rect.centery + 8
        radius = min(rect.w, rect.h) * 0.34

        for ring in range(1, 5):
            rr = radius * (ring / 4.0)
            pts = []
            for i in range(6):
                ang = -math.pi / 2 + i * (2 * math.pi / 6)
                pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
            pygame.draw.polygon(s, (78, 72, 108), pts, 1)

        poly = []
        for i, v in enumerate(values):
            ang = -math.pi / 2 + i * (2 * math.pi / 6)
            rr = radius * (v / max_v)
            x = cx + rr * math.cos(ang)
            y = cy + rr * math.sin(ang)
            poly.append((x, y))
            ax = cx + (radius + 18) * math.cos(ang)
            ay = cy + (radius + 18) * math.sin(ang)
            t = self.app.tiny_font.render(labels[i], True, UI_THEME["muted"])
            s.blit(t, t.get_rect(center=(ax, ay)))

        fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        rel = [(x - rect.x, y - rect.y) for x, y in poly]
        pygame.draw.polygon(fill, (168, 120, 236, 76), rel)
        pygame.draw.polygon(fill, (226, 196, 255, 180), rel, 2)
        s.blit(fill, rect.topleft)

    def render(self, s):
        self._refresh_layout(s)
        s.fill(UI_THEME["bg"])

        pygame.draw.rect(s, UI_THEME["panel"], self.back, border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (self.back.x + 40, self.back.y + 10))

        for rect in (self.main_rect, self.side_rect, self.preview_rect):
            pygame.draw.rect(s, UI_THEME["panel"], rect, border_radius=12)
            pygame.draw.rect(s, UI_THEME["accent_violet"], rect, 2, border_radius=12)

        s.blit(self.app.small_font.render("Mazo Activo (click para previsualizar)", True, UI_THEME["gold"]), (self.main_rect.x + 12, self.main_rect.y + 14))
        s.blit(self.app.small_font.render("Reserva / Sideboard", True, UI_THEME["gold"]), (self.side_rect.x + 12, self.side_rect.y + 14))
        s.blit(self.app.small_font.render("Preview + Geometria", True, UI_THEME["gold"]), (self.preview_rect.x + 14, self.preview_rect.y + 14))

        attacks = skills = rituals = total_cost = 0
        role_counts = {"attack": 0, "defense": 0, "energy": 0, "control": 0, "ritual": 0, "combo": 0}
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        deck = self.app.run_state["deck"]
        sideboard = self.app.run_state["sideboard"]
        for cid in deck:
            cd = self.app.card_defs.get(cid, {})
            total_cost += cd.get("cost", 1)
            tags = cd.get("tags", [])
            attacks += int("attack" in tags)
            skills += int("skill" in tags)
            rituals += int("ritual" in tags)
            role = infer_card_role(cd)
            role_counts[role] = int(role_counts.get(role, 0)) + 1

        m_start, m_end = self._visible_main_range()
        for vi, i in enumerate(range(m_start, m_end)):
            cid = deck[i]
            cd = self.app.card_defs.get(cid, self.app.card_defs.get(next(iter(self.app.card_defs.keys()), "")))
            r = self._main_row_rect(vi)
            is_selected = self.selected_zone == "main" and self.selected_index == i
            col = (56, 66, 108) if r.collidepoint(mouse) else (34, 36, 56)
            pygame.draw.rect(s, col, r, border_radius=4)
            if is_selected:
                pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=4)
            s.blit(self.app.tiny_font.render(f"{i+1:02d}. {self.app.loc.t(cd.get('name_key', cid))}", True, UI_THEME["text"]), (r.x + 6, r.y + 6))

        s_start, s_end = self._visible_side_range()
        for vi, i in enumerate(range(s_start, s_end)):
            cid = sideboard[i]
            cd = self.app.card_defs.get(cid, self.app.card_defs.get(next(iter(self.app.card_defs.keys()), "")))
            r = self._side_row_rect(vi)
            is_selected = self.selected_zone == "sideboard" and self.selected_index == i
            col = (56, 66, 108) if r.collidepoint(mouse) else (34, 36, 56)
            pygame.draw.rect(s, col, r, border_radius=4)
            if is_selected:
                pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=4)
            s.blit(self.app.tiny_font.render(f"{i+1:02d}. {self.app.loc.t(cd.get('name_key', cid))}", True, UI_THEME["text"]), (r.x + 6, r.y + 4))

        self._draw_scrollbar(s, self.main_rect, len(deck), self.main_view_rows, m_start)
        self._draw_scrollbar(s, self.side_rect, len(sideboard), self.side_view_rows, s_start)

        n = max(1, len(deck))
        avg = total_cost / n
        main_stats_chip = pygame.Rect(self.main_rect.right - 286, self.main_rect.y + 10, 274, 36)
        pygame.draw.rect(s, UI_THEME["panel_2"], main_stats_chip, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], main_stats_chip, 1, border_radius=8)
        main_line = f"Cartas {n} | Coste {avg:.1f} | ATK {attacks} | RIT {rituals}"
        while self.app.tiny_font.size(main_line)[0] > main_stats_chip.w - 12 and len(main_line) > 8:
            main_line = main_line[:-4] + "..."
        s.blit(self.app.tiny_font.render(main_line, True, UI_THEME["gold"]), (main_stats_chip.x + 6, main_stats_chip.y + 10))

        reserve_count = len(sideboard)
        top_roles = sorted(role_counts.items(), key=lambda it: it[1], reverse=True)
        role_line = " / ".join(f"{k[:3].upper()} {v}" for k, v in top_roles[:3] if v > 0) or "Sin roles"
        side_stats_chip = pygame.Rect(self.side_rect.right - 286, self.side_rect.y + 10, 274, 36)
        pygame.draw.rect(s, UI_THEME["panel_2"], side_stats_chip, border_radius=8)
        pygame.draw.rect(s, UI_THEME["accent_violet"], side_stats_chip, 1, border_radius=8)
        side_line = f"Reserva {reserve_count} | {role_line}"
        while self.app.tiny_font.size(side_line)[0] > side_stats_chip.w - 12 and len(side_line) > 8:
            side_line = side_line[:-4] + "..."
        s.blit(self.app.tiny_font.render(side_line, True, UI_THEME["muted"]), (side_stats_chip.x + 6, side_stats_chip.y + 10))

        hover_card_id = None
        for vi, i in enumerate(range(m_start, m_end)):
            r = self._main_row_rect(vi)
            if r.collidepoint(mouse):
                hover_card_id = deck[i]
                break
        if hover_card_id is None:
            for vi, i in enumerate(range(s_start, s_end)):
                r = self._side_row_rect(vi)
                if r.collidepoint(mouse):
                    hover_card_id = sideboard[i]
                    break

        preview_id = hover_card_id or self.selected_card_id or (deck[0] if deck else (sideboard[0] if sideboard else None))
        selected = self.app.card_defs.get(preview_id) if preview_id else None

        top_preview = pygame.Rect(self.preview_rect.x + 14, self.preview_rect.y + 42, self.preview_rect.w - 28, int(self.preview_rect.h * 0.52))
        bottom_geo = pygame.Rect(self.preview_rect.x + 14, top_preview.bottom + 12, self.preview_rect.w - 28, self.preview_rect.bottom - (top_preview.bottom + 26))
        self.preview.render(s, top_preview, selected, app=self.app)

        axes = self._deck_geometry_stats(deck)
        self._draw_geometry_map(s, bottom_geo, axes)

        side_enabled = self.selected_zone == "main"
        main_enabled = self.selected_zone == "sideboard"
        pygame.draw.rect(s, UI_THEME["violet"] if side_enabled else (84, 76, 106), self.move_to_side_btn, border_radius=10)
        pygame.draw.rect(s, UI_THEME["violet"] if main_enabled else (84, 76, 106), self.move_to_main_btn, border_radius=10)
        s.blit(self.app.small_font.render("Mover a reserva", True, UI_THEME["text"]), (self.move_to_side_btn.x + 32, self.move_to_side_btn.y + 12))
        s.blit(self.app.small_font.render("Mover al mazo", True, UI_THEME["text"]), (self.move_to_main_btn.x + 36, self.move_to_main_btn.y + 12))

        if self.toast_t > 0 and self.toast_text:
            toast_rect = pygame.Rect(self.preview_rect.right - 560, self.preview_rect.bottom - 58, 560, 52)
            pygame.draw.rect(s, UI_THEME["deep_purple"], toast_rect, border_radius=10)
            pygame.draw.rect(s, UI_THEME["gold"], toast_rect, 2, border_radius=10)
            s.blit(self.app.small_font.render(self.toast_text[:80], True, UI_THEME["text"]), (toast_rect.x + 14, toast_rect.y + 14))



