import pygame

from game.ui.anim import TypewriterBanner
from game.ui.theme import UI_THEME
from game.settings import INTERNAL_HEIGHT, INTERNAL_WIDTH


def wrap_text(font, text, width):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if font.size(nxt)[0] <= width:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


ENEMY_DIALOGUES = {
    "voidling": ["Te borraré del telar.", "Sangra la trama.", "Ya casi caes."],
    "ink_mite": ["Toda historia se mancha.", "No podrás leer tu destino.", "Tu magia se derrite."],
    "inverse_weaver": ["Yo escribo finales.", "Nadie cruza este umbral.", "Inclínate ante el vacío."],
}
CHAKANA_DIALOGUES = [
    "Mi hilo no se rompe.",
    "La Chakana me sostiene.",
    "Transmuto miedo en poder.",
    "No retrocedo.",
]


class CombatScreen:
    def __init__(self, app, combat_state, is_boss=False):
        self.app = app
        self.c = combat_state
        self.is_boss = is_boss
        self.hand_scroll = 0
        self.selected_card_index = None
        self.floaters = []
        self.tooltip = None
        self.log_visible = True
        self.log_lines = []
        self.help_visible = False
        self.banner = TypewriterBanner()
        self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
        self.end_turn_rect = pygame.Rect(INTERNAL_WIDTH - 300, INTERNAL_HEIGHT - 146, 250, 90)
        self.status_rect = pygame.Rect(INTERNAL_WIDTH - 300, INTERNAL_HEIGHT - 250, 250, 84)
        self.selected_info_rect = pygame.Rect(INTERNAL_WIDTH - 520, INTERNAL_HEIGHT - 146, 200, 90)
        self.dialog_enemy = TypewriterBanner()
        self.dialog_hero = TypewriterBanner()
        self.dialog_cd = 0
        self.selected_biome = self.app.rng.choice(self.app.bg_gen.BIOMES)
        self.bg_seed = abs(hash(f"{self.selected_biome}:{self.c.turn}:{self.c.enemies[0].id if self.c.enemies else 'none'}")) % 100000
        self._taunt("enemy_taunt_start")
        self._trigger_dialog("intro")

    def _taunt(self, key):
        txt = self.app.loc.t(key)
        if txt == key:
            txt = self.app.loc.t("lore_short_2")
        self.banner.set(txt, 2.5)

    def _enemy_rect(self, idx):
        return pygame.Rect(120 + idx * 430, 150, 370, 405)

    def _visible_hand(self):
        hand = self.c.hand
        start = max(0, min(self.hand_scroll, max(0, len(hand) - 6)))
        return start, hand[start : start + 6]

    def _card_rect(self, vis_idx, total, hovered):
        card_w, card_h = 196, 282
        gap = 18
        total_w = total * card_w + max(0, total - 1) * gap
        start_x = (INTERNAL_WIDTH - total_w) // 2
        base_y = int(INTERNAL_HEIGHT * 0.665)
        center = (total - 1) / 2.0
        arc = abs(vis_idx - center)
        x = start_x + vis_idx * (card_w + gap)
        y = base_y + int(arc * 8)
        if hovered:
            y -= 18
        return pygame.Rect(x, y, card_w, card_h)

    def _intent_text(self, enemy):
        intent = enemy.current_intent()
        kind = intent.get("intent", "attack")
        val = intent.get("value", [intent.get("stacks", 1), intent.get("stacks", 1)])
        num = val[0] if isinstance(val, list) else val
        if kind == "attack":
            label = f"ATK {num}"
        elif kind == "defend":
            label = f"DEF {num}"
        elif kind == "debuff":
            label = f"DEBUFF {intent.get('stacks', 1)}"
        else:
            label = f"BUFF {intent.get('stacks', 1)}"
        return label, kind

    def _selected_card(self):
        if self.selected_card_index is None or self.selected_card_index >= len(self.c.hand):
            return None
        return self.c.hand[self.selected_card_index]

    def _trigger_dialog(self, reason):
        if self.dialog_cd > 0:
            return
        enemy_id = self.c.enemies[0].id if self.c.enemies else "voidling"
        enemy_line = self.app.rng.choice(ENEMY_DIALOGUES.get(enemy_id, ENEMY_DIALOGUES["voidling"]))
        hero_line = self.app.rng.choice(CHAKANA_DIALOGUES)
        if reason == "low_enemy":
            hero_line = "La victoria está cerca."
        self.dialog_enemy.set(enemy_line, 2.4)
        self.dialog_hero.set(hero_line, 2.4)
        self.dialog_cd = 4.0

    def _execute_selected(self):
        card = self._selected_card()
        if not card:
            self.c.end_turn()
            self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)
            return
        if card.cost > self.c.player["energy"]:
            return
        if card.definition.target == "enemy":
            target_idx = next((i for i, e in enumerate(self.c.enemies) if e.alive), None)
            if target_idx is None:
                return
            self.c.play_card(self.selected_card_index, target_idx)
            self._trigger_dialog("rare" if card.definition.rarity in {"rare", "legendary"} else "attack")
        else:
            self.c.play_card(self.selected_card_index, None)
            self._trigger_dialog("cast")
        self.selected_card_index = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.hand_scroll -= event.y
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self._execute_selected()
            elif event.key == pygame.K_h:
                self.help_visible = not self.help_visible
            elif event.key == pygame.K_ESCAPE:
                self.c.needs_target = None
                self.selected_card_index = None
                self.help_visible = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            if self.end_turn_rect.collidepoint(pos):
                self._execute_selected()
                return
            if self.status_rect.collidepoint(pos):
                self.log_visible = not self.log_visible
                return
            for i, e in enumerate(self.c.enemies):
                if self._enemy_rect(i).collidepoint(pos) and e.alive and self.selected_card_index is not None:
                    self.c.play_card(self.selected_card_index, i)
                    self.selected_card_index = None
                    return
            start, visible = self._visible_hand()
            for i, _ in enumerate(visible):
                rr = self._card_rect(i, len(visible), False)
                if rr.collidepoint(pos):
                    self.selected_card_index = start + i
                    self.app.sfx.play("card_pick")
                    return

    def update(self, dt):
        self.c.update(dt)
        self.dialog_cd = max(0, self.dialog_cd - dt)
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            self.turn_timer -= dt
            if self.turn_timer <= 0:
                self.c.end_turn()
                self.turn_timer = self.app.run_state.get("settings", {}).get("turn_timer_seconds", 20)

        for ev in self.c.pop_events():
            if ev["type"] == "damage":
                self.floaters.append({"target": ev["target"], "text": f"-{ev['amount']}", "color": UI_THEME["bad"], "time": 0.9})
                self.log_lines.insert(0, f"{ev['target']}: -{ev['amount']} HP")
                if ev["target"] == "player" and ev["amount"] >= 9:
                    self._trigger_dialog("big_hit")
            elif ev["type"] == "block":
                self.floaters.append({"target": ev["target"], "text": f"+{ev['amount']} B", "color": UI_THEME["block"], "time": 0.9})
                self.log_lines.insert(0, f"{ev['target']}: +{ev['amount']} Bloque")
        self.log_lines = self.log_lines[:7]
        self.floaters = [{**f, "time": f["time"] - dt} for f in self.floaters if f["time"] > 0]

        if any(e.alive and e.hp <= e.max_hp * 0.25 for e in self.c.enemies):
            self._trigger_dialog("low_enemy")

        if self.c.result == "victory":
            self.app.on_combat_victory()
        elif self.c.result == "defeat":
            self.app.goto_menu()

    def _draw_card(self, s, rect, card, selected=False, hovered=False):
        pygame.draw.rect(s, UI_THEME["card_bg"], rect, border_radius=12)
        pygame.draw.rect(s, UI_THEME["card_border"], rect, 2, border_radius=12)
        art_h = int(rect.h * 0.66)
        art = self.app.assets.sprite("cards", card.definition.id, (rect.w - 16, art_h), fallback=(80, 60, 120))
        s.blit(art, (rect.x + 8, rect.y + 34))
        title = self.app.loc.t(card.definition.name_key)
        s.blit(self.app.card_title_font.render(title, True, UI_THEME["text"]), (rect.x + 10, rect.y + 4))
        txt = self.app.loc.t(card.definition.text_key)
        lines = wrap_text(self.app.card_text_font, txt, rect.w - 18)[:3]
        for i, line in enumerate(lines):
            s.blit(self.app.card_text_font.render(line, True, UI_THEME["muted"]), (rect.x + 10, rect.y + int(rect.h * 0.74) + i * 22))
        pygame.draw.circle(s, UI_THEME["energy"], (rect.right - 20, rect.y + 20), 15)
        s.blit(self.app.small_font.render(str(card.cost), True, UI_THEME["text_dark"]), (rect.right - 26, rect.y + 8))
        if selected:
            pygame.draw.rect(s, UI_THEME["accent_violet"], rect.inflate(8, 8), 3, border_radius=14)

    def render(self, s):
        sky, silhouettes, fog = self.app.bg_gen.get_layers(self.selected_biome, self.bg_seed)
        parallax = int((pygame.time.get_ticks() * 0.02) % 24)
        s.blit(sky, (0, 0))
        s.blit(silhouettes, (-parallax, 0))
        s.blit(silhouettes, (INTERNAL_WIDTH - parallax, 0))
        s.blit(fog, (parallax // 2, 0))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        self.tooltip = None

        top = pygame.Rect(0, 0, INTERNAL_WIDTH, 98)
        pygame.draw.rect(s, UI_THEME["primary_purple"], top)
        s.blit(self.app.big_font.render("CHAKANA: Purple Wizard", True, UI_THEME["gold"]), (24, 24))
        lore = self.banner.current or self.app.loc.t("lore_short_1")
        s.blit(self.app.font.render(lore, True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - 260, 34))
        if self.app.run_state.get("settings", {}).get("turn_timer_enabled", False):
            timer_txt = f"⏱ {int(self.turn_timer)}s"
            s.blit(self.app.font.render(timer_txt, True, UI_THEME["text"]), (INTERNAL_WIDTH - 170, 32))

        dialog_l = pygame.Rect(280, 104, 650, 70)
        dialog_r = pygame.Rect(960, 104, 650, 70)
        pygame.draw.rect(s, (28, 16, 44), dialog_l, border_radius=10)
        pygame.draw.rect(s, (28, 16, 44), dialog_r, border_radius=10)
        s.blit(self.app.small_font.render(f"Enemy: {self.dialog_enemy.current}", True, UI_THEME["bad"]), (dialog_l.x + 12, dialog_l.y + 24))
        s.blit(self.app.small_font.render(f"Chakana: {self.dialog_hero.current}", True, UI_THEME["good"]), (dialog_r.x + 12, dialog_r.y + 24))

        p = self.c.player
        hud = pygame.Rect(INTERNAL_WIDTH - 540, 186, 490, 300)
        pygame.draw.rect(s, UI_THEME["panel"], hud, border_radius=12)
        s.blit(self.app.font.render(f"HP {p['hp']}/{p['max_hp']}", True, UI_THEME["text"]), (hud.x + 20, hud.y + 20))
        s.blit(self.app.font.render(f"Bloque {p['block']}", True, UI_THEME["block"]), (hud.x + 20, hud.y + 62))
        s.blit(self.app.font.render(f"Ruptura {p['rupture']}", True, UI_THEME["rupture"]), (hud.x + 20, hud.y + 104))
        s.blit(self.app.font.render("Energía", True, UI_THEME["text"]), (hud.x + 20, hud.y + 148))
        for i in range(5):
            pygame.draw.circle(s, UI_THEME["energy"] if i < p["energy"] else (65, 68, 90), (hud.x + 120 + i * 42, hud.y + 164), 13)

        for i, e in enumerate(self.c.enemies):
            er = self._enemy_rect(i)
            pygame.draw.rect(s, UI_THEME["deep_purple"], er, border_radius=14)
            sp = self.app.assets.sprite("enemies", e.id, (184, 184), fallback=(100, 60, 90))
            s.blit(sp, (er.x + 12, er.y + 16))
            intent_txt, kind = self._intent_text(e)
            color = UI_THEME["bad"] if kind == "attack" else UI_THEME["block"]
            s.blit(self.app.small_font.render("Intent", True, UI_THEME["muted"]), (er.x + 220, er.y + 26))
            s.blit(self.app.big_font.render(intent_txt, True, color), (er.x + 220, er.y + 56))
            s.blit(self.app.font.render(self.app.loc.t(e.name_key), True, UI_THEME["text"]), (er.x + 12, er.y + 214))
            ratio = max(0, e.hp) / max(1, e.max_hp)
            pygame.draw.rect(s, (35, 24, 50), (er.x + 12, er.y + 252, 340, 18), border_radius=7)
            pygame.draw.rect(s, UI_THEME["hp"], (er.x + 12, er.y + 252, int(340 * ratio), 18), border_radius=7)
            s.blit(self.app.small_font.render(f"HP {e.hp}/{e.max_hp}  BLK {e.block}  RUP {e.statuses.get('rupture',0)}", True, UI_THEME["text"]), (er.x + 12, er.y + 278))

        pygame.draw.rect(s, (16, 18, 32), (0, int(INTERNAL_HEIGHT * 0.61), INTERNAL_WIDTH, INTERNAL_HEIGHT - int(INTERNAL_HEIGHT * 0.61)))
        start, visible = self._visible_hand()
        hover_idx = None
        for i, _ in enumerate(visible):
            if self._card_rect(i, len(visible), False).inflate(0, 20).collidepoint(mouse):
                hover_idx = i
        for i, c in enumerate(visible):
            rr = self._card_rect(i, len(visible), hover_idx == i)
            self._draw_card(s, rr, c, selected=(start + i == self.selected_card_index), hovered=(hover_idx == i))

        pygame.draw.rect(s, UI_THEME["panel_2"], self.status_rect, border_radius=10)
        s.blit(self.app.small_font.render("Registro", True, UI_THEME["text"]), (self.status_rect.x + 78, self.status_rect.y + 30))

        selected = self._selected_card()
        action_label = self.app.loc.t("button_end_turn")
        btn_col = UI_THEME["violet"]
        disabled = False
        sub = "Sin carta"
        if selected:
            sub = f"Seleccionada: {self.app.loc.t(selected.definition.name_key)} (Costo {selected.cost})"
            if selected.definition.target == "enemy":
                action_label = "ATACAR"
            else:
                action_label = "EJECUTAR"
            if selected.cost > p["energy"]:
                disabled = True
                btn_col = (90, 78, 110)
                self.tooltip = "Energía insuficiente"
        pygame.draw.rect(s, btn_col, self.end_turn_rect, border_radius=12)
        s.blit(self.app.font.render(action_label, True, UI_THEME["text"]), (self.end_turn_rect.x + 58, self.end_turn_rect.y + 26))
        s.blit(self.app.small_font.render(sub, True, UI_THEME["muted"]), (self.end_turn_rect.x - 300, self.end_turn_rect.y + 32))
        if disabled:
            pygame.draw.rect(s, (220, 130, 130), self.end_turn_rect, 2, border_radius=12)

        if self.log_visible:
            battle_log = pygame.Rect(INTERNAL_WIDTH - 540, 500, 490, 300)
            pygame.draw.rect(s, UI_THEME["panel"], battle_log, border_radius=12)
            s.blit(self.app.font.render(self.app.loc.t("combat_log"), True, UI_THEME["text"]), (battle_log.x + 14, battle_log.y + 12))
            for i, line in enumerate(self.log_lines[:8]):
                col = UI_THEME["bad"] if "-" in line else UI_THEME["block"] if "+" in line else UI_THEME["muted"]
                s.blit(self.app.small_font.render(line, True, col), (battle_log.x + 14, battle_log.y + 48 + i * 30))

        if self.help_visible:
            panel = pygame.Rect(200, 170, 970, 520)
            pygame.draw.rect(s, UI_THEME["deep_purple"], panel, border_radius=12)
            s.blit(self.app.big_font.render("Ayuda / Cómo ganar", True, UI_THEME["text"]), (panel.x + 24, panel.y + 24))
            lines = [
                "Click carta: seleccionar", "Botón principal: EJECUTAR/ATACAR", "E o click botón: confirmar", "ESC: cancelar selección",
                "H: abrir/cerrar ayuda", "Tip: farmea nodos Desafío para oro extra", "Tip: sube de nivel y abre sobres premium", "Boss exige mazo mejorado",
            ]
            for i, line in enumerate(lines):
                s.blit(self.app.small_font.render(line, True, UI_THEME["muted"]), (panel.x + 24, panel.y + 88 + i * 40))

        if self.tooltip and not self.help_visible:
            tr = pygame.Rect(min(mouse[0] + 16, INTERNAL_WIDTH - 420), min(mouse[1] + 14, INTERNAL_HEIGHT - 80), 400, 60)
            pygame.draw.rect(s, (18, 18, 26), tr, border_radius=8)
            s.blit(self.app.card_text_font.render(self.tooltip, True, UI_THEME["text"]), (tr.x + 10, tr.y + 18))
