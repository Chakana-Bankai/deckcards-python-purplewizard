import pygame

from game.ui.theme import UI_THEME
from game.settings import INTERNAL_WIDTH


class PathSelectScreen:
    def __init__(self, app):
        self.app = app
        self.hover_index = None
        self.selected_index = 0
        self.anim = {}
        self.options = [
            {
                "name": "Rayo Chakana",
                "deck": ["filo_astral","garra_espiritual","estallido_arcano","fragmento_celeste","filo_en_cadena","sello_protector","guardia_terrenal","vision_del_condor","lectura_del_destino","pulso_cosmico","mantra_del_umbral","embate_del_jaguar"],
                "sync": "Aggro + energía + robo",
                "diff": "Media",
            },
            {
                "name": "Manto Obsidiana",
                "deck": ["sello_protector","muralla_de_piedra","escudo_de_luz","resistencia_ancestral","campo_protector","escudo_del_chaman","piedra_ritual","firmeza_del_cuerpo","filo_astral","observacion_sagrada","silencio_interior","espiritu_guardian"],
                "sync": "Premium inicial: bloqueo y control",
                "diff": "Media-Alta",
            },
            {
                "name": "Magia",
                "deck": ["portal_de_la_chakana","invocacion_astral","vinculo_de_energia","fusion_espiritual","vision_del_condor","revelacion_astral","filo_astral","sello_protector","silencio_interior","eco_de_sabiduria","ritual_de_la_trama","chakana_de_luz"],
                "sync": "Premium inicial: magia y combos fáciles",
                "diff": "Alta",
            },
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
            for i, opt in enumerate(self.options):
                r = pygame.Rect(120 + i * 590, 160, 520, 760)
                if r.collidepoint(pos):
                    self.selected_index = i
                    self.app.sfx.play("ui_click")
                    self.app.start_run_with_deck(opt["deck"])
                    return

    def update(self, dt):
        pass

    def render(self, s):
        s.fill(UI_THEME["bg"])
        s.blit(self.app.big_font.render("Elige tu Trama Inicial", True, UI_THEME["text"]), (INTERNAL_WIDTH // 2 - 220, 64))
        s.blit(self.app.small_font.render("Toda ruta abre una lección distinta de la Chakana.", True, UI_THEME["muted"]), (INTERNAL_WIDTH // 2 - 270, 102))
        mouse = self.app.renderer.map_mouse(pygame.mouse.get_pos())
        for i, opt in enumerate(self.options):
            r = pygame.Rect(120 + i * 590, 160, 520, 760)
            hover = r.collidepoint(mouse)
            if hover:
                self.hover_index = i
                self.selected_index = i
            target = 1.05 if (hover or self.selected_index == i) else 1.0
            cur = self.anim.get(i, 1.0)
            cur = cur + (target - cur) * 0.22
            self.anim[i] = cur
            rr = r.inflate(int((cur - 1.0) * r.w), int((cur - 1.0) * r.h))
            rr.center = r.center
            pygame.draw.rect(s, UI_THEME["panel"], rr, border_radius=12)
            if self.selected_index == i:
                pygame.draw.rect(s, UI_THEME["gold"], rr, 3, border_radius=12)
                s.blit(self.app.tiny_font.render("✔", True, UI_THEME["gold"]), (rr.right - 24, rr.y + 10))
            elif hover:
                pygame.draw.rect(s, UI_THEME["accent_violet"], rr, 2, border_radius=12)
            s.blit(self.app.map_font.render(opt["name"], True, UI_THEME["gold"]), (rr.x + 24, rr.y + 20))
            s.blit(self.app.small_font.render(f"Sinergia: {opt['sync']}", True, UI_THEME["muted"]), (rr.x + 24, rr.y + 62))
            s.blit(self.app.small_font.render(f"Dificultad: {opt['diff']}", True, UI_THEME["text"]), (rr.x + 24, rr.y + 94))
            attacks = 0
            blocks = 0
            util = 0
            finisher = 0
            cost = 0
            for j, cid in enumerate(opt["deck"]):
                cd = self.app.card_defs.get(cid, self.app.card_defs.get(next(iter(self.app.card_defs.keys()),"")))
                tags = cd.get("tags", [])
                if "attack" in tags:
                    attacks += 1
                if "skill" in tags or "defend" in tags:
                    blocks += 1
                if "utility" in tags or "draw" in str(cd.get("effects", "")):
                    util += 1
                if "finisher" in tags:
                    finisher += 1
                cost += int(cd.get("cost", 1))
                s.blit(self.app.tiny_font.render(self.app.loc.t(cd.get("name_key", cid)), True, UI_THEME["text"]), (rr.x + 24, rr.y + 136 + j * 24))
            avg = cost / max(1, len(opt["deck"]))
            s.blit(self.app.small_font.render(f"Daño {attacks}  Bloqueo/Habilidad {blocks}  Utilidad {util}  Remate {finisher}", True, UI_THEME["muted"]), (rr.x + 24, rr.y + 662))
            s.blit(self.app.small_font.render(f"Costo promedio: {avg:.1f}", True, UI_THEME["text"]), (rr.x + 24, rr.y + 696))
            s.blit(self.app.small_font.render("Enter o click para iniciar", True, UI_THEME["accent_violet"]), (rr.x + 24, rr.y + 726))
