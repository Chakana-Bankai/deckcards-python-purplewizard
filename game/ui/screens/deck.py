import pygame

from game.ui.theme import UI_THEME


class DeckScreen:
    MIN_MAIN_DECK = 10
    MAX_MAIN_DECK = 20

    def __init__(self, app):
        self.app = app
        self.back = pygame.Rect(20, 20, 160, 46)
        self.selected_card_id = None
        self.selected_zone = None
        self.selected_index = None
        self.toast_text = ""
        self.toast_t = 0.0

    def _toast(self, text: str):
        self.toast_text = str(text)
        self.toast_t = 1.8

    def _select(self, zone: str, index: int, cid: str):
        self.selected_zone = zone
        self.selected_index = index
        self.selected_card_id = cid

    def _swap_main_to_sideboard(self, index: int):
        deck = self.app.run_state["deck"]
        sideboard = self.app.run_state["sideboard"]
        cid = deck[index]
        if len(deck) <= self.MIN_MAIN_DECK:
            self._toast(f"No puedes bajar de {self.MIN_MAIN_DECK} cartas en el mazo principal")
            return
        deck.pop(index)
        sideboard.append(cid)
        self._select("sideboard", len(sideboard) - 1, cid)
        self._toast(f"{self.app.loc.t(self.app.card_defs.get(cid, {}).get('name_key', cid))} movida a sideboard")

    def _swap_sideboard_to_main(self, index: int):
        deck = self.app.run_state["deck"]
        sideboard = self.app.run_state["sideboard"]
        cid = sideboard[index]
        if len(deck) >= self.MAX_MAIN_DECK:
            self._toast(f"El mazo principal no puede superar {self.MAX_MAIN_DECK} cartas")
            return
        sideboard.pop(index)
        deck.append(cid)
        self._select("main", len(deck) - 1, cid)
        self._toast(f"{self.app.loc.t(self.app.card_defs.get(cid, {}).get('name_key', cid))} movida al mazo principal")

    def _wrap_text(self, text: str, width: int, max_lines: int = 5):
        words = str(text or "").split()
        lines = []
        cur = ""
        for word in words:
            candidate = (cur + " " + word).strip()
            if self.app.tiny_font.size(candidate)[0] <= width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
                if len(lines) >= max_lines:
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        return lines

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                self.app.goto_map()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.back.collidepoint(pos):
                self.app.goto_map()
                return
            for i, cid in enumerate(self.app.run_state["deck"]):
                r = pygame.Rect(48, 152 + i * 26, 620, 24)
                if r.collidepoint(pos):
                    self._select("main", i, cid)
                    self._swap_main_to_sideboard(i)
                    return
            for i, cid in enumerate(self.app.run_state["sideboard"]):
                r = pygame.Rect(48, 566 + i * 24, 620, 22)
                if r.collidepoint(pos):
                    self._select("sideboard", i, cid)
                    self._swap_sideboard_to_main(i)
                    return

    def update(self, dt):
        self.toast_t = max(0.0, self.toast_t - dt)

    def render(self, s):
        s.fill(UI_THEME["bg"])

        pygame.draw.rect(s, UI_THEME["panel"], self.back, border_radius=8)
        s.blit(self.app.font.render(self.app.loc.t("menu_back"), True, UI_THEME["text"]), (60, 30))

        main_rect = pygame.Rect(36, 98, 644, 384)
        side_rect = pygame.Rect(36, 510, 644, 404)
        preview_rect = pygame.Rect(700, 98, 1184, 816)

        pygame.draw.rect(s, UI_THEME["panel"], main_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], main_rect, 2, border_radius=12)
        pygame.draw.rect(s, UI_THEME["panel"], side_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], side_rect, 2, border_radius=12)
        pygame.draw.rect(s, UI_THEME["panel"], preview_rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["accent_violet"], preview_rect, 2, border_radius=12)

        s.blit(self.app.small_font.render("Mazo Activo (click para enviar a sideboard)", True, UI_THEME["gold"]), (48, 112))
        s.blit(self.app.small_font.render("Sideboard (click para regresar al mazo)", True, UI_THEME["gold"]), (48, 524))
        s.blit(self.app.small_font.render("Selector de mazo", True, UI_THEME["gold"]), (714, 112))

        attacks = skills = rituals = total_cost = 0
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, cid in enumerate(self.app.run_state["deck"]):
            cd = self.app.card_defs.get(cid, self.app.card_defs.get(next(iter(self.app.card_defs.keys()), "")))
            total_cost += cd.get("cost", 1)
            tags = cd.get("tags", [])
            if "attack" in tags:
                attacks += 1
            if "skill" in tags:
                skills += 1
            if "ritual" in tags:
                rituals += 1
            r = pygame.Rect(48, 152 + i * 26, 620, 24)
            is_selected = self.selected_zone == "main" and self.selected_index == i
            col = (56, 66, 108) if r.collidepoint(mouse) else (34, 36, 56)
            pygame.draw.rect(s, col, r, border_radius=4)
            if is_selected:
                pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=4)
            s.blit(self.app.tiny_font.render(f"{i+1:02d}. {self.app.loc.t(cd.get('name_key', cid))}", True, UI_THEME["text"]), (54, 156 + i * 26))

        for i, cid in enumerate(self.app.run_state["sideboard"]):
            cd = self.app.card_defs.get(cid, self.app.card_defs.get(next(iter(self.app.card_defs.keys()), "")))
            r = pygame.Rect(48, 566 + i * 24, 620, 22)
            is_selected = self.selected_zone == "sideboard" and self.selected_index == i
            col = (56, 66, 108) if r.collidepoint(mouse) else (34, 36, 56)
            pygame.draw.rect(s, col, r, border_radius=4)
            if is_selected:
                pygame.draw.rect(s, UI_THEME["gold"], r, 2, border_radius=4)
            s.blit(self.app.tiny_font.render(f"{i+1:02d}. {self.app.loc.t(cd.get('name_key', cid))}", True, UI_THEME["text"]), (54, 569 + i * 24))

        n = max(1, len(self.app.run_state["deck"]))
        avg = total_cost / n
        s.blit(self.app.font.render(self.app.loc.t("deck_stats", count=n, avg=f"{avg:.1f}"), True, UI_THEME["gold"]), (48, 940))
        s.blit(self.app.font.render(self.app.loc.t("deck_stats_tags", atk=attacks, skill=skills, ritual=rituals), True, UI_THEME["muted"]), (48, 972))

        selected = self.app.card_defs.get(self.selected_card_id) if self.selected_card_id else None
        if selected:
            art_rect = pygame.Rect(preview_rect.x + 22, preview_rect.y + 58, 320, 460)
            art = self.app.assets.sprite("cards", selected.get("id", ""), (art_rect.w, art_rect.h), fallback=(70, 44, 105))
            s.blit(art, art_rect.topleft)
            pygame.draw.rect(s, UI_THEME["accent_violet"], art_rect, 2, border_radius=8)

            name = self.app.loc.t(selected.get("name_key", selected.get("id", "Carta")))
            s.blit(self.app.big_font.render(name[:36], True, UI_THEME["text"]), (preview_rect.x + 370, preview_rect.y + 66))
            s.blit(self.app.small_font.render(f"Coste: {selected.get('cost', 0)}", True, UI_THEME["energy"]), (preview_rect.x + 370, preview_rect.y + 118))
            tag_txt = ", ".join(selected.get("tags", [])) or "-"
            s.blit(self.app.small_font.render(f"Tags: {tag_txt}", True, UI_THEME["muted"]), (preview_rect.x + 370, preview_rect.y + 152))

            desc = self.app.loc.t(selected.get("text_key", ""))
            y = preview_rect.y + 206
            for line in self._wrap_text(desc, 770, max_lines=12):
                s.blit(self.app.small_font.render(line, True, UI_THEME["text"]), (preview_rect.x + 370, y))
                y += 26
        else:
            s.blit(self.app.font.render("Selecciona una carta para previsualizar", True, UI_THEME["muted"]), (preview_rect.x + 18, preview_rect.y + 58))

        if self.toast_t > 0 and self.toast_text:
            toast_rect = pygame.Rect(860, 930, 860, 52)
            pygame.draw.rect(s, UI_THEME["deep_purple"], toast_rect, border_radius=10)
            pygame.draw.rect(s, UI_THEME["gold"], toast_rect, 2, border_radius=10)
            s.blit(self.app.small_font.render(self.toast_text[:100], True, UI_THEME["text"]), (toast_rect.x + 16, toast_rect.y + 14))
