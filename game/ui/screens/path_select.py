import pygame

from game.ui.theme import UI_THEME
from game.settings import INTERNAL_WIDTH
from game.ui.components.pixel_icons import draw_icon_with_value


class PathSelectScreen:
    def __init__(self, app):
        self.app = app
        self.hover_index = None
        self.selected_index = 0
        self.anim = {}
        self.options = [
            {"name": "Cosmic Attack", "deck": ["filo_astral", "embate_del_jaguar", "pulso_cosmico", "filo_en_cadena", "estallido_arcano", "vision_del_condor", "fragmento_celeste", "garra_espiritual", "mantra_del_umbral", "lectura_del_destino", "sello_protector", "guardia_terrenal"], "sync": "Ataque acelerado con presión constante", "diff": "Media"},
            {"name": "Harmony Control", "deck": ["sello_protector", "muralla_de_piedra", "escudo_de_luz", "resistencia_ancestral", "campo_protector", "escudo_del_chaman", "silencio_interior", "observacion_sagrada", "firmeza_del_cuerpo", "espiritu_guardian", "filo_astral", "chakana_de_luz"], "sync": "Bloqueo sólido + tempo de control", "diff": "Media"},
            {"name": "Ritual Sacrifice", "deck": ["ritual_de_la_trama", "piedra_ritual", "vinculo_de_energia", "fusion_espiritual", "invocacion_astral", "revelacion_astral", "mantra_del_umbral", "silencio_interior", "sello_protector", "filo_astral", "eco_de_sabiduria", "portal_de_la_chakana"], "sync": "Rituales y conversiones explosivas", "diff": "Alta"},
            {"name": "Temporal Scry", "deck": ["vision_del_condor", "lectura_del_destino", "observacion_sagrada", "revelacion_astral", "portal_de_la_chakana", "silencio_interior", "sello_protector", "filo_astral", "invocacion_astral", "eco_de_sabiduria", "fragmento_celeste", "guardia_terrenal"], "sync": "Scry + robo para consistencia", "diff": "Media"},
            {"name": "Astral Defense", "deck": ["sello_protector", "muralla_de_piedra", "escudo_de_luz", "campo_protector", "guardia_terrenal", "resistencia_ancestral", "firmeza_del_cuerpo", "escudo_del_chaman", "espiritu_guardian", "vision_del_condor", "filo_astral", "chakana_de_luz"], "sync": "Defensa astral con cierre seguro", "diff": "Baja-Media"},
            {"name": "Chaos Burst", "deck": ["estallido_arcano", "pulso_cosmico", "embate_del_jaguar", "filo_en_cadena", "filo_astral", "garra_espiritual", "vinculo_de_energia", "fusion_espiritual", "ritual_de_la_trama", "fragmento_celeste", "portal_de_la_chakana", "revelacion_astral"], "sync": "Daño alto con picos de energía", "diff": "Alta"},
            {"name": "Spirit Drain", "deck": ["mantra_del_umbral", "silencio_interior", "eco_de_sabiduria", "ritual_de_la_trama", "vinculo_de_energia", "fusion_espiritual", "observacion_sagrada", "sello_protector", "guardia_terrenal", "filo_astral", "piedra_ritual", "espiritu_guardian"], "sync": "Desgaste y control de recursos", "diff": "Media-Alta"},
        ]

    def on_enter(self):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto_menu()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            opt = self.options[self.selected_index]
            self.app.sfx.play("ui_click")
            self.app.start_run_with_deck(opt["deck"])
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.renderer.map_mouse(event.pos)
            for i, _ in enumerate(self.options):
                r = self._option_rect(i)
                if r.collidepoint(pos):
                    self.selected_index = i
                    self.app.sfx.play("ui_click")
                    self.app.start_run_with_deck(self.options[i]["deck"])
                    return

    def update(self, dt):
        pass

    def _option_rect(self, index: int) -> pygame.Rect:
        cols = 4
        card_w, card_h = 430, 420
        gap_x, gap_y = 26, 30
        row = index // cols
        col = index % cols
        x0 = 65
        y0 = 150
        return pygame.Rect(x0 + col * (card_w + gap_x), y0 + row * (card_h + gap_y), card_w, card_h)

    def _card_icons(self, card_def: dict) -> list[str]:
        tags = set(card_def.get("tags", []) or [])
        effects = list(card_def.get("effects", []) or [])
        icons = []
        if "attack" in tags:
            icons.append("sword")
        if "skill" in tags or any(str(e.get("type", "")) in {"block", "gain_block"} for e in effects if isinstance(e, dict)):
            icons.append("shield")
        if any(str(e.get("type", "")) == "draw" for e in effects if isinstance(e, dict)):
            icons.append("scroll")
        if any(str(e.get("type", "")) == "scry" for e in effects if isinstance(e, dict)):
            icons.append("eye")
        if any(str(e.get("type", "")) in {"energy", "gain_mana"} for e in effects if isinstance(e, dict)):
            icons.append("bolt")
        if "ritual" in tags:
            icons.append("star")
        return icons[:2] or ["star"]

    def _draw_deck_preview(self, s: pygame.Surface, rect: pygame.Rect, deck: list[str]):
        preview = deck[:4]
        for idx, cid in enumerate(preview):
            cd = self.app.card_defs.get(cid, {})
            pr = pygame.Rect(rect.x + 16 + idx * 102, rect.y + 106, 94, 132)
            pygame.draw.rect(s, (50, 44, 61), pr, border_radius=8)
            pygame.draw.rect(s, UI_THEME["accent_violet"], pr, 1, border_radius=8)
            name = self.app.loc.t(cd.get("name_key", cid)) if isinstance(cd, dict) else str(cid)
            s.blit(self.app.tiny_font.render(str(name)[:11], True, UI_THEME["text"]), (pr.x + 6, pr.y + 8))
            x = pr.x + 6
            for icon in self._card_icons(cd if isinstance(cd, dict) else {}):
                x = draw_icon_with_value(s, icon, 1, UI_THEME["gold"], self.app.tiny_font, x, pr.y + 32, size=1)
            cost = int(cd.get("cost", 1)) if isinstance(cd, dict) else 1
            pygame.draw.circle(s, UI_THEME["energy"], (pr.right - 12, pr.y + 12), 10)
            s.blit(self.app.tiny_font.render(str(cost), True, UI_THEME["text_dark"]), (pr.right - 15, pr.y + 6))

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Elige tu Trama Inicial", True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - 220, 52))
        s.blit(self.app.small_font.render("7 arquetipos de mazo para empezar la run.", True, UI_THEME["muted"]), (INTERNAL_WIDTH // 2 - 210, 90))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())

        for i, opt in enumerate(self.options):
            r = self._option_rect(i)
            hover = r.collidepoint(mouse)
            if hover:
                self.hover_index = i
                self.selected_index = i

            target = 1.03 if (hover or self.selected_index == i) else 1.0
            cur = self.anim.get(i, 1.0)
            cur = cur + (target - cur) * 0.18
            self.anim[i] = cur
            rr = r.inflate(int((cur - 1.0) * r.w), int((cur - 1.0) * r.h))
            rr.center = r.center

            pygame.draw.rect(s, UI_THEME["panel"], rr, border_radius=12)
            if self.selected_index == i:
                pygame.draw.rect(s, UI_THEME["gold"], rr, 3, border_radius=12)
            elif hover:
                pygame.draw.rect(s, UI_THEME["accent_violet"], rr, 2, border_radius=12)

            s.blit(self.app.map_font.render(opt["name"], True, UI_THEME["gold"]), (rr.x + 16, rr.y + 14))
            s.blit(self.app.small_font.render(f"Sinergia: {opt['sync']}", True, UI_THEME["muted"]), (rr.x + 16, rr.y + 48))
            s.blit(self.app.small_font.render(f"Dificultad: {opt['diff']}", True, UI_THEME["text"]), (rr.x + 16, rr.y + 74))
            self._draw_deck_preview(s, rr, opt["deck"])
            s.blit(self.app.tiny_font.render("Enter o click para iniciar", True, UI_THEME["accent_violet"]), (rr.x + 16, rr.bottom - 24))
